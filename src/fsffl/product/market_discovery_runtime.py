from __future__ import annotations

from collections import OrderedDict, defaultdict
from collections.abc import Callable, Iterable
from typing import Any

from fsffl.opportunity import (
    AttentionStatus,
    BilateralPlausibility,
    CandidatePath,
    DeepEvaluationStatus,
    MarketOpportunity,
    OpportunityHypothesis,
    OpportunitySource,
    PreliminaryEconomicBand,
    canonical_opportunity_family_key,
    canonical_package_family_key,
    canonical_path_id,
)
from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.trade_decision import live_bounded_materiality_policy

from .behavioral_runtime import cached_behavior_profile_for_team
from .opportunity_posture import calculated_competitive_state
from .runtime import UserRuntimeContext
from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import resolve_owned_asset_ref


DEFAULT_PRELIMINARY_DECISION_BUDGET = 8
DEFAULT_FOR_YOU_LIMIT = 4
_MAX_ALTERNATE_PACKAGES = 2

TradeEvaluator = Callable[[UserRuntimeContext, dict[str, object]], dict[str, object]]


def _receive_refs(row: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(item.get("asset_ref") or "")
            for item in (row.get("receive") or [])
            if isinstance(item, dict) and item.get("asset_ref")
        )
    )


def _send_refs(row: dict[str, object]) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(item.get("asset_ref") or "")
            for item in (row.get("send") or [])
            if isinstance(item, dict) and item.get("asset_ref")
        )
    )


def _target_label(row: dict[str, object]) -> str:
    receive = row.get("receive") or []
    if receive and isinstance(receive[0], dict):
        return str(receive[0].get("label") or receive[0].get("asset_ref") or "target")
    return "target"


def _target_position(row: dict[str, object]) -> str:
    return str(row.get("target_position") or "UNKNOWN")


def _objective_family(row: dict[str, object], source: OpportunitySource) -> str:
    if source == OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT:
        return "explicit_trade_intent"
    return "upgrade_position"


def _target_family(
    row: dict[str, object],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
) -> str:
    if exact_target_constraint:
        return exact_target_constraint
    if source == OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT:
        receive = _receive_refs(row)
        if receive:
            return receive[0]
    return f"{_target_position(row)}:starter_upgrade"


def _opportunity_identity(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
) -> tuple[str, str, str, str, str]:
    team_id = str(runtime.selected_team_id or "")
    objective = _objective_family(row, source)
    need = _target_position(row)
    target_family = _target_family(
        row,
        source=source,
        exact_target_constraint=exact_target_constraint,
    )
    family = canonical_opportunity_family_key(
        focal_team_id=team_id,
        objective_family=objective,
        need_dimension=need,
        target_family=target_family,
    )
    state_id = str(runtime.league_state.state_id if runtime.league_state is not None else "")
    opportunity_id = f"market-opportunity:{state_id}:{family}"
    return opportunity_id, family, objective, need, target_family


def _row_search_pair(row: dict[str, object]) -> tuple[float, float]:
    gap = row.get("market_gap_ratio")
    distance = row.get("search_distance")
    return (
        float(gap) if isinstance(gap, (int, float)) else float("inf"),
        float(distance) if isinstance(distance, (int, float)) else float("inf"),
    )


def _prune_package_neighborhood(rows: list[dict[str, object]]) -> tuple[dict[str, object], tuple[dict[str, object], ...], int]:
    """Collapse one exact target/counterparty neighborhood before Decision work.

    Within each package shape, a row with both a larger relative market gap and a
    larger absolute search distance is Search-dominated by a closer row. This uses
    Search's existing coordinates only; it does not claim Decision or utility
    dominance. One best row per materially distinct package shape is retained.
    """

    by_shape: OrderedDict[str, list[dict[str, object]]] = OrderedDict()
    for row in rows:
        by_shape.setdefault(str(row.get("package_shape") or "unknown"), []).append(row)

    survivors: list[dict[str, object]] = []
    pruned = 0
    for shape_rows in by_shape.values():
        ordered = sorted(
            shape_rows,
            key=lambda row: (
                _row_search_pair(row),
                int(row.get("package_variant_rank") or 999),
                _send_refs(row),
            ),
        )
        if ordered:
            survivors.append(ordered[0])
            pruned += max(0, len(ordered) - 1)

    survivors.sort(
        key=lambda row: (
            _row_search_pair(row),
            len(row.get("send") or []),
            _send_refs(row),
        )
    )
    representative = survivors[0]
    alternates = tuple(survivors[1 : 1 + _MAX_ALTERNATE_PACKAGES])
    pruned += max(0, len(survivors) - 1 - len(alternates))
    return representative, alternates, pruned


