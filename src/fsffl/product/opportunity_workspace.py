from __future__ import annotations

from .opportunity_search import build_roster_aware_trade_candidates
from .runtime import UserRuntimeContext
from .trade_analysis_runtime import build_private_beta_trade_analysis
from .trade_center import TradeDraft, TradeDraftSide, submit_trade_draft
from .trade_center_view import (
    build_trade_center_browser_view,
    resolve_owned_asset_ref,
)


_SEARCH_ORDERING = "cardinal_market_fit_then_roster_need"
_DECISION_BUDGET_POLICY = "multi_lane_market_focal_counterparty_structural_exploration"


def _empty_workspace(
    *,
    status: str,
    message: str,
    retryable: bool,
    runtime: UserRuntimeContext,
) -> dict[str, object]:
    league_state = runtime.league_state
    return {
        "status": status,
        "message": message,
        "retryable": retryable,
        "league_state_id": league_state.state_id if league_state is not None else None,
        "as_of": league_state.as_of.isoformat() if league_state is not None else None,
        "focal_team_id": runtime.selected_team_id,
        "focal_team_name": None,
        "requirements": {
            "league_state": league_state is not None,
            "managed_team": runtime.selected_team_id is not None,
            "authoritative_cardinal_value": bool(
                runtime.value_evidence is not None
                and runtime.value_evidence.fsffl_cardinal_values
            ),
            "simulation": runtime.simulation_analytics is not None,
        },
        "trade_discovery": {
            "candidate_count": 0,
            "returned_count": 0,
            "truncated": False,
            "ordering": _SEARCH_ORDERING,
            "bilateral_evaluated_count": 0,
            "bilateral_evaluation_limit": 0,
            "bilateral_evaluation_policy": _DECISION_BUDGET_POLICY,
            "candidates": [],
        },
        "available_players": {"count": 0, "players": []},
        "capabilities": {
            "structural_trade_discovery": False,
            "authoritative_value_ordering": False,
            "bilateral_decision_evaluation": False,
            "negotiation_feasibility": False,
            "behavioral_acceptance": False,
            "waiver_materiality": False,
            "post_transaction_simulation": False,
        },
        "authority": {
            "search_role": "candidate_generation_ordering_and_decision_enrichment",
            "recommendation_authority": False,
            "provisional_value_used": False,
            "bilateral_evaluation_budget_is_product_compute_policy": True,
        },
    }


def _evaluate_structural_trade(
    runtime: UserRuntimeContext,
    row: dict[str, object],
) -> dict[str, object]:
    """Attach NEXT-5 bilateral evidence to one already-generated search row."""

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
            f"opportunity:{league_state.state_id}:{focal_team_id}:"
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
    analysis = build_private_beta_trade_analysis(
        runtime,
        proposal,
        focal_team_id=focal_team_id,
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
        "bilateral_decision_evaluated": decision != {},
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
        "post_trade_simulation_attached": bool(
            (analysis.get("availability") or {}).get("competitive_outcomes")
        ),
        "explanation": (
            "Roster-aware structural trade test enriched with the current NEXT-5 bilateral "
            "Decision and negotiation-feasibility shape. Feasibility describes calculated "
            "bilateral consequences; it is not an acceptance probability or recommendation."
        ),
    }


def _receive_asset_ref(row: dict[str, object]) -> str:
    receive = row.get("receive") or []
    if not receive:
        return ""
    first = receive[0]
    return str(first.get("asset_ref", "")) if isinstance(first, dict) else ""


def _optional_strength(row: dict[str, object], key: str) -> float:
    value = row.get(key)
    return float(value) if value is not None else float("inf")


