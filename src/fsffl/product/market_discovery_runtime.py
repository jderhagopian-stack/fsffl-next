from __future__ import annotations

from collections import OrderedDict, defaultdict
import logging
from collections.abc import Callable, Iterable, Mapping
from time import monotonic
from typing import Any

from fsffl.forecast import attach_provisional_position_floor_forecasts
from fsffl.forecast.models import ForecastHorizon
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
from fsffl.team_utility import compare_position_strengths, optimize_team_lineup
from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.trade_decision import (
    apply_bilateral_trade,
    assess_package_economics,
    assess_preliminary_bilateral_screen,
    bind_owner_behavior_evidence,
    calculate_bilateral_economic_net,
    live_bounded_materiality_policy,
    live_bounded_package_premium_prior,
    summarize_bilateral_trade_economics,
    summarize_package_concentration,
    resolve_mandatory_roster_cuts,
)

from fsffl.trade_decision.roster_economics import adjust_bilateral_market_net_for_mandatory_cuts

from .behavioral_runtime import cached_behavior_profile_for_team
from .opportunity_posture import calculated_competitive_state
from .runtime import UserRuntimeContext
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import (
    build_trade_center_browser_view,
    owned_asset_index,
    resolve_owned_asset_ref,
)
from .trade_value_adapter import cardinal_market_profiles


DEFAULT_PRELIMINARY_DECISION_BUDGET = 8
DEFAULT_FOR_YOU_LIMIT = 4
_MAX_ALTERNATE_PACKAGES = 2
_logger = logging.getLogger("uvicorn.error")

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


def _objective_family(
    row: dict[str, object],
    source: OpportunitySource,
    *,
    intent: str = "",
) -> str:
    if source != OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT:
        return "upgrade_position"
    return {
        "target": "target_player",
        "shop": "shop_player",
        "position": "target_position",
        "owner": "explore_owner",
        "consolidate": "consolidate_assets",
    }.get(intent, "improve_team")


def _need_dimension(
    row: dict[str, object],
    *,
    intent: str = "",
    intent_value: str = "",
) -> str:
    if intent == "position" and intent_value:
        return intent_value
    if intent == "owner":
        return "OWNER"
    return _target_position(row)


def _target_family(
    row: dict[str, object],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
    intent: str = "",
    intent_value: str = "",
) -> str:
    if exact_target_constraint:
        return exact_target_constraint
    position = _target_position(row)
    if source != OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT:
        return f"{position}:starter_upgrade"
    receive = _receive_refs(row)
    if intent == "target" and receive:
        return receive[0]
    if intent == "position":
        return f"{intent_value or position}:starter_upgrade"
    if intent == "owner":
        owner = intent_value or str(row.get("counterparty_team_id") or "")
        return f"owner:{owner}"
    if intent == "shop":
        return f"shop:{intent_value or 'selected'}:{position}"
    if intent == "consolidate":
        return f"{position}:consolidation_target"
    return f"{position}:starter_upgrade"


