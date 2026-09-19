from __future__ import annotations

from typing import Any, Callable

from fsffl.state.models import LeagueState, RosterSlot
from fsffl.team_utility import compare_team_utility_vectors

from .runtime import LiveForecastEvidence
from .scenario_cache import run_cached_scenario_simulation
from .simulation_runtime import LiveSimulationAnalyticsResult


SimulationLoader = Callable[[LeagueState, LiveForecastEvidence], LiveSimulationAnalyticsResult]
_PRODUCT_MODEL_VERSION = "next8-players-unavailable-simulator-v1:scenario-cache"
_SIMULATOR_ENVELOPE_PREFIX = "simulator:"


def _utility_for_team(result: LiveSimulationAnalyticsResult, team_id: str):
    view = next((item for item in result.team_views if item.team_id == team_id), None)
    if view is None or view.utility is None:
        raise ValueError(f"simulation utility is unavailable for {team_id}")
    return view.utility


def build_players_unavailable_scenario(
    runtime: Any,
    *,
    player_ids: tuple[str, ...],
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Stress-test the selected franchise with one or more players unavailable.

    Ownership is preserved. Selected active-roster players move to hypothetical IR
    in a changed NEXT-1 State, then the same NEXT-2 Forecast evidence is run through
    authoritative NEXT-4 Simulation. Product never applies injury multipliers or
    invents substitute projections. Exact repeated scenarios may reuse the cached
    authoritative Simulation result.
    """

    league_state = runtime.league_state
    forecast_evidence = runtime.forecast_evidence
    baseline = runtime.simulation_analytics
    team_id = runtime.selected_team_id
    if league_state is None:
        raise ValueError("Simulator requires a loaded league state")
    if team_id is None:
        raise ValueError("Simulator requires a selected franchise")
    if forecast_evidence is None or not forecast_evidence.league_scored_forecasts:
        raise ValueError("Simulator requires current NEXT-2 forecast evidence")
    if baseline is None:
        raise ValueError("Simulator requires a current NEXT-4 baseline simulation")

    unique_ids = tuple(dict.fromkeys(player_id.strip() for player_id in player_ids if player_id.strip()))
    if not unique_ids:
        raise ValueError("Simulator requires at least one unavailable player")

    team_state = next((item for item in league_state.team_states if item.team_id == team_id), None)
    if team_state is None:
        raise ValueError("selected franchise is missing canonical team state")
    entries = {item.player_id: item for item in team_state.roster}
    missing = [player_id for player_id in unique_ids if player_id not in entries]
    if missing:
        raise ValueError("Simulator players must be rostered by the selected franchise")
    already_unavailable = [
        player_id
        for player_id in unique_ids
        if entries[player_id].slot in {RosterSlot.IR, RosterSlot.TAXI}
    ]
    if already_unavailable:
        raise ValueError("Simulator players must currently be available to the active lineup")

    selected = frozenset(unique_ids)
    changed_roster = tuple(
        item.model_copy(update={"slot": RosterSlot.IR}) if item.player_id in selected else item
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
    players_by_id = {item.player_id: item for item in league_state.players}
    players = [
        {
            "player_id": player_id,
            "player_name": players_by_id[player_id].full_name if player_id in players_by_id else player_id,
            "position": players_by_id[player_id].position.value if player_id in players_by_id else None,
        }
        for player_id in unique_ids
    ]

    return {
        "scenario_kind": "players_unavailable",
        "focal_team_id": team_id,
        "player_ids": list(unique_ids),
        "players": players,
        "player_names": [item["player_name"] for item in players],
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


def build_player_unavailable_scenario(
    runtime: Any,
    *,
    player_id: str,
    simulation_loader: SimulationLoader,
) -> dict[str, object]:
    """Single-player What-If plus a temporary multi-player Simulator envelope.

    The hosted product currently has one narrow availability endpoint. A value
    prefixed with ``simulator:`` carries comma-separated canonical player ids into
    the generalized server-side Simulator runtime. This is transport only: State,
    Forecast, Simulation, utility delta and cache authority remain entirely on the
    server. Normal player ids preserve the original one-player What-If contract.
    """

    if player_id.startswith(_SIMULATOR_ENVELOPE_PREFIX):
        encoded = player_id[len(_SIMULATOR_ENVELOPE_PREFIX):]
        return build_players_unavailable_scenario(
            runtime,
            player_ids=tuple(item for item in encoded.split(",") if item),
            simulation_loader=simulation_loader,
        )

    result = build_players_unavailable_scenario(
        runtime,
        player_ids=(player_id,),
        simulation_loader=simulation_loader,
    )
    player = result["players"][0]
    return {
        **result,
        "scenario_kind": "player_unavailable",
        "player_id": player["player_id"],
        "player_name": player["player_name"],
        "model_version": f"{_PRODUCT_MODEL_VERSION}:single-player-what-if",
    }
