from __future__ import annotations

from datetime import UTC, datetime

from fsffl.analytics.league import LeagueAnalyticsView, build_league_analytics_view
from fsffl.analytics.models import (
    AnalyticsContext,
    AnalyticsWarning,
    AnalyticsWarningKind,
    ModelLineageEntry,
)
from fsffl.analytics.team import TeamAnalyticsView, build_team_analytics_view
from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility import (
    RegularSeasonSimulationResult,
    TeamUtilityVector,
    build_regular_season_simulation_input,
    build_weekly_team_scoring_distribution,
    optimize_team_lineup,
    regular_season_game_counts,
    simulate_regular_season,
)


class LiveSimulationAnalyticsResult(FrozenModel):
    """NEXT-7 views backed by authoritative NEXT-4 simulation outcomes."""

    league_view: LeagueAnalyticsView
    team_views: tuple[TeamAnalyticsView, ...]
    simulation_result: RegularSeasonSimulationResult
    model_version: str = "next8-live-simulation-analytics-v1"


def build_live_simulation_analytics(
    league_state: LeagueState,
    *,
    forecasts: tuple[ForecastObservation, ...],
    forecast_model_version: str,
    simulation_count: int = 50_000,
    seed: int = 20260905,
    generated_at: datetime | None = None,
) -> LiveSimulationAnalyticsResult:
    """Run the governed Forecast -> NEXT-4 Simulation -> NEXT-7 path.

    Product orchestration supplies canonical inputs and stores outputs. It does
    not calculate wins, playoff probabilities, lineup value, or forecast
    uncertainty itself. Missing schedule/rules/lineup evidence fails closed.
    """

    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("simulation forecast evidence cannot postdate LeagueState")
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    generated = max(generated, league_state.as_of)

    game_counts = regular_season_game_counts(league_state)
    lineups = {}
    scoring = []
    for team in sorted(league_state.teams, key=lambda item: item.team_id):
        lineup = optimize_team_lineup(
            league_state,
            forecasts,
            team_id=team.team_id,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
        )
        lineups[team.team_id] = lineup
        scoring.append(
            build_weekly_team_scoring_distribution(
                league_state,
                forecasts,
                team_id=team.team_id,
                as_of=league_state.as_of,
                regular_season_game_count=game_counts[team.team_id],
            )
        )

    request = build_regular_season_simulation_input(
        league_state,
        scoring=tuple(scoring),
        simulation_count=simulation_count,
        seed=seed,
        model_version="next4-live-regular-season-v1",
    )
    simulation = simulate_regular_season(request)
    outcomes = {item.team_id: item for item in simulation.outcomes}

    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=generated,
        lineage=(
            ModelLineageEntry(component="state", model_version=league_state.schema_version),
            ModelLineageEntry(component="forecast", model_version=forecast_model_version),
            ModelLineageEntry(component="lineup", model_version="next4-lineup-v2"),
            ModelLineageEntry(
                component="team_scoring",
                model_version="next4-weekly-team-scoring-v1:independent_equal_week",
            ),
            ModelLineageEntry(component="simulation", model_version=simulation.model_version),
        ),
        warnings=(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.MISSING_EVIDENCE,
                code="value_not_enriched",
                message=(
                    "Authoritative NEXT-2 forecasts and NEXT-4 competitive simulation are attached. "
                    "NEXT-3 dynasty value and downstream trade/opportunity evidence remain pending."
                ),
                source_component="product-runtime",
            ),
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="weekly_scoring_decomposition_provisional",
                message=(
                    "Weekly scoring uses the governed independent equal-week decomposition of calibrated "
                    "season uncertainty until empirical weekly/covariance evidence is promoted."
                ),
                source_component="team-utility",
            ),
        ),
    )

    team_views = tuple(
        build_team_analytics_view(
            league_state,
            context=context,
            team_id=team.team_id,
            forecasts=forecasts,
            optimized_lineup=lineups[team.team_id],
            utility=TeamUtilityVector(
                team_id=team.team_id,
                as_of=league_state.as_of,
                competitive_outcome=outcomes[team.team_id],
                model_version="next4-live-competitive-vector-v1",
            ),
        )
        for team in sorted(league_state.teams, key=lambda item: item.team_id)
    )
    return LiveSimulationAnalyticsResult(
        league_view=build_league_analytics_view(context=context, team_views=team_views),
        team_views=team_views,
        simulation_result=simulation,
    )