def _opportunity_identity(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
    intent: str = "",
    intent_value: str = "",
) -> tuple[str, str, str, str, str]:
    team_id = str(runtime.selected_team_id or "")
    objective = _objective_family(row, source, intent=intent)
    need = _need_dimension(row, intent=intent, intent_value=intent_value)
    target_family = _target_family(
        row,
        source=source,
        exact_target_constraint=exact_target_constraint,
        intent=intent,
        intent_value=intent_value,
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


_ECONOMIC_BAND_ORDER = {
    PreliminaryEconomicBand.ROBUST_OR_ORDINARY.value: 0,
    PreliminaryEconomicBand.BOUNDED_UNCERTAINTY.value: 1,
    PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN.value: 2,
    PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN.value: 3,
    PreliminaryEconomicBand.INCOMPLETE.value: 4,
}


def _cheap_band_rank(row: dict[str, object]) -> int:
    return _ECONOMIC_BAND_ORDER.get(
        str(row.get("preliminary_economic_band") or ""),
        _ECONOMIC_BAND_ORDER[PreliminaryEconomicBand.INCOMPLETE.value],
    )


def _row_dominates(left: dict[str, object], right: dict[str, object]) -> bool:
    """Search-owned Pareto pruning over comparable governed package variants."""

    if str(left.get("package_shape") or "") != str(right.get("package_shape") or ""):
        return False
    if str(left.get("preliminary_economic_band") or "") != str(
        right.get("preliminary_economic_band") or ""
    ):
        return False
    left_gap, left_distance = _row_search_pair(left)
    right_gap, right_distance = _row_search_pair(right)
    left_values = (left_gap, left_distance)
    right_values = (right_gap, right_distance)
    return all(a <= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a < b for a, b in zip(left_values, right_values, strict=True)
    )


def _prune_package_neighborhood(rows: list[dict[str, object]]) -> tuple[dict[str, object], tuple[dict[str, object], ...], int]:
    """Prune one target/counterparty neighborhood after cheap Decision economics.

    Search does not invent an economic score. It consumes the categorical
    preliminary economic band plus its own distance/complexity coordinates and
    removes only rows that are Pareto-dominated on every available governed
    dimension. Materially different shapes/economic bands can therefore survive
    even when they are not the single closest additive Cardinal package.
    """

    survivors = [
        row
        for index, row in enumerate(rows)
        if not any(
            other_index != index and _row_dominates(other, row)
            for other_index, other in enumerate(rows)
        )
    ]
    survivors.sort(
        key=lambda row: (
            _cheap_band_rank(row),
            _row_search_pair(row),
            len(row.get("send") or []),
            int(row.get("package_variant_rank") or 999),
            _send_refs(row),
        )
    )
    if not survivors:
        survivors = sorted(
            rows,
            key=lambda row: (
                _cheap_band_rank(row),
                _row_search_pair(row),
                len(row.get("send") or []),
                _send_refs(row),
            ),
        )[:1]

    kept_rows: list[dict[str, object]] = [survivors[0]]
    kept_shapes = {str(survivors[0].get("package_shape") or "unknown")}
    for row in survivors[1:]:
        shape = str(row.get("package_shape") or "unknown")
        if shape in kept_shapes:
            continue
        kept_rows.append(row)
        kept_shapes.add(shape)
        if len(kept_rows) >= 1 + _MAX_ALTERNATE_PACKAGES:
            break
    if len(kept_rows) < 1 + _MAX_ALTERNATE_PACKAGES:
        for row in survivors[1:]:
            if row in kept_rows:
                continue
            kept_rows.append(row)
            if len(kept_rows) >= 1 + _MAX_ALTERNATE_PACKAGES:
                break

    representative = kept_rows[0]
    alternates = tuple(kept_rows[1:])
    pruned = max(0, len(rows) - len(kept_rows))
    return representative, alternates, pruned


def _build_path_seeds(
    runtime: UserRuntimeContext,
    rows: Iterable[dict[str, object]],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
    intent: str = "",
    intent_value: str = "",
) -> tuple[list[dict[str, object]], int]:
    grouped: OrderedDict[tuple[str, str, tuple[str, ...]], list[dict[str, object]]] = OrderedDict()
    for row in rows:
        opportunity_id, _, _, _, _ = _opportunity_identity(
            runtime,
            row,
            source=source,
            exact_target_constraint=exact_target_constraint,
            intent=intent,
            intent_value=intent_value,
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


def _proposal_from_row(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    prefix: str,
    asset_index: Mapping[tuple[str, str], object] | None = None,
):
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        raise ValueError("trade screen requires loaded State and managed team")
    counterparty_team_id = str(row.get("counterparty_team_id") or "")
    send = row.get("send") or []
    receive = row.get("receive") or []
    if not counterparty_team_id or not send or not receive:
        raise ValueError("trade screen requires bilateral package assets")

    def resolve(team_id: str, asset_ref: str):
        if asset_index is not None:
            cached = asset_index.get((team_id, asset_ref))
            if cached is not None:
                return cached
        return resolve_owned_asset_ref(
            league_state,
            team_id=team_id,
            asset_ref=asset_ref,
        )

    focal_assets = tuple(
        resolve(focal_team_id, str(item["asset_ref"]))
        for item in send
    )
    counterparty_assets = tuple(
        resolve(counterparty_team_id, str(item["asset_ref"]))
        for item in receive
    )
    draft = TradeDraft(
        draft_id=(
            f"{prefix}:{league_state.state_id}:{focal_team_id}:"
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
    return submit_trade_draft(draft, as_of=league_state.as_of)


def _economic_side(payload: dict[str, Any] | None, team_id: str) -> dict[str, Any]:
    if not payload:
        return {}
    for key in ("side_a", "side_b"):
        side = payload.get(key) or {}
        if str(side.get("team_id") or "") == team_id:
            return side
    return {}


def _cheap_economic_band(
    runtime: UserRuntimeContext,
    row: dict[str, object],
) -> PreliminaryEconomicBand:
    league_state = runtime.league_state
    focal_team_id = str(runtime.selected_team_id or "")
    counterparty_team_id = str(row.get("counterparty_team_id") or "")
    net = row.get("economic_net")
    focal = _economic_side(net if isinstance(net, dict) else None, focal_team_id)
    counterparty = _economic_side(
        net if isinstance(net, dict) else None,
        counterparty_team_id,
    )
    focal_market = focal.get("market") or {}
    counterparty_market = counterparty.get("market") or {}
    if (
        league_state is None
        or focal_market.get("status") != "complete"
        or counterparty_market.get("status") != "complete"
        or focal_market.get("mean_delta") is None
        or counterparty_market.get("mean_delta") is None
    ):
        return PreliminaryEconomicBand.INCOMPLETE

    try:
        threshold = live_bounded_materiality_policy(
            as_of=league_state.as_of
        ).economic.mean_value_abs
    except ValueError:
        return PreliminaryEconomicBand.INCOMPLETE

    focal_delta = float(focal_market["mean_delta"])
    counterparty_delta = float(counterparty_market["mean_delta"])
    package = row.get("package_economics")
    resolution = str(package.get("resolution") or "") if isinstance(package, dict) else ""
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


def evaluate_candidate_economics(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    profiles=None,
    market_values: Mapping[str, float] | None = None,
    asset_index: Mapping[tuple[str, str], object] | None = None,
) -> dict[str, object]:
    """Attach cheap Decision-owned economics before Search family pruning.

    This stage intentionally excludes lineup optimization, Team Utility, owner
    behavior and changed-state Simulation. It exists only to prevent additive
    Search closeness from deciding which package survives into the bounded
    bilateral screen.
    """

    league_state = runtime.league_state
    if league_state is None:
        return {
            **row,
            "preliminary_economic_band": PreliminaryEconomicBand.INCOMPLETE.value,
            "cheap_economic_screen_complete": False,
        }
    profiles = profiles if profiles is not None else cardinal_market_profiles(
        runtime.value_evidence
    )
    if not profiles:
        return {
            **row,
            "preliminary_economic_band": PreliminaryEconomicBand.INCOMPLETE.value,
            "cheap_economic_screen_complete": False,
        }

    proposal = _proposal_from_row(
        runtime,
        row,
        prefix="market-economic",
        asset_index=asset_index,
    )
    economics = summarize_bilateral_trade_economics(
        proposal,
        profiles,
        model_version="market-discovery-economic-screen-v1",
    )
    economic_net = calculate_bilateral_economic_net(
        economics,
        model_version="market-discovery-economic-net-v1",
    )
    market_values = (
        market_values
        if market_values is not None
        else {
            asset_id: profile.market_price.distribution.mean
            for asset_id, profile in profiles.items()
            if profile.market_price is not None
        }
    )
    concentration = (
        summarize_package_concentration(
            proposal,
            market_values,
            model_version="market-discovery-package-concentration-v1",
        )
        if market_values
        else None
    )
    package_economics = (
        assess_package_economics(
            concentration,
            prior=live_bounded_package_premium_prior(as_of=proposal.as_of),
            model_version="market-discovery-package-economic-screen-v1",
        )
        if concentration is not None
        else None
    )
    result = {
        **row,
        "economics": economics.model_dump(mode="json"),
        "economic_net": economic_net.model_dump(mode="json"),
        "package_concentration": (
            concentration.model_dump(mode="json")
            if concentration is not None
            else None
        ),
        "package_economics": (
            package_economics.model_dump(mode="json")
            if package_economics is not None
            else None
        ),
        "cheap_economic_screen_complete": True,
        "cheap_economic_screen_authority": "decision",
    }
    result["preliminary_economic_band"] = _cheap_economic_band(
        runtime,
        result,
    ).value
    return result


def evaluate_candidate_path(
    runtime: UserRuntimeContext,
    row: dict[str, object],
    *,
    profiles=None,
    market_values: Mapping[str, float] | None = None,
    asset_index: Mapping[tuple[str, str], object] | None = None,
    effective_forecasts=None,
    baseline_by_team: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Attach the bounded cheap Decision-owned pre-Simulation bilateral screen.

    Market discovery deliberately does not invoke the full Trade Center roster
    consequence analysis here. It consumes already-governed baseline lineups,
    computes only the changed-roster lineups needed for replacement effects and
    mandatory-cut legality, and preserves exact Simulation for user-selected deep
    investigation.
    """

    started = monotonic()
    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None or focal_team_id is None:
        return row

    counterparty_team_id = str(row["counterparty_team_id"])
    if not (row.get("send") or []) or not (row.get("receive") or []):
        return row
    forecast_evidence = runtime.forecast_evidence
    if forecast_evidence is None:
        raise ValueError("preliminary bilateral screen requires current Forecast evidence")
    if effective_forecasts is None:
        forecasts = (
            forecast_evidence.raw_forecasts
            + forecast_evidence.league_scored_forecasts
        )
        effective_forecasts = attach_provisional_position_floor_forecasts(
            league_state,
            forecasts,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
        )
    proposal = _proposal_from_row(
        runtime,
        row,
        prefix="market-prelim",
        asset_index=asset_index,
    )
    scenario = apply_bilateral_trade(league_state, proposal)
    state_validated = monotonic()

    if baseline_by_team is None:
        simulation = runtime.simulation_analytics
        baseline_by_team = {
            view.team_id: view.optimized_lineup
            for view in (simulation.team_views if simulation is not None else ())
            if view.optimized_lineup is not None
        }

    def lineup(state, team_id):
        baseline = (
            baseline_by_team.get(team_id)
            if state.state_id == league_state.state_id
            else None
        )
        if baseline is not None:
            return baseline
        return optimize_team_lineup(
            state,
            effective_forecasts,
            team_id=team_id,
            as_of=state.as_of,
            horizon=ForecastHorizon.SEASON,
            allow_unfilled_slots=True,
            model_version="market-preliminary-screen-lineup-v1",
        )

    after_trade_lineups = {
        team_id: lineup(scenario.after, team_id)
        for team_id in (focal_team_id, counterparty_team_id)
    }
    protected = {
        team_id: frozenset(item.player_id for item in current.assignments)
        for team_id, current in after_trade_lineups.items()
    }
    profiles = profiles if profiles is not None else cardinal_market_profiles(
        runtime.value_evidence
    )
    market_values = (
        market_values
        if market_values is not None
        else {
            asset_id: profile.market_price.distribution.mean
            for asset_id, profile in profiles.items()
            if profile.market_price is not None
        }
    )
    roster_resolution = resolve_mandatory_roster_cuts(
        scenario.after,
        protected_player_ids_by_team=protected,
        market_values=market_values,
    )
    legal_after = roster_resolution.league_state
    trade_team_resolutions = tuple(
        item
        for item in roster_resolution.resolutions
        if item.team_id in {focal_team_id, counterparty_team_id}
    )
    has_cuts = any(item.required_cut_count > 0 for item in trade_team_resolutions)
    final_lineups = (
        {
            team_id: lineup(legal_after, team_id)
            for team_id in (focal_team_id, counterparty_team_id)
        }
        if has_cuts
        else after_trade_lineups
    )
    lineup_finished = monotonic()

    comparisons = {
        team_id: compare_position_strengths(
            lineup(league_state, team_id),
            final_lineups[team_id],
            model_version="market-preliminary-position-strength-v1",
        )
        for team_id in (focal_team_id, counterparty_team_id)
    }

    economics = summarize_bilateral_trade_economics(
        proposal,
        profiles,
        model_version="market-preliminary-trade-economics-v1",
    )
    economic_net = calculate_bilateral_economic_net(
        economics,
        model_version="market-preliminary-economic-net-v1",
    )
    adjusted_market = adjust_bilateral_market_net_for_mandatory_cuts(
        economic_net,
        trade_team_resolutions,
    )
    screen = assess_preliminary_bilateral_screen(
        proposal,
        focal_team_id=focal_team_id,
        roster_adjusted_market_net=adjusted_market,
        position_strength_comparisons=comparisons,
    )
    decision_finished = monotonic()

    profile = cached_behavior_profile_for_team(
        league_state,
        counterparty_team_id,
    )
    behavioral = (
        bind_owner_behavior_evidence(
            proposal,
            accepting_team_id=counterparty_team_id,
            profile=profile,
        )
        if profile is not None
        else None
    )
    feasibility_shape = {
        "bilateral_supported": "mutual_gain_candidate",
        "counterparty_dominated": "counterparty_dominated",
        "incomplete": "incomplete",
    }.get(screen.shape.value, "mixed")
    cut_cost_complete = all(
        item.required_cut_count == 0 or item.cut_market_value_total is not None
        for item in trade_team_resolutions
    )
    completed = monotonic()

    return {
        **row,
        "preliminary_decision_screen_evaluated": True,
        "bilateral_decision_evaluated": True,
        "decision_shape": screen.shape.value,
        "focal_decision_shape": screen.focal.shape.value,
        "counterparty_decision_shape": screen.counterparty.shape.value,
        "negotiation_feasibility_shape": feasibility_shape,
        "negotiation_feasibility_evaluated": True,
        "acceptance_probability": None,
        "focal_roster_delta": comparisons[focal_team_id].model_dump(mode="json"),
        "counterparty_roster_delta": comparisons[counterparty_team_id].model_dump(mode="json"),
        "behavioral_evidence_attached": behavioral is not None,
        "behavioral_context": (
            behavioral.model_dump(mode="json") if behavioral is not None else None
        ),
        "post_trade_simulation_attached": False,
        "economics": economics.model_dump(mode="json"),
        "economic_net": economic_net.model_dump(mode="json"),
        "roster_adjusted_market_net": adjusted_market.model_dump(mode="json"),
        "roster_legality": [
            item.model_dump(mode="json") for item in trade_team_resolutions
        ],
        "position_strength_comparisons": {
            team_id: comparison.model_dump(mode="json")
            for team_id, comparison in comparisons.items()
        },
        "preliminary_bilateral_screen": screen.model_dump(mode="json"),
        "decision_completeness": {
            "status": "partial_pre_simulation",
            "simulation_backed": False,
            "final_disposition_available": False,
            "decision_scope": "lightweight_bilateral_roster_economic_screen",
            "missing_authorities": (
                "NEXT-4 Simulation competitive outcomes",
                "NEXT-5 full material assessment and final trade disposition",
            ),
        },
        "availability": {
            "roster_consequences": True,
            "position_strength": True,
            "negotiation_feasibility": True,
            "market_economics": True,
            "economic_net": True,
            "competitive_outcomes": False,
            "championship_probability": False,
            "mandatory_cut_cost": cut_cost_complete,
            "package_concentration_evidence": row.get("package_concentration") is not None,
            "bounded_package_economic_guard": row.get("package_economics") is not None,
            "behavioral_evidence": behavioral is not None,
            "acceptance_probability": False,
            "final_trade_disposition": False,
        },
        "preliminary_screen_timing_ms": {
            "state_validation": round((state_validated - started) * 1000.0, 3),
            "changed_lineup_and_legality": round(
                (lineup_finished - state_validated) * 1000.0,
                3,
            ),
            "replacement_and_economic_screen": round(
                (decision_finished - lineup_finished) * 1000.0,
                3,
            ),
            "behavioral_context": round(
                (completed - decision_finished) * 1000.0,
                3,
            ),
            "total": round((completed - started) * 1000.0, 3),
        },
        "explanation": (
            "Representative Candidate Path completed the bounded lightweight "
            "pre-Simulation Decision screen using roster legality, mandatory-cut "
            "economics and optimized starter replacement effects. It is not an "
            "acceptance probability, final disposition, or season-outcome claim."
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
    if focal_shape in {"uniform_loss", "dominated", "incomplete", ""}:
        return (
            BilateralPlausibility.FOCAL_DOMINATED
            if focal_shape in {"uniform_loss", "dominated"}
            else BilateralPlausibility.INCOMPLETE
        )
    if (
        feasibility == "counterparty_dominated"
        or counterparty_shape in {"uniform_loss", "dominated"}
    ):
        return BilateralPlausibility.COUNTERPARTY_DOMINATED
    if feasibility == "incomplete" or counterparty_shape in {"incomplete", ""}:
        return BilateralPlausibility.INCOMPLETE
    if economic_band in {
        PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN,
        PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN,
    }:
        return BilateralPlausibility.BILATERAL_FRICTION
    if (
        feasibility == "mutual_gain_candidate"
        or (
            focal_shape == "supported"
            and counterparty_shape == "supported"
        )
    ):
        return BilateralPlausibility.BILATERAL_SUPPORTED
    if feasibility in {"mixed", "neutral"}:
        return BilateralPlausibility.BILATERAL_FRICTION
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
        return str(row.get("focal_decision_shape") or "") in {"uniform_gain", "supported"}
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
    reason_codes = [
        "search_family_representative",
        f"economic:{economic_band.value}",
        f"bilateral:{plausibility.value}",
        (
            "preliminary_decision_screen_complete"
            if row.get("bilateral_decision_evaluated")
            else "preliminary_decision_screen_pending"
        ),
        (
            "owner_context_observed"
            if owner_status == "observed_history"
            else "owner_context_unavailable"
        ),
    ]
    if alternates:
        reason_codes.append("package_variants_clustered")
    if missing:
        reason_codes.append("evidence_incomplete")

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
        reason_codes=tuple(reason_codes),
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


_BILATERAL_PATH_ORDER = {
    BilateralPlausibility.BILATERAL_SUPPORTED: 0,
    BilateralPlausibility.BILATERAL_FRICTION: 1,
    BilateralPlausibility.INCOMPLETE: 2,
    BilateralPlausibility.COUNTERPARTY_DOMINATED: 3,
    BilateralPlausibility.FOCAL_DOMINATED: 4,
}
_ECONOMIC_PATH_ORDER = {
    PreliminaryEconomicBand.ROBUST_OR_ORDINARY: 0,
    PreliminaryEconomicBand.BOUNDED_UNCERTAINTY: 1,
    PreliminaryEconomicBand.COUNTERPARTY_ECONOMIC_STRAIN: 2,
    PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN: 3,
    PreliminaryEconomicBand.INCOMPLETE: 4,
}


def _candidate_path_order(path: CandidatePath) -> tuple[object, ...]:
    row = path.representative_package
    return (
        _BILATERAL_PATH_ORDER[path.bilateral_plausibility],
        _ECONOMIC_PATH_ORDER[path.economic_screen],
        0 if path.evidence_completeness == "complete" else 1,
        float(row.get("market_gap_ratio"))
        if isinstance(row.get("market_gap_ratio"), (int, float))
        else float("inf"),
        float(row.get("search_distance"))
        if isinstance(row.get("search_distance"), (int, float))
        else float("inf"),
        path.path_id,
    )


def _aggregate_opportunities(
    runtime: UserRuntimeContext,
    seeds: list[dict[str, object]],
    paths: list[CandidatePath],
    *,
    source: OpportunitySource,
    exact_target_constraint: str | None,
    intent: str = "",
    intent_value: str = "",
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
            intent=intent,
            intent_value=intent_value,
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
        survivors = sorted(
            (
                path
                for path in related
                if _path_can_support_attention(
                    path.representative_package,
                    path.economic_screen,
                    path.bilateral_plausibility,
                )
            ),
            key=_candidate_path_order,
        )
        screened = sorted(
            (
                path
                for path in related
                if path.deep_evaluation_status == DeepEvaluationStatus.PRELIM_SCREENED
            ),
            key=_candidate_path_order,
        )
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
        reason_codes = [
            f"attention:{attention.value}",
            f"strategic:{('explicit_market_intent' if source == OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT else ('current_position_need' if row.get('focal_position_strength_rank') is not None else 'market_structure'))}",
            f"economic:{economic.value}",
            f"bilateral:{bilateral.value}",
        ]
        if survivors:
            reason_codes.append("attention_eligible_path_present")
        elif screened:
            reason_codes.append("screened_path_requires_more_review")
        elif related:
            reason_codes.append("market_structure_only")
        else:
            reason_codes.append("no_candidate_path")
        if len(related) > len(path_ids):
            reason_codes.append("alternate_paths_clustered")
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
                    "explicit_market_intent"
                    if source == OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT
                    else (
                        "current_position_need"
                        if row.get("focal_position_strength_rank") is not None
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
                reason_codes=tuple(reason_codes),
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

    ordered = sorted(
        eligible,
        key=lambda item: (
            0 if item.strategic_relevance == "current_position_need" else 1,
            _BILATERAL_PATH_ORDER[item.bilateral_plausibility],
            _ECONOMIC_PATH_ORDER[item.preliminary_economic_band],
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
    intent: str = "",
    intent_value: str = "",
    search_generation_diagnostics: dict[str, object] | None = None,
    evaluator: TradeEvaluator = evaluate_candidate_path,
    asset_index: Mapping[tuple[str, str], object] | None = None,
) -> dict[str, object]:
    """Build governed Opportunity/Path output from raw Search rows."""

    started = monotonic()
    profiles = cardinal_market_profiles(runtime.value_evidence)
    market_values = {
        asset_id: profile.market_price.distribution.mean
        for asset_id, profile in profiles.items()
        if profile.market_price is not None
    }
    if asset_index is None and runtime.league_state is not None and runtime.selected_team_id is not None:
        try:
            asset_index = owned_asset_index(
                build_trade_center_browser_view(
                    runtime.league_state,
                    focal_team_id=runtime.selected_team_id,
                )
            )
        except ValueError:
            asset_index = None
    economically_screened_rows: list[dict[str, object]] = []
    cheap_economic_errors = 0
    for raw_row in rows:
        try:
            economically_screened_rows.append(
                evaluate_candidate_economics(
                    runtime,
                    dict(raw_row),
                    profiles=profiles,
                    market_values=market_values,
                    asset_index=asset_index,
                )
            )
        except ValueError as exc:
            cheap_economic_errors += 1
            economically_screened_rows.append(
                {
                    **raw_row,
                    "preliminary_economic_band": PreliminaryEconomicBand.INCOMPLETE.value,
                    "cheap_economic_screen_complete": False,
                    "cheap_economic_screen_error": str(exc),
                }
            )

    economics_finished = monotonic()
    seeds, family_pruned = _build_path_seeds(
        runtime,
        economically_screened_rows,
        source=source,
        exact_target_constraint=exact_target_constraint,
        intent=intent,
        intent_value=intent_value,
    )
    family_finished = monotonic()
    selected_indices = set(
        select_preliminary_screen_indices(seeds, limit=evaluation_limit)
    )
    effective_forecasts = None
    baseline_by_team = None
    preliminary_shared_error: ValueError | None = None
    if (
        selected_indices
        and evaluator is evaluate_candidate_path
        and runtime.league_state is not None
        and runtime.forecast_evidence is not None
    ):
        try:
            forecasts = (
                runtime.forecast_evidence.raw_forecasts
                + runtime.forecast_evidence.league_scored_forecasts
            )
            effective_forecasts = attach_provisional_position_floor_forecasts(
                runtime.league_state,
                forecasts,
                as_of=runtime.league_state.as_of,
                horizon=ForecastHorizon.SEASON,
            )
            simulation = runtime.simulation_analytics
            baseline_by_team = {
                view.team_id: view.optimized_lineup
                for view in (simulation.team_views if simulation is not None else ())
                if view.optimized_lineup is not None
            }
        except ValueError as exc:
            preliminary_shared_error = exc
    paths: list[CandidatePath] = []
    decision_errors = 0
    for index, seed in enumerate(seeds):
        row = dict(seed["representative"])
        if index in selected_indices:
            try:
                if evaluator is evaluate_candidate_path:
                    if preliminary_shared_error is not None:
                        raise ValueError(str(preliminary_shared_error))
                    row = evaluate_candidate_path(
                        runtime,
                        row,
                        profiles=profiles,
                        market_values=market_values,
                        asset_index=asset_index,
                        effective_forecasts=effective_forecasts,
                        baseline_by_team=baseline_by_team,
                    )
                else:
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

    decision_finished = monotonic()
    hypotheses, opportunities = _aggregate_opportunities(
        runtime,
        seeds,
        paths,
        source=source,
        exact_target_constraint=exact_target_constraint,
        intent=intent,
        intent_value=intent_value,
    )
    by_id = {path.path_id: path for path in paths}
    for_you, relaxations = select_for_you(opportunities, by_id)
    completed = monotonic()
    _logger.info(
        "FSFFL Market discovery funnel scope=%s rows=%d counterparties=%s/%s targets=%s/%s "
        "economic_ms=%.3f family_ms=%.3f prelim_runs=%d prelim_ms=%.3f opportunities=%d "
        "for_you=%d simulation_calls=0 cache_hit=%s total_ms=%.3f",
        (
            search_generation_diagnostics.get("scope_label")
            if search_generation_diagnostics
            else None
        ),
        len(rows),
        (
            search_generation_diagnostics.get("counterparties_admitted_pre_package")
            if search_generation_diagnostics
            else None
        ),
        (
            search_generation_diagnostics.get("counterparties_considered")
            if search_generation_diagnostics
            else None
        ),
        (
            search_generation_diagnostics.get("targets_admitted_pre_package")
            if search_generation_diagnostics
            else None
        ),
        (
            search_generation_diagnostics.get("targets_considered")
            if search_generation_diagnostics
            else None
        ),
        (economics_finished - started) * 1000.0,
        (family_finished - economics_finished) * 1000.0,
        len(selected_indices),
        (decision_finished - family_finished) * 1000.0,
        len(opportunities),
        len(for_you),
        (
            search_generation_diagnostics.get("search_cache_hit")
            if search_generation_diagnostics
            else None
        ),
        (completed - started) * 1000.0,
    )
    search_timing = (
        dict(search_generation_diagnostics.get("timing_ms") or {})
        if search_generation_diagnostics
        and isinstance(search_generation_diagnostics.get("timing_ms"), dict)
        else {}
    )

    return {
        "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
        "candidate_paths": [item.model_dump(mode="json") for item in paths],
        "opportunities": [item.model_dump(mode="json") for item in opportunities],
        "for_you": [item.model_dump(mode="json") for item in for_you],
        "diagnostics": {
            "hypotheses_generated": len(hypotheses),
            "scope_label": (
                search_generation_diagnostics.get("scope_label")
                if search_generation_diagnostics
                else None
            ),
            "focal_need_positions": (
                list(search_generation_diagnostics.get("focal_need_positions") or [])
                if search_generation_diagnostics
                else []
            ),
            "counterparties_considered": (
                int(search_generation_diagnostics.get("counterparties_considered", 0))
                if search_generation_diagnostics
                else 0
            ),
            "counterparties_admitted_pre_package": (
                int(search_generation_diagnostics.get("counterparties_admitted_pre_package", 0))
                if search_generation_diagnostics
                else 0
            ),
            "targets_considered": (
                int(search_generation_diagnostics.get("targets_considered", 0))
                if search_generation_diagnostics
                else len(
                    {
                        asset_ref
                        for row in rows
                        for asset_ref in _receive_refs(row)
                    }
                )
            ),
            "targets_admitted_pre_package": (
                int(search_generation_diagnostics.get("targets_admitted_pre_package", 0))
                if search_generation_diagnostics
                else len(
                    {
                        asset_ref
                        for row in rows
                        for asset_ref in _receive_refs(row)
                    }
                )
            ),
            "send_assets_considered": (
                int(search_generation_diagnostics.get("send_assets_considered", 0))
                if search_generation_diagnostics
                else 0
            ),
            "send_assets_admitted_for_counterparty_need": (
                int(search_generation_diagnostics.get("send_assets_admitted_for_counterparty_need", 0))
                if search_generation_diagnostics
                else 0
            ),
            "admission_rejection_reasons": (
                dict(search_generation_diagnostics.get("admission_rejection_reasons") or {})
                if search_generation_diagnostics
                and isinstance(search_generation_diagnostics.get("admission_rejection_reasons"), dict)
                else {}
            ),
            "raw_packages_generated": len(rows),
            "raw_packages_generated_pre_dedup": (
                int(search_generation_diagnostics.get("raw_packages_generated_pre_dedup", len(rows)))
                if search_generation_diagnostics
                else len(rows)
            ),
            "packages_removed_exact_duplicate": (
                int(search_generation_diagnostics.get("packages_removed_exact_duplicate", 0))
                if search_generation_diagnostics
                else 0
            ),
            "packages_screened_economic": len(economically_screened_rows),
            "packages_economic_incomplete": sum(
                1
                for row in economically_screened_rows
                if row.get("preliminary_economic_band")
                == PreliminaryEconomicBand.INCOMPLETE.value
            ),
            "cheap_economic_screen_errors": cheap_economic_errors,
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
            "opportunities_suppressed": sum(
                1
                for opportunity in opportunities
                if opportunity.attention_status == AttentionStatus.SUPPRESSED
            ),
            "opportunities_market_match_only": sum(
                1
                for opportunity in opportunities
                if opportunity.attention_status == AttentionStatus.MARKET_MATCH_ONLY
            ),
            "opportunities_attention_ready": sum(
                1
                for opportunity in opportunities
                if opportunity.attention_status == AttentionStatus.WORTH_ATTENTION
            ),
            "for_you_selected": len(for_you),
            "diversity_relaxations": relaxations,
            "changed_state_simulation_calls_during_discovery": 0,
            "search_cache_hit": (
                bool(search_generation_diagnostics.get("search_cache_hit"))
                if search_generation_diagnostics
                and "search_cache_hit" in search_generation_diagnostics
                else None
            ),
            "search_cache_elapsed_ms": (
                search_generation_diagnostics.get("search_cache_elapsed_ms")
                if search_generation_diagnostics
                else None
            ),
            "timing_ms": {
                "search_generation": search_timing,
                "cheap_economic_screen": round(
                    (economics_finished - started) * 1000.0,
                    3,
                ),
                "family_prune_and_seed": round(
                    (family_finished - economics_finished) * 1000.0,
                    3,
                ),
                "preliminary_decision_screen": round(
                    (decision_finished - family_finished) * 1000.0,
                    3,
                ),
                "opportunity_aggregation_and_diversity": round(
                    (completed - decision_finished) * 1000.0,
                    3,
                ),
                "market_discovery_total": round(
                    (completed - started) * 1000.0,
                    3,
                ),
            },
        },
        "authority": {
            "opportunity_aggregation_is_search_owned": True,
            "cheap_economic_screen_is_decision_owned": True,
            "preliminary_screen_is_decision_owned": True,
            "owner_context_descriptive_only": True,
            "acceptance_probability": None,
            "changed_state_simulation_calls_during_discovery": 0,
            "recommendation_authority": False,
        },
    }
