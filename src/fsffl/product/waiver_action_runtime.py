from __future__ import annotations

from typing import Any, Callable

from fsffl.opportunity import (
    EvidenceCompleteness,
    WaiverMove,
    assess_waiver_materiality,
    candidate_from_waiver_evaluation,
)
from fsffl.team_utility import AssetPortfolioDelta, TeamScenarioDelta
from fsffl.trade_decision import live_bounded_materiality_policy

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult
from .waiver_simulation_runtime import build_waiver_simulation_comparison


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-waiver-action-v1"


def _cardinal_scores(value_evidence) -> dict[str, object]:
    if value_evidence is None:
        return {}
    return {row.asset_id: row for row in value_evidence.fsffl_cardinal_values}


def _economic_delta(runtime: Any, move: WaiverMove, policy) -> AssetPortfolioDelta | None:
    scores = _cardinal_scores(runtime.value_evidence)
    add = scores.get(move.add_player_id)
    drop = scores.get(move.drop_player_id) if move.drop_player_id is not None else None
    if add is None or (move.drop_player_id is not None and drop is None):
        return None
    if add.scale != policy.economic.scale:
        raise ValueError("waiver add Value scale does not match governed economic materiality policy")
    if drop is not None and drop.scale != policy.economic.scale:
        raise ValueError("waiver drop Value scale does not match governed economic materiality policy")
    mean_delta = add.score - (drop.score if drop is not None else 0.0)
    return AssetPortfolioDelta(mean_value=mean_delta, stddev_value=0.0)


def _complete(delta: TeamScenarioDelta) -> bool:
    competitive = delta.competitive
    resilience = delta.resilience
    return all(
        value is not None
        for value in (
            competitive.expected_wins if competitive else None,
            competitive.playoff_probability if competitive else None,
            competitive.championship_probability if competitive else None,
            resilience.largest_single_player_lineup_drop if resilience else None,
            delta.asset_portfolio.mean_value if delta.asset_portfolio else None,
        )
    )


def build_actionable_waiver_comparison(
    runtime: Any,
    move: WaiverMove,
    *,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Join governed waiver evidence without creating a new desirability score.

    NEXT-6 owns the candidate, canonical State owns legality, NEXT-3 owns the
    add/drop market-value delta, NEXT-4 owns changed-roster competitive outcomes,
    and the shared Decision materiality policy interprets practical significance.
    Action authority is granted only when every required channel is present and the
    existing waiver assessment returns SUPPORT. Missing evidence fails closed.
    """

    league_state = runtime.league_state
    if league_state is None:
        raise ValueError("waiver action evaluation requires a loaded league state")
    if runtime.selected_team_id is None:
        raise ValueError("waiver action evaluation requires a selected franchise")
    if move.focal_team_id != runtime.selected_team_id:
        raise ValueError("waiver action move must describe the selected franchise")

    comparison = build_waiver_simulation_comparison(
        runtime,
        move,
        simulation_loader=simulation_loader,
    )
    policy = live_bounded_materiality_policy(as_of=league_state.as_of)
    delta = TeamScenarioDelta.model_validate(comparison["team_delta"])
    delta = delta.model_copy(update={"asset_portfolio": _economic_delta(runtime, move, policy)})
    completeness = EvidenceCompleteness.COMPLETE if _complete(delta) else EvidenceCompleteness.PARTIAL
    assessment = assess_waiver_materiality(
        delta,
        as_of=league_state.as_of,
        competitive_policy=policy.competitive,
        economic_policy=policy.economic,
        economic_scale=policy.economic.scale,
        model_version=f"{_PRODUCT_MODEL_VERSION}:materiality",
    )
    candidate = candidate_from_waiver_evaluation(
        candidate_id=(
            f"waiver:{league_state.state_id}:{move.focal_team_id}:"
            f"{move.add_player_id}:{move.drop_player_id or 'open-slot'}"
        ),
        focal_team_id=move.focal_team_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        evidence_completeness=completeness,
        assessment=assessment,
        search_model_version=f"{_PRODUCT_MODEL_VERSION}:candidate",
    )

    return {
        **comparison,
        "team_delta": delta.model_dump(mode="json"),
        "materiality_policy": policy.model_dump(mode="json"),
        "material_assessment": assessment.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "action_authority": candidate.action_authority.value,
        "authority": {
            **comparison["authority"],
            "market_value": "NEXT-3 Value authoritative Cardinal score",
            "materiality": "shared governed Decision materiality policy",
            "waiver_action": "NEXT-6 Opportunity candidate authority",
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