def _build_path_seeds(
    runtime: UserRuntimeContext,
    rows: Iterable[dict[str, object]],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
) -> tuple[list[dict[str, object]], int]:
    grouped: OrderedDict[tuple[str, str, tuple[str, ...]], list[dict[str, object]]] = OrderedDict()
    for row in rows:
        opportunity_id, _, _, _, _ = _opportunity_identity(
            runtime,
            row,
            source=source,
            exact_target_constraint=exact_target_constraint,
        )
        key = (
            opportunity_id,
            str(row.get("counterparty_team_id") or ""),
            _receive_refs(row),
        )
        grouped.setdefault(key, []).append(row)

    seeds: list[dict[str, object]] = []
    pruned = 0
    for (opportunity_id, counterparty_team_id, receive_refs), family_rows in grouped.items():
        representative, alternates, removed = _prune_package_neighborhood(family_rows)
        pruned += removed
        package_family = canonical_package_family_key(
            opportunity_id=opportunity_id,
            counterparty_team_id=counterparty_team_id,
            receive_asset_refs=receive_refs,
        )
        seeds.append(
            {
                "opportunity_id": opportunity_id,
                "counterparty_team_id": counterparty_team_id,
                "receive_asset_refs": receive_refs,
                "package_family_key": package_family,
                "representative": representative,
                "alternates": alternates,
            }
        )
    return seeds, pruned


def _opportunity_family_for_seed(seed: dict[str, object]) -> str:
    return str(seed["opportunity_id"])


def select_preliminary_screen_indices(
    seeds: list[dict[str, object]],
    *,
    limit: int,
) -> tuple[int, ...]:
    """Spend Decision work one Opportunity family at a time before repeats."""

    budget = min(max(limit, 0), len(seeds))
    if budget == 0:
        return ()

    by_family: OrderedDict[str, list[int]] = OrderedDict()
    for index, seed in enumerate(seeds):
        by_family.setdefault(_opportunity_family_for_seed(seed), []).append(index)

    selected: list[int] = []
    depth = 0
    while len(selected) < budget:
        progressed = False
        for indices in by_family.values():
            if depth < len(indices):
                selected.append(indices[depth])
                progressed = True
                if len(selected) >= budget:
                    break
        if not progressed:
            break
        depth += 1
    return tuple(sorted(selected))


