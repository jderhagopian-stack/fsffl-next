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
from fsffl.forecast import (
    PROVISIONAL_POSITION_FLOOR_SOURCE,
    attach_provisional_position_floor_forecasts,
)
from fsffl.forecast.models import ForecastHorizon, ForecastObservation
from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility import (
    RegularSeasonSimulationResult,
    TeamUtilityVector,
    assemble_team_utility_vector,
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
    model_version: str = "next8-live-simulation-analytics-v2"


def build_live_simulation_analytics(
    league_state: LeagueState,
    *,
    forecasts: tuple[ForecastObservation, ...],
    forecast_model_version: str,
    simulation_count: int = 50_000,
    seed: int = 20260905,
    generated_at: datetime | None = None,
) -> LiveSimulationAnalyticsResult:
    """Run Forecast -> NEXT-4 Simulation -> NEXT-7 for a real dynasty league.

    Rare missing active-player forecasts receive a conservative governed NEXT-2
    position-floor fallback before NEXT-4. A roster that still cannot legally fill
    every required slot is simulated with explicit zero-point unfilled slots.
    Neither condition is allowed to block league-wide competitive outcomes.
    """

    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("simulation forecast evidence cannot postdate LeagueState")
    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    generated = max(generated, league_state.as_of)

    effective_forecasts = attach_provisional_position_floor_forecasts(
        league_state,
        forecasts,
        as_of=league_state.as_of,
        horizon=ForecastHorizon.SEASON,
    )
    fallback_ids = {
        item.player_id
        for item in effective_forecasts
        if item.source == PROVISIONAL_POSITION_FLOOR_SOURCE
    }

    game_counts = regular_season_game_counts(league_state)
    lineups = {}
    scoring = []
    incomplete_team_names: list[str] = []
    for team in sorted(league_state.teams, key=lambda item: item.team_id):
        lineup = optimize_team_lineup(
            league_state,
            effective_forecasts,
            team_id=team.team_id,
            as_of=league_state.as_of,
            horizon=ForecastHorizon.SEASON,
            allow_unfilled_slots=True,
        )
        lineups[team.team_id] = lineup
        if lineup.unfilled_slots:
            slots = ", ".join(
                f"{item.slot.value}{item.slot_index}" for item in lineup.unfilled_slots
            )
            incomplete_team_names.append(f"{team.display_name} ({slots})")
        scoring.append(
            build_weekly_team_scoring_distribution(
                league_state,
                effective_forecasts,
                team_id=team.team_id,
                as_of=league_state.as_of,
                regular_season_game_count=game_counts[team.team_id],
                allow_unfilled_slots=True,
            )
        )

    request = build_regular_season_simulation_input(
        league_state,
        scoring=tuple(scoring),
        simulation_count=simulation_count,
        seed=seed,
        model_version="next4-live-regular-season-v2",
    )
    simulation = simulate_regular_season(request)
    outcomes = {item.team_id: item for item in simulation.outcomes}

    warnings: list[AnalyticsWarning] = [
        AnalyticsWarning(
            kind=AnalyticsWarningKind.MISSING_EVIDENCE,
            code="value_not_enriched",
            message=(
                "Authoritative NEXT-2 forecasts and NEXT-4 competitive simulation/team consequences are attached. "
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
        AnalyticsWarning(
            kind=AnalyticsWarningKind.MISSING_EVIDENCE,
            code="competitive_state_policy_not_attached",
            message=(
                "Simulation outcomes are authoritative; contender/rebuilding classification remains unknown "
                "until an explicit governed competitive-state policy is attached."
            ),
            source_component="team-utility",
        ),
    ]
    if fallback_ids:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="position_floor_forecast_fallback",
                message=(
                    f"{len(fallback_ids)} active roster player(s) lacked direct live forecast coverage and use the "
                    "governed conservative same-position floor forecast with widest observed position uncertainty."
                ),
                source_component="forecast",
            )
        )
    if incomplete_team_names:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="explicit_unfilled_lineup_slots",
                message=(
                    "Roster state cannot legally fill every starter slot for: "
                    + "; ".join(incomplete_team_names)
                    + ". Unfilled slots contribute zero points; no taxi/free-agent player is fabricated."
                ),
                source_component="team-utility",
            )
        )

    context = AnalyticsContext(
        schema_version="1",
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        as_of=league_state.as_of,
        generated_at=generated,
        lineage=(
            ModelLineageEntry(component="state", model_version=league_state.schema_version),
            ModelLineageEntry(component="forecast", model_version=forecast_model_version),
            ModelLineageEntry(component="lineup", model_version="next4-lineup-v3"),
            ModelLineageEntry(
                component="team_scoring",
                model_version="next4-weekly-team-scoring-v2:independent_equal_week",
            ),
            ModelLineageEntry(component="simulation", model_version=simulation.model_version),
            ModelLineageEntry(component="team_utility", model_version="next4-live-team-utility-v2"),
        ),
        warnings=tuple(warnings),
    )

    team_views: list[TeamAnalyticsView] = []
    for team in sorted(league_state.teams, key=lambda item: item.team_id):
        try:
            utility = assemble_team_utility_vector(
                league_state,
                effective_forecasts,
                team_id=team.team_id,
                as_of=league_state.as_of,
                horizon=ForecastHorizon.SEASON,
                competitive_outcome=outcomes[team.team_id],
                model_version="next4-live-team-utility-v2",
            )
        except ValueError as exc:
            if not lineups[team.team_id].unfilled_slots:
                raise
            utility = TeamUtilityVector(
                team_id=team.team_id,
                as_of=league_state.as_of,
                competitive_outcome=outcomes[team.team_id],
                model_version="next4-live-team-utility-v2:resilience_unavailable_incomplete_roster",
            )
        team_views.append(
            build_team_analytics_view(
                league_state,
                context=context,
                team_id=team.team_id,
                forecasts=effective_forecasts,
                optimized_lineup=lineups[team.team_id],
                utility=utility,
            )
        )

    views = tuple(team_views)
    return LiveSimulationAnalyticsResult(
        league_view=build_league_analytics_view(context=context, team_views=views),
        team_views=views,
        simulation_result=simulation,
    )
