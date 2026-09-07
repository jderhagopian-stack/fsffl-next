from __future__ import annotations

from typing import Any, Callable

from fsffl.opportunity.waiver import WaiverMove, apply_waiver_move
from fsffl.team_utility import compare_team_utility_vectors

from .runtime import LiveForecastEvidence
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[Any, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-waiver-simulation-v1"


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
) -> dict[str, object]:
    """Run one canonical add/drop scenario through NEXT-4 Simulation authority.

    Product does not score waiver desirability here. NEXT-6 owns candidate search,
    NEXT-4 owns competitive outcomes, and materiality remains a separate governed
    interpretation step with explicit policies. This adapter only creates the
    changed State, simulates it, and returns the typed before/after Team Utility
    delta for the focal franchise.
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
    changed = simulation_loader(changed_state, forecast_evidence)
    baseline_utility = _utility_for_team(baseline, move.focal_team_id)
    changed_utility = _utility_for_team(changed, move.focal_team_id)
    delta = compare_team_utility_vectors(
        baseline_utility,
        changed_utility,
        model_version=f"{_PRODUCT_MODEL_VERSION}:team-delta",
    )

    return {
        "move": move.model_dump(mode="json"),
        "focal_team_id": move.focal_team_id,
        "state_id_before": league_state.state_id,
        "state_id_after": changed_state.state_id,
        "baseline_simulation_count": baseline.simulation_result.simulation_count,
        "scenario_simulation_count": changed.simulation_result.simulation_count,
        "team_delta": delta.model_dump(mode="json"),
        "materiality": None,
        "authority": {
            "candidate_search": "NEXT-6 Opportunity",
            "state_transition": "NEXT-6 Waiver scenario",
            "competitive_outcomes": "NEXT-4 Simulation",
            "scenario_delta": "NEXT-4 Team Utility",
            "materiality_evaluated": False,
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