def evaluate_candidate_path(
    runtime: UserRuntimeContext,
    row: dict[str, object],
) -> dict[str, object]:
    """Attach governed pre-Simulation Decision evidence to one representative package."""

    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return row

    counterparty_team_id = str(row["counterparty_team_id"])
    send = row.get("send") or []
    receive = row.get("receive") or []
    if not send or not receive:
        return row

    focal_assets = tuple(
        resolve_owned_asset_ref(
            league_state,
            team_id=focal_team_id,
            asset_ref=str(item["asset_ref"]),
        )
        for item in send
    )
    counterparty_assets = tuple(
        resolve_owned_asset_ref(
            league_state,
            team_id=counterparty_team_id,
            asset_ref=str(item["asset_ref"]),
        )
        for item in receive
    )
    draft = TradeDraft(
        draft_id=(
            f"market-prelim:{league_state.state_id}:{focal_team_id}:"
            f"{counterparty_team_id}:"
            f"{'-'.join(str(item['asset_ref']) for item in send)}:"
            f"{'-'.join(str(item['asset_ref']) for item in receive)}"
        ),
        focal_team_id=focal_team_id,
        counterparty_team_id=counterparty_team_id,
        focal_side=TradeDraftSide(team_id=focal_team_id, assets=focal_assets),
        counterparty_side=TradeDraftSide(
            team_id=counterparty_team_id,
            assets=counterparty_assets,
        ),
    )
    proposal = submit_trade_draft(draft, as_of=league_state.as_of)
    profile = cached_behavior_profile_for_team(
        league_state,
        counterparty_team_id,
    )
    analysis = build_private_beta_trade_analysis(
        runtime,
        proposal,
        focal_team_id=focal_team_id,
        counterparty_behavior_profile=profile,
    )

    decision = analysis.get("decision") or {}
    side_a = decision.get("side_a") or {}
    side_b = decision.get("side_b") or {}
    focal_side = side_a if side_a.get("team_id") == focal_team_id else side_b
    counterparty_side = side_a if side_a.get("team_id") == counterparty_team_id else side_b

    evaluation = analysis.get("evaluation") or {}
    eval_a = evaluation.get("side_a") or {}
    eval_b = evaluation.get("side_b") or {}
    focal_eval = eval_a if eval_a.get("team_id") == focal_team_id else eval_b
    counterparty_eval = eval_a if eval_a.get("team_id") == counterparty_team_id else eval_b
    feasibility = analysis.get("negotiation_feasibility") or {}

    return {
        **row,
        "bilateral_decision_evaluated": bool(decision),
        "decision_shape": decision.get("shape"),
        "focal_decision_shape": focal_side.get("shape"),
        "counterparty_decision_shape": counterparty_side.get("shape"),
        "negotiation_feasibility_shape": feasibility.get("shape"),
        "negotiation_feasibility_evaluated": bool(feasibility),
        "acceptance_probability": None,
        "focal_roster_delta": (focal_eval.get("delta") or {}).get("resilience"),
        "counterparty_roster_delta": (counterparty_eval.get("delta") or {}).get("resilience"),
        "behavioral_evidence_attached": bool(
            (analysis.get("availability") or {}).get("behavioral_evidence")
        ),
        "behavioral_context": analysis.get("behavioral_context"),
        "post_trade_simulation_attached": False,
        "economics": analysis.get("economics"),
        "economic_net": analysis.get("economic_net"),
        "roster_adjusted_market_net": analysis.get("roster_adjusted_market_net"),
        "package_concentration": analysis.get("package_concentration"),
        "package_economics": analysis.get("package_economics"),
        "roster_legality": analysis.get("roster_legality") or [],
        "decision_dimensions": analysis.get("decision_dimensions"),
        "availability": analysis.get("availability") or {},
        "decision_completeness": analysis.get("decision_completeness") or {},
        "explanation": (
            "Representative Candidate Path completed the bounded pre-Simulation Decision screen. "
            "This is bilateral plausibility evidence, not an acceptance probability, final disposition, "
            "or exact competitive-outcome claim."
        ),
    }


def _side(payload: dict[str, Any] | None, team_id: str) -> dict[str, Any]:
    if not payload:
        return {}
    for key in ("side_a", "side_b"):
        side = payload.get(key) or {}
        if str(side.get("team_id") or "") == team_id:
            return side
    return {}


