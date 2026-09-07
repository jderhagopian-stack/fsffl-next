from __future__ import annotations

from typing import Any, Callable

from fsffl.state.models import LeagueState, RosterSlot
from fsffl.team_utility import compare_team_utility_vectors

from .runtime import LiveForecastEvidence
from .scenario_cache import run_cached_scenario_simulation
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-player-unavailable-what-if-v2:scenario-cache"


def _utility_for_team(result: LiveSimulationAnalyticsResult, team_id: str):
    view = next((item for item in result.team_views if item.team_id == team_id), None)
    if view is None or view.utility is None:
        raise ValueError(f"simulation utility is unavailable for {team_id}")
    return view.utility


def build_player_unavailable_scenario(
    runtime: Any,
    *,
    player_id: str,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Stress-test the selected franchise with one rostered player unavailable.

    This is a hypothetical State transition only. Ownership is preserved; the
    selected player is moved from the active roster to IR for the scenario so the
    existing NEXT-4 lineup and Simulation authorities naturally exclude him. No
    forecast, Value, utility or probability is recalculated in Product code.
    Exact repeated changed States may reuse the prior authoritative Simulation.
    """

    league_state = runtime.league_state
    forecast_evidence = runtime.forecast_evidence
    baseline = runtime.simulation_analytics
    team_id = runtime.selected_team_id
    if league_state is None:
        raise ValueError("What-If requires a loaded league state")
    if team_id is None:
        raise ValueError("What-If requires a selected franchise")
    if forecast_evidence is None or not forecast_evidence.league_scored_forecasts:
        raise ValueError("What-If requires current NEXT-2 forecast evidence")
    if baseline is None:
        raise ValueError("What-If requires a current NEXT-4 baseline simulation")

    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team_state is None:
        raise ValueError("selected franchise is missing canonical team state")
    entry = next((item for item in team_state.roster if item.player_id == player_id), None)
    if entry is None:
        raise ValueError("What-If player must be rostered by the selected franchise")
    if entry.slot in {RosterSlot.IR, RosterSlot.TAXI}:
        raise ValueError("What-If player is already unavailable to the active lineup")

    changed_roster = tuple(
        item.model_copy(update={"slot": RosterSlot.IR}) if item.player_id == player_id else item
        for item in team_state.roster
    )
    changed_team_state = team_state.model_copy(update={"roster": changed_roster})
    changed_state = league_state.model_copy(
        update={
            "team_states": tuple(
                changed_team_state if item.team_id == team_id else item
                for item in league_state.team_states
            )
        }
    )
    changed, cache_hit = run_cached_scenario_simulation(
        changed_state,
        forecast_evidence,
        simulation_loader=simulation_loader,
    )
    baseline_utility = _utility_for_team(baseline, team_id)
    changed_utility = _utility_for_team(changed, team_id)
    delta = compare_team_utility_vectors(
        baseline_utility,
        changed_utility,
        model_version=f"{_PRODUCT_MODEL_VERSION}:team-delta",
    )
    player = next((item for item in league_state.players if item.player_id == player_id), None)

    return {
        "scenario_kind": "player_unavailable",
        "focal_team_id": team_id,
        "player_id": player_id,
        "player_name": player.full_name if player is not None else player_id,
        "state_id_before": league_state.state_id,
        "state_id_after": changed_state.state_id,
        "baseline_simulation_count": baseline.simulation_result.simulation_count,
        "scenario_simulation_count": changed.simulation_result.simulation_count,
        "scenario_cache_hit": cache_hit,
        "team_delta": delta.model_dump(mode="json"),
        "calculated_state_before": baseline_utility.calculated_competitive_state.value,
        "calculated_state_after": changed_utility.calculated_competitive_state.value,
        "authority": {
            "scenario_state": "NEXT-1 point-in-time State hypothetical",
            "forecast": "NEXT-2 Forecast unchanged",
            "competitive_outcomes": "NEXT-4 Simulation",
            "scenario_delta": "NEXT-4 Team Utility",
            "scenario_cache": "performance-only exact-result reuse",
            "value": "unchanged; ownership is preserved",
            "presentation_calculation": False,
        },
        "model_version": _PRODUCT_MODEL_VERSION,
    }
