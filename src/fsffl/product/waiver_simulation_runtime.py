from __future__ import annotations

from typing import Any, Callable

from fsffl.opportunity.waiver import WaiverMove, apply_waiver_move
from fsffl.team_utility import (
    compare_counterfactual_simulation_results,
    compare_team_utility_vectors,
)

from .runtime import LiveForecastEvidence
from .scenario_cache import (
    ScenarioComputationStage,
    run_progressive_scenario_simulation,
)
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-waiver-simulation-v2:scenario-cache"


def _utility_for_team(result: LiveSimulationAnalyticsResult, team_id: str):
    view = next((item for item in result.team_views if item.team_id == team_id), None)
    if view is None or view.utility is None:
        raise ValueError(f"simulation utility is unavailable for {team_id}")
    return view.utility


def build_waiver_simulation_comparison(
    runtime: Any,
    move: WaiverMove,
    *,
    simulation_loader: SimulationLoader,
    scenario_stage: ScenarioComputationStage = ScenarioComputationStage.CONFIRMATION,
) -> dict[str, object]:
    """Run one governed add/drop scenario stage through NEXT-4 Simulation.

    Product does not score waiver desirability here. NEXT-6 owns candidate search,
    NEXT-4 owns competitive outcomes, and materiality remains a separate governed
    interpretation step with explicit policies. Screening/provisional stages are
    diagnostic previews; confirmation or exact canonical competitive reuse is
    authoritative. Exact repeated changed States may reuse the exact stage result.
    """

    league_state = runtime.league_state
    forecast_evidence = runtime.forecast_evidence
    baseline = runtime.simulation_analytics
    if league_state is None:
        raise ValueError("waiver simulation requires a loaded league state")
    if move.focal_team_id != runtime.selected_team_id:
        raise ValueError("waiver move must describe the selected franchise")
    if forecast_evidence is None or not forecast_evidence.league_scored_forecasts:
        raise ValueError("waiver simulation requires current NEXT-2 forecast evidence")
    if baseline is None:
        raise ValueError("waiver simulation requires a current NEXT-4 baseline simulation")

    changed_state = apply_waiver_move(league_state, move=move)
    changed, cache_hit, computation = run_progressive_scenario_simulation(
        league_state,
        changed_state,
        forecast_evidence,
        baseline,
        simulation_loader=simulation_loader,
        stage=scenario_stage,
    )
    baseline_utility = _utility_for_team(baseline, move.focal_team_id)
    changed_utility = _utility_for_team(changed, move.focal_team_id)
    simulation_delta = compare_counterfactual_simulation_results(
        baseline.simulation_result,
        changed.simulation_result,
        team_id=move.focal_team_id,
        model_version=f"{_PRODUCT_MODEL_VERSION}:simulation-delta",
    )
    delta = compare_team_utility_vectors(
        baseline_utility,
        changed_utility,
        competitive_override=simulation_delta,
        model_version=f"{_PRODUCT_MODEL_VERSION}:team-delta",
    )

    return {
        "move": move.model_dump(mode="json"),
        "focal_team_id": move.focal_team_id,
        "state_id_before": league_state.state_id,
        "state_id_after": changed_state.state_id,
        "baseline_simulation_count": baseline.simulation_result.simulation_count,
        "scenario_simulation_count": changed.simulation_result.simulation_count,
        "scenario_cache_hit": cache_hit,
        "scenario_computation": computation.model_dump(mode="json"),
        "simulation_counterfactual_delta": simulation_delta.model_dump(mode="json"),
        "team_delta": delta.model_dump(mode="json"),
        "materiality": None,
        "authority": {
            "candidate_search": "NEXT-6 Opportunity",
            "state_transition": "NEXT-6 Waiver scenario",
            "competitive_outcomes": "NEXT-4 Simulation",
            "competitive_delta": "NEXT-4 Simulation common-world comparison when replay/topology coordinates match",
            "scenario_delta": "NEXT-4 Team Utility consumes Simulation competitive delta and adds resilience",
            "scenario_cache": "performance-only exact-result reuse",
            "scenario_computation": (
                "screening/provisional are explicitly non-authoritative; "
                "confirmation or exact canonical reuse is authoritative"
            ),
            "materiality_evaluated": False,
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