def _economic_band(
    runtime: UserRuntimeContext,
    row: dict[str, object],
) -> PreliminaryEconomicBand:
    league_state = runtime.league_state
    focal_team_id = str(runtime.selected_team_id or "")
    counterparty_team_id = str(row.get("counterparty_team_id") or "")
    if league_state is None:
        return PreliminaryEconomicBand.INCOMPLETE

    adjusted = row.get("roster_adjusted_market_net")
    focal_adjusted = _side(adjusted if isinstance(adjusted, dict) else None, focal_team_id)
    counterparty_adjusted = _side(
        adjusted if isinstance(adjusted, dict) else None,
        counterparty_team_id,
    )
    if (
        focal_adjusted.get("status") != "complete"
        or counterparty_adjusted.get("status") != "complete"
        or focal_adjusted.get("roster_adjusted_market_delta") is None
        or counterparty_adjusted.get("roster_adjusted_market_delta") is None
    ):
        return PreliminaryEconomicBand.INCOMPLETE

    try:
        threshold = live_bounded_materiality_policy(
            as_of=league_state.as_of
        ).economic.mean_value_abs
    except ValueError:
        return PreliminaryEconomicBand.INCOMPLETE

    focal_delta = float(focal_adjusted["roster_adjusted_market_delta"])
    counterparty_delta = float(counterparty_adjusted["roster_adjusted_market_delta"])
    package = row.get("package_economics")
    resolution = (
        str(package.get("resolution") or "")
        if isinstance(package, dict)
        else ""
    )
    singleton_sender = (
        str(package.get("singleton_sender_team_id") or "")
        if isinstance(package, dict)
        else ""
    )
    package_sender = (
        str(package.get("package_sender_team_id") or "")
        if isinstance(package, dict)
        else ""
    )

    if focal_delta < -threshold:
        return PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN
    if counterparty_delta < -threshold:
        return PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN

    if resolution == "singleton_underpaid":
        if singleton_sender == focal_team_id:
            return PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN
        if singleton_sender == counterparty_team_id:
            return PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN
    if resolution == "package_clears_upper_bound":
        if package_sender == focal_team_id:
            return PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN
        if package_sender == counterparty_team_id:
            return PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN
    if resolution == "within_provisional_band":
        return PreliminaryEconomicBand.BOUNDED_UNCERTAINTY
    return PreliminaryEconomicBand.ROBUST_OR_ORDINARY


def _bilateral_plausibility(
    row: dict[str, object],
    economic_band: PreliminaryEconomicBand,
) -> BilateralPlausibility:
    if not row.get("bilateral_decision_evaluated"):
        return BilateralPlausibility.INCOMPLETE

    focal_shape = str(row.get("focal_decision_shape") or "")
    counterparty_shape = str(row.get("counterparty_decision_shape") or "")
    feasibility = str(row.get("negotiation_feasibility_shape") or "")
    if focal_shape in {"uniform_loss", "incomplete", ""}:
        return (
            BilateralPlausibility.FOCAL_DOMINATED
            if focal_shape == "uniform_loss"
            else BilateralPlausibility.INCOMPLETE
        )
    if feasibility == "counterparty_dominated" or counterparty_shape == "uniform_loss":
        return BilateralPlausibility.COUNTERPARTY_DOMINATED
    if feasibility == "incomplete" or counterparty_shape in {"incomplete", ""}:
        return BilateralPlausibility.INCOMPLETE
    if economic_band in {
        PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN,
        PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN,
    }:
        return BilateralPlausibility.BILATERAL_FRICTION
    if feasibility in {"mutual_gain_candidate", "mixed", "neutral"}:
        return BilateralPlausibility.BILATERAL_SUPPORTED
    return BilateralPlausibility.BILATERAL_FRICTION


def _owner_context(row: dict[str, object]) -> tuple[str, dict[str, Any] | None]:
    context = row.get("behavioral_context")
    if not isinstance(context, dict):
        return "unavailable", None
    evidence = context.get("evidence") or {}
    items = evidence.get("items") if isinstance(evidence, dict) else None
    return (
        "observed_history",
        {
            "status": context.get("status"),
            "evidence_item_count": len(items or []),
            "acceptance_probability": None,
            "descriptive_only": True,
        },
    )