def _select_bilateral_evaluation_indices(
    candidates: list[dict[str, object]],
    *,
    limit: int,
) -> tuple[int, ...]:
    """Allocate scarce Decision work across distinct governed search lenses.

    Cardinal Value remains a cheap market-plausibility coordinate, not the definition
    of the best trade. The first Decision lane preserves the best market-ranked row.
    Separate lanes then sample the strongest focal roster-need fit and the strongest
    counterparty roster-need fit using already-published positional-strength evidence.
    Remaining budget favors structural diversity before falling back to Search rank.

    No lane creates a composite score, trade-value coefficient, fixed acceptability
    cutoff, acceptance probability, or recommendation. The candidate list is not
    reordered. NEXT-5 Decision remains authoritative for bilateral consequences.
    """

    budget = min(max(limit, 0), len(candidates))
    if budget == 0:
        return ()

    selected: list[int] = []
    selected_set: set[int] = set()

    def add(index: int | None) -> None:
        if index is None or len(selected) >= budget or index in selected_set:
            return
        selected.append(index)
        selected_set.add(index)

    # Lane 1: closest governed market-plausibility candidate from Search.
    add(0)

    # Lane 2: best published focal-team roster-need fit, with market rank only as
    # a deterministic tie-breaker. Missing strength evidence does not win the lane.
    focal_index = min(
        range(len(candidates)),
        key=lambda index: (
            _optional_strength(candidates[index], "focal_position_strength_index"),
            index,
        ),
        default=None,
    )
    if focal_index is not None and _optional_strength(
        candidates[focal_index], "focal_position_strength_index"
    ) != float("inf"):
        add(focal_index)

    # Lane 3: best published counterparty need fit, again without scalar blending.
    counterparty_index = min(
        range(len(candidates)),
        key=lambda index: (
            _optional_strength(
                candidates[index], "counterparty_receive_position_strength_index"
            ),
            index,
        ),
        default=None,
    )
    if counterparty_index is not None and _optional_strength(
        candidates[counterparty_index], "counterparty_receive_position_strength_index"
    ) != float("inf"):
        add(counterparty_index)

    # Remaining compute seeks genuinely different structures before duplicating the
    # same counterparty, receive target and package shape. This is coverage policy,
    # not football or economic scoring.
    while len(selected) < budget:
        covered_counterparties = {
            str(candidates[index].get("counterparty_team_id", "")) for index in selected
        }
        covered_targets = {_receive_asset_ref(candidates[index]) for index in selected}
        covered_shapes = {str(candidates[index].get("package_shape", "")) for index in selected}

        next_index = next(
            (
                index
                for index, row in enumerate(candidates)
                if index not in selected_set
                and (
                    str(row.get("counterparty_team_id", "")) not in covered_counterparties
                    or _receive_asset_ref(row) not in covered_targets
                    or str(row.get("package_shape", "")) not in covered_shapes
                )
            ),
            None,
        )
        if next_index is None:
            next_index = next(
                (index for index in range(len(candidates)) if index not in selected_set),
                None,
            )
        if next_index is None:
            break
        add(next_index)

    return tuple(sorted(selected))


