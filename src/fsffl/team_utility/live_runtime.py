from __future__ import annotations

from fsffl.forecast.models import ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState

from .scoring import build_weekly_team_scoring_distribution
from .simulation import (
    RegularSeasonSimulationResult,
    TeamScoringDistribution,
    build_regular_season_simulation_input,
    regular_season_game_counts,
    simulate_regular_season,
)


class LiveLeagueSimulationEvidence(FrozenModel):
    """Authoritative NEXT-4 competitive simulation evidence for a live league."""

    weekly_scoring: tuple[TeamScoringDistribution, ...]
    result: RegularSeasonSimulationResult
    model_version: str = "next4-live-league-simulation-v1"


def run_live_league_simulation(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    simulation_count: int = 50_000,
    seed: int = 20260905,
    model_version: str = "next4-live-league-simulation-v1",
) -> LiveLeagueSimulationEvidence:
    """Run league-wide NEXT-4 simulation from canonical State and NEXT-2 forecasts.

    The runtime does not infer provider schedule semantics, playoff size, forecast
    uncertainty, or product-facing conclusions. Those arrive through canonical
    State and Forecast contracts. Weekly scoring is the explicit governed
    decomposition owned by NEXT-4, and competitive outcomes are produced only by
    Simulation authority.
    """

    if not forecasts:
        raise ValueError("live league simulation requires authoritative forecasts")
    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("simulation forecasts cannot postdate canonical league state")

    game_counts = regular_season_game_counts(league_state)
    weekly_scoring = tuple(
        build_weekly_team_scoring_distribution(
            league_state,
            forecasts,
            team_id=team.team_id,
            as_of=league_state.as_of,
            regular_season_game_count=game_counts[team.team_id],
        )
        for team in sorted(league_state.teams, key=lambda item: item.team_id)
    )
    request = build_regular_season_simulation_input(
        league_state,
        scoring=weekly_scoring,
        simulation_count=simulation_count,
        seed=seed,
        model_version=model_version,
    )
    result = simulate_regular_season(request)
    return LiveLeagueSimulationEvidence(
        weekly_scoring=weekly_scoring,
        result=result,
        model_version=model_version,
    )