def _path_risks(
    row: dict[str, object],
    economic_band: PreliminaryEconomicBand,
    plausibility: BilateralPlausibility,
) -> tuple[str, ...]:
    risks: list[str] = []
    if economic_band == PreliminaryEconomicBand.BOUNDED_UNCERTAINTY:
        risks.append("One-for-many economics remain inside the governed provisional package band.")
    elif economic_band == PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN:
        risks.append("The focal side carries material preliminary market-economic strain.")
    elif economic_band == PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN:
        risks.append("The counterparty carries material preliminary market-economic strain.")
    elif economic_band == PreliminaryEconomicBand.INCOMPLETE:
        risks.append("Required preliminary economic evidence is incomplete.")
    if plausibility == BilateralPlausibility.BILATERAL_FRICTION:
        risks.append("Bilateral evidence is mixed enough to require deeper transaction review.")
    elif plausibility == BilateralPlausibility.COUNTERPARTY_DOMINATED:
        risks.append("The current Decision shape is counterparty-dominated.")
    elif plausibility == BilateralPlausibility.FOCAL_DOMINATED:
        risks.append("The current Decision shape is uniformly adverse for the focal team.")
    elif plausibility == BilateralPlausibility.INCOMPLETE:
        risks.append("Bilateral Decision evidence is incomplete.")
    return tuple(risks)


def _path_can_support_attention(
    row: dict[str, object],
    economic_band: PreliminaryEconomicBand,
    plausibility: BilateralPlausibility,
) -> bool:
    if economic_band == PreliminaryEconomicBand.INCOMPLETE:
        return False
    if plausibility not in {
        BilateralPlausibility.BILATERAL_SUPPORTED,
        BilateralPlausibility.BILATERAL_FRICTION,
    }:
        return False
    if economic_band == PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN:
        return str(row.get("focal_decision_shape") or "") == "uniform_gain"
    if economic_band == PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN:
        return (
            str(row.get("counterparty_decision_shape") or "") != "uniform_loss"
            and str(row.get("negotiation_feasibility_shape") or "")
            != "counterparty_dominated"
        )
    return True


def _build_candidate_path(
    runtime: UserRuntimeContext,
    seed: dict[str, object],
    row: dict[str, object],
) -> CandidatePath:
    economic_band = _economic_band(runtime, row)
    plausibility = _bilateral_plausibility(row, economic_band)
    owner_status, owner_context = _owner_context(row)
    availability = row.get("availability") or {}
    missing: list[str] = []
    if economic_band == PreliminaryEconomicBand.INCOMPLETE:
        missing.append("complete_roster_adjusted_cardinal_economics")
    if not row.get("bilateral_decision_evaluated"):
        missing.append("pre_simulation_bilateral_decision")
    if not availability.get("roster_consequences") and row.get("bilateral_decision_evaluated"):
        missing.append("complete_roster_consequences")

    package = dict(row)
    alternates = tuple(dict(item) for item in (seed.get("alternates") or ()))
    path_id = canonical_path_id(
        package_family_key=str(seed["package_family_key"]),
        send_asset_refs=_send_refs(row),
    )
    return CandidatePath(
        path_id=path_id,
        opportunity_id=str(seed["opportunity_id"]),
        counterparty_team_id=str(seed["counterparty_team_id"]),
        receive_asset_refs=tuple(seed["receive_asset_refs"]),
        package_family_key=str(seed["package_family_key"]),
        representative_package=package,
        alternate_packages=alternates,
        structural_status=str(row.get("discovery_status") or "structurally_valid"),
        economic_screen=economic_band,
        roster_legality_status=(
            "complete"
            if availability.get("mandatory_cut_cost")
            else "incomplete"
        ),
        bilateral_plausibility=plausibility,
        negotiation_feasibility_shape=(
            str(row.get("negotiation_feasibility_shape"))
            if row.get("negotiation_feasibility_shape")
            else None
        ),
        owner_context_status=owner_status,
        owner_context=owner_context,
        deep_evaluation_status=(
            DeepEvaluationStatus.PRELIM_SCREENED
            if row.get("bilateral_decision_evaluated")
            else DeepEvaluationStatus.NEEDS_DEEP_EVALUATION
        ),
        evidence_completeness="complete" if not missing else "partial",
        missing_evidence=tuple(missing),
        risks=_path_risks(row, economic_band, plausibility),
        authority={
            "search_generated_structure": True,
            "decision_pre_simulation_screened": bool(
                row.get("bilateral_decision_evaluated")
            ),
            "simulation_backed": False,
            "acceptance_probability": None,
            "owner_context_descriptive_only": True,
            "recommendation_authority": False,
        },
    )