def build_opportunity_workspace(
    runtime: UserRuntimeContext,
    *,
    candidate_limit: int = 80,
    bilateral_evaluation_limit: int = 4,
) -> dict[str, object]:
    """Build a responsive Opportunity workspace with progressive governed evidence.

    Search uses Cardinal market plausibility and roster context to generate an ordered
    candidate universe without recommendation authority. A small multi-lane set is
    synchronously enriched through NEXT-5 Decision so a better roster-fit opportunity
    is not hidden merely because another structure is the closest Cardinal match.
    Deeper Decision/materiality work remains behind explicit actions.
    """

    league_state = runtime.league_state
    focal_team_id = runtime.selected_team_id
    if league_state is None:
        return _empty_workspace(
            status="needs_league",
            message="Connect a league before running opportunity discovery.",
            retryable=False,
            runtime=runtime,
        )
    if focal_team_id is None:
        return _empty_workspace(
            status="needs_team",
            message="Select the franchise you manage before running opportunity discovery.",
            retryable=False,
            runtime=runtime,
        )

    values = runtime.value_evidence
    cardinal = {
        row.asset_id: row
        for row in (values.fsffl_cardinal_values if values is not None else ())
    }
    if not cardinal:
        return _empty_workspace(
            status="building_intelligence",
            message=(
                "Current FSFFL Value evidence is still being built. Opportunity discovery "
                "will activate automatically when the governed intelligence refresh finishes."
            ),
            retryable=True,
            runtime=runtime,
        )

    try:
        browser = build_trade_center_browser_view(
            league_state,
            focal_team_id=focal_team_id,
        )
    except ValueError as exc:
        return _empty_workspace(
            status="blocked",
            message=f"Canonical roster context is inconsistent: {exc}",
            retryable=True,
            runtime=runtime,
        )

    candidates = build_roster_aware_trade_candidates(runtime, browser, cardinal)
    total_candidate_count = len(candidates)
    returned = candidates[: max(candidate_limit, 0)]

    evaluation_indices = _select_bilateral_evaluation_indices(
        returned,
        limit=bilateral_evaluation_limit,
    )
    for index in evaluation_indices:
        try:
            returned[index] = _evaluate_structural_trade(runtime, returned[index])
        except ValueError as exc:
            returned[index] = {
                **returned[index],
                "bilateral_decision_evaluated": False,
                "negotiation_feasibility_evaluated": False,
                "decision_error": str(exc),
            }

    rostered_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
    }
    states = {row.player_id: row for row in league_state.player_states}
    available_players = []
    for player in league_state.players:
        if player.player_id in rostered_ids:
            continue
        player_state = states.get(player.player_id)
        value_row = cardinal.get(player.player_id)
        available_players.append(
            {
                "player_id": player.player_id,
                "full_name": player.full_name,
                "position": player.position.value,
                "nfl_team": player.nfl_team,
                "age_years": player_state.age_years if player_state is not None else None,
                "status": player_state.status.value if player_state is not None else "unknown",
                "fsffl_value": value_row.score if value_row is not None else None,
                "action_authority": "diagnostic_only",
                "explanation": (
                    "Currently unowned in canonical State. Availability is descriptive; "
                    "add/drop materiality has not yet been evaluated."
                ),
            }
        )
    available_players.sort(
        key=lambda row: (
            row["fsffl_value"] is None,
            -(row["fsffl_value"] or 0.0),
            str(row["full_name"]),
        )
    )

    return {
        "status": "ready",
        "message": "Current roster-aware opportunity discovery workspace is ready.",
        "retryable": False,
        "league_state_id": league_state.state_id,
        "as_of": league_state.as_of.isoformat(),
        "focal_team_id": focal_team_id,
        "focal_team_name": browser.focal_team.display_name,
        "requirements": {
            "league_state": True,
            "managed_team": True,
            "authoritative_cardinal_value": True,
            "simulation": runtime.simulation_analytics is not None,
        },
        "trade_discovery": {
            "candidate_count": total_candidate_count,
            "returned_count": len(returned),
            "truncated": total_candidate_count > len(returned),
            "ordering": _SEARCH_ORDERING,
            "bilateral_evaluated_count": sum(
                1 for row in returned if row.get("bilateral_decision_evaluated")
            ),
            "bilateral_evaluation_limit": bilateral_evaluation_limit,
            "bilateral_evaluation_policy": _DECISION_BUDGET_POLICY,
            "candidates": returned,
        },
        "available_players": {"count": len(available_players), "players": available_players},
        "capabilities": {
            "structural_trade_discovery": True,
            "authoritative_value_ordering": True,
            "roster_aware_search": runtime.simulation_analytics is not None,
            "two_for_one_consolidation_search": True,
            "bilateral_decision_evaluation": bool(evaluation_indices),
            "negotiation_feasibility": any(
                row.get("negotiation_feasibility_evaluated") for row in returned
            ),
            "behavioral_acceptance": False,
            "waiver_materiality": bool(available_players),
            "post_transaction_simulation": False,
        },
        "authority": {
            "search_role": "candidate_generation_ordering_and_decision_enrichment",
            "recommendation_authority": False,
            "provisional_value_used": False,
            "bilateral_evaluation_budget_is_product_compute_policy": True,
            "decision_budget_coverage_does_not_reorder_candidates": True,
            "decision_budget_market_fit_is_one_lane_not_winner_selection": True,
            "search_order_is_not_a_composite_opportunity_score": True,
            "search_market_fit_has_no_fixed_acceptability_cutoff": True,
            "negotiation_feasibility_is_not_acceptance_probability": True,
        },
    }