def _hypothesis_for_opportunity(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    opportunity_id: str,
    family: str,
    objective: str,
    need: str,
    target_family: str,
    source: OpportunitySource,
) -> OpportunityHypothesis:
    league_state = runtime.league_state
    if league_state is None or runtime.selected_team_id is None:
        raise ValueError("Market hypothesis requires loaded State and managed team")
    evidence = tuple(
        str(item)
        for item in (row.get("search_context") or [])
        if str(item).strip()
    )
    return OpportunityHypothesis(
        hypothesis_id=f"hypothesis:{opportunity_id}",
        league_state_id=league_state.state_id,
        focal_team_id=runtime.selected_team_id,
        as_of=league_state.as_of,
        objective_family=objective,
        need_dimension=need,
        target_archetype=target_family,
        calculated_competitive_state=calculated_competitive_state(runtime).value,
        requested_owner_posture=OwnerStrategicPosture.DEFAULT_CALCULATED.value,
        strategic_evidence=evidence,
        source=source,
        evidence_status="supported" if evidence else "limited",
        model_versions=("next4-position-strength", "market-search-v1"),
    )


def _aggregate_opportunities(
    runtime: UserRuntimeContext,
    seeds: list[dict[str, object]],
    paths: list[CandidatePath],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
) -> tuple[list[OpportunityHypothesis], list[MarketOpportunity]]:
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return [], []

    paths_by_opportunity: dict[str, list[CandidatePath]] = defaultdict(list)
    for path in paths:
        paths_by_opportunity[path.opportunity_id].append(path)

    first_row_by_opportunity: OrderedDict[str, dict[str, object]] = OrderedDict()
    metadata: dict[str, tuple[str, str, str, str]] = {}
    for seed in seeds:
        row = seed["representative"]
        opportunity_id, family, objective, need, target_family = _opportunity_identity(
            runtime,
            row,
            source=source,
            exact_target_constraint=exact_target_constraint,
        )
        first_row_by_opportunity.setdefault(opportunity_id, row)
        metadata[opportunity_id] = (family, objective, need, target_family)

    hypotheses: list[OpportunityHypothesis] = []
    opportunities: list[MarketOpportunity] = []
    for opportunity_id, row in first_row_by_opportunity.items():
        family, objective, need, target_family = metadata[opportunity_id]
        hypothesis = _hypothesis_for_opportunity(
            runtime,
            row,
            opportunity_id=opportunity_id,
            family=family,
            objective=objective,
            need=need,
            target_family=target_family,
            source=source,
        )
        hypotheses.append(hypothesis)
        related = paths_by_opportunity.get(opportunity_id, [])
        survivors = [
            path
            for path in related
            if _path_can_support_attention(
                path.representative_package,
                path.economic_screen,
                path.bilateral_plausibility,
            )
        ]
        screened = [
            path
            for path in related
            if path.deep_evaluation_status == DeepEvaluationStatus.PRELIM_SCREENED
        ]
        if source == OpportunitySource.AUTOMATIC_FOR_YOU and survivors:
            attention = AttentionStatus.WORTH_ATTENTION
        elif survivors or screened:
            attention = AttentionStatus.EXPLORABLE
        elif related:
            attention = AttentionStatus.MARKET_MATCH_ONLY
        else:
            attention = AttentionStatus.SUPPRESSED

        representative = survivors or screened or related
        path_ids = tuple(path.path_id for path in representative[:3])
        economic = (
            representative[0].economic_screen
            if representative
            else PreliminaryEconomicBand.INCOMPLETE
        )
        bilateral = (
            representative[0].bilateral_plausibility
            if representative
            else BilateralPlausibility.INCOMPLETE
        )
        why_now = tuple(
            str(item)
            for item in (row.get("search_context") or [])
            if str(item).strip()
        )[:3]
        risks: list[str] = []
        for path in representative:
            for risk in path.risks:
                if risk not in risks:
                    risks.append(risk)
        opportunities.append(
            MarketOpportunity(
                opportunity_id=opportunity_id,
                hypothesis_id=hypothesis.hypothesis_id,
                league_state_id=league_state.state_id,
                focal_team_id=focal_team_id,
                objective_family=objective,
                need_dimension=need,
                target_family=target_family,
                why_now=why_now,
                strategic_relevance=(
                    "current_position_need"
                    if row.get("focal_position_strength_rank") is not None
                    else (
                        "explicit_market_intent"
                        if source == OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT
                        else "market_structure"
                    )
                ),
                preliminary_economic_band=economic,
                bilateral_plausibility=bilateral,
                evidence_completeness=(
                    "complete"
                    if representative
                    and representative[0].evidence_completeness == "complete"
                    else "partial"
                ),
                attention_status=attention,
                opportunity_family_key=family,
                representative_path_ids=path_ids,
                alternate_path_count=max(0, len(related) - len(path_ids)),
                top_risks=tuple(risks[:3]),
                authority={
                    "search_aggregation_only": True,
                    "decision_truth_preserved": True,
                    "simulation_backed": False,
                    "acceptance_probability": None,
                    "recommendation_authority": False,
                },
                freshness={
                    "league_state_id": league_state.state_id,
                    "as_of": league_state.as_of.isoformat(),
                },
            )
        )
    return hypotheses, opportunities


def select_for_you(
    opportunities: Iterable[MarketOpportunity],
    paths_by_id: dict[str, CandidatePath],
    *,
    limit: int = DEFAULT_FOR_YOU_LIMIT,
) -> tuple[list[MarketOpportunity], list[str]]:
    """Select a small attention frontier without a composite opportunity score."""

    eligible = [
        opportunity
        for opportunity in opportunities
        if opportunity.attention_status == AttentionStatus.WORTH_ATTENTION
    ]

    bilateral_order = {
        BilateralPlausibility.BILATERAL_SUPPORTED: 0,
        BilateralPlausibility.BILATERAL_FRICTION: 1,
        BilateralPlausibility.INCOMPLETE: 2,
        BilateralPlausibility.COUNTERPARTY_DOMINATED: 3,
        BilateralPlausibility.FOCAL_DOMINATED: 4,
    }
    economic_order = {
        PreliminaryEconomicBand.ROBUST_OR_ORDINARY: 0,
        PreliminaryEconomicBand.BOUNDED_UNCERTAINTY: 1,
        PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN: 2,
        PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN: 3,
        PreliminaryEconomicBand.INCOMPLETE: 4,
    }
    ordered = sorted(
        eligible,
        key=lambda item: (
            0 if item.strategic_relevance == "current_position_need" else 1,
            bilateral_order[item.bilateral_plausibility],
            economic_order[item.preliminary_economic_band],
            0 if item.evidence_completeness == "complete" else 1,
            min(
                (
                    float(paths_by_id[path_id].representative_package.get("market_gap_ratio") or float("inf"))
                    for path_id in item.representative_path_ids
                    if path_id in paths_by_id
                ),
                default=float("inf"),
            ),
            item.opportunity_id,
        ),
    )

    selected: list[MarketOpportunity] = []
    need_counts: dict[str, int] = defaultdict(int)
    counterparty_counts: dict[str, int] = defaultdict(int)
    target_families: set[str] = set()
    relaxations: list[str] = []

    def counterparty(opportunity: MarketOpportunity) -> str:
        for path_id in opportunity.representative_path_ids:
            path = paths_by_id.get(path_id)
            if path is not None:
                return path.counterparty_team_id
        return ""

    for opportunity in ordered:
        if len(selected) >= limit:
            break
        cp = counterparty(opportunity)
        if opportunity.target_family in target_families:
            continue
        if need_counts[opportunity.need_dimension] >= 2:
            continue
        if cp and counterparty_counts[cp] >= 2:
            continue
        selected.append(opportunity)
        target_families.add(opportunity.target_family)
        need_counts[opportunity.need_dimension] += 1
        if cp:
            counterparty_counts[cp] += 1

    if len(selected) < min(3, len(ordered)):
        for cap_name in ("counterparty", "need_dimension"):
            for opportunity in ordered:
                if len(selected) >= min(limit, max(3, len(selected))):
                    break
                if opportunity in selected or opportunity.target_family in target_families:
                    continue
                cp = counterparty(opportunity)
                if cap_name == "counterparty" and need_counts[opportunity.need_dimension] >= 2:
                    continue
                selected.append(opportunity)
                target_families.add(opportunity.target_family)
                need_counts[opportunity.need_dimension] += 1
                if cp:
                    counterparty_counts[cp] += 1
                relaxations.append(cap_name)
                if len(selected) >= limit:
                    break
            if len(selected) >= min(3, len(ordered)) or len(selected) >= limit:
                break

    return selected[:limit], sorted(set(relaxations))


def build_market_discovery(
    runtime: UserRuntimeContext,
    rows: list[dict[str, object]],
    *,
    evaluation_limit: int = DEFAULT_PRELIMINARY_DECISION_BUDGET,
    source: OpportunitySource = OpportunitySource.AUTOMATIC_FOR_YOU,
    exact_target_constraint: str | None = None,
    evaluator: TradeEvaluator = evaluate_candidate_path,
) -> dict[str, object]:
    """Build governed Opportunity/Path output from raw Search rows."""

    seeds, family_pruned = _build_path_seeds(
        runtime,
        rows,
        source=source,
        exact_target_constraint=exact_target_constraint,
    )
    selected_indices = set(
        select_preliminary_screen_indices(seeds, limit=evaluation_limit)
    )
    paths: list[CandidatePath] = []
    decision_errors = 0
    for index, seed in enumerate(seeds):
        row = dict(seed["representative"])
        if index in selected_indices:
            try:
                row = evaluator(runtime, row)
            except ValueError as exc:
                decision_errors += 1
                row = {
                    **row,
                    "bilateral_decision_evaluated": False,
                    "negotiation_feasibility_evaluated": False,
                    "decision_error": str(exc),
                }
        paths.append(_build_candidate_path(runtime, seed, row))

    hypotheses, opportunities = _aggregate_opportunities(
        runtime,
        seeds,
        paths,
        source=source,
        exact_target_constraint=exact_target_constraint,
    )
    by_id = {path.path_id: path for path in paths}
    for_you, relaxations = select_for_you(opportunities, by_id)

    return {
        "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
        "candidate_paths": [item.model_dump(mode="json") for item in paths],
        "opportunities": [item.model_dump(mode="json") for item in opportunities],
        "for_you": [item.model_dump(mode="json") for item in for_you],
        "diagnostics": {
            "raw_packages_generated": len(rows),
            "path_families_created": len(seeds),
            "packages_collapsed_family_neighborhood": family_pruned,
            "preliminary_decision_budget": max(evaluation_limit, 0),
            "preliminary_decision_runs": len(selected_indices),
            "preliminary_decision_errors": decision_errors,
            "counterparty_dominated_count": sum(
                1
                for path in paths
                if path.bilateral_plausibility
                == BilateralPlausibility.COUNTERPARTY_DOMINATED
            ),
            "focal_dominated_count": sum(
                1
                for path in paths
                if path.bilateral_plausibility
                == BilateralPlausibility.FOCAL_DOMINATED
            ),
            "opportunities_created": len(opportunities),
            "opportunities_attention_ready": sum(
                1
                for opportunity in opportunities
                if opportunity.attention_status == AttentionStatus.WORTH_ATTENTION
            ),
            "for_you_selected": len(for_you),
            "diversity_relaxations": relaxations,
            "changed_state_simulation_calls_during_discovery": 0,
        },
        "authority": {
            "opportunity_aggregation_is_search_owned": True,
            "preliminary_screen_is_decision_owned": True,
            "owner_context_descriptive_only": True,
            "acceptance_probability": None,
            "changed_state_simulation_calls_during_discovery": 0,
            "recommendation_authority": False,
        },
    }
