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
    build_bye_aware_weekly_team_scoring_distribution,
    build_regular_season_simulation_input,
    optimize_team_lineup,
    simulate_regular_season,
)


class LiveSimulationAnalyticsResult(FrozenModel):
    """NEXT-7 views backed by authoritative NEXT-4 simulation outcomes."""

    league_view: LeagueAnalyticsView
    team_views: tuple[TeamAnalyticsView, ...]
    simulation_result: RegularSeasonSimulationResult
    model_version: str = "next8-live-simulation-analytics-v4"


def build_live_simulation_analytics(
    league_state: LeagueState,
    *,
    forecasts: tuple[ForecastObservation, ...],
    forecast_model_version: str,
    simulation_count: int = 50_000,
    seed: int = 20260905,
    generated_at: datetime | None = None,
) -> LiveSimulationAnalyticsResult:
    """Run Forecast -> week-specific NEXT-4 Simulation -> NEXT-7.

    Canonical NFL bye state is consumed from State authority. NEXT-4 re-optimizes
    every fantasy roster for every scheduled fantasy week after excluding players
    whose NFL team is on bye. Season forecast means are still decomposed to equal
    active-NFL-game means as a provisional bridge, but ordinary weekly scoring
    variance now comes from an independently calibrated NEXT-2 weekly-volatility
    model rather than full-season forecast uncertainty.
    """

    if any(item.as_of > league_state.as_of for item in forecasts):
        raise ValueError("simulation forecast evidence cannot postdate LeagueState")
    if not league_state.nfl_team_byes:
        raise ValueError("canonical NFL bye-week state is required for live simulation")
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

    fantasy_weeks = tuple(sorted({matchup.week for matchup in league_state.matchups}))
    if not fantasy_weeks:
        raise ValueError("canonical fantasy regular-season schedule is required")

    lineups = {}
    weekly_scoring = []
    incomplete_team_names: list[str] = []
    bye_week_unfilled: list[str] = []
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

        for week in fantasy_weeks:
            week_distribution = build_bye_aware_weekly_team_scoring_distribution(
                league_state,
                effective_forecasts,
                team_id=team.team_id,
                week=week,
                as_of=league_state.as_of,
            )
            weekly_scoring.append(week_distribution)
            if "explicit_unfilled_zero" in week_distribution.model_version and not lineup.unfilled_slots:
                bye_week_unfilled.append(f"{team.display_name} W{week}")

    request = build_regular_season_simulation_input(
        league_state,
        weekly_scoring=tuple(weekly_scoring),
        simulation_count=simulation_count,
        seed=seed,
        model_version="next4-live-regular-season-v4:empirical-weekly-volatility",
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
            code="weekly_mean_decomposition_provisional",
            message=(
                "Simulation is bye-aware and re-optimizes each roster for each fantasy week. Player season means "
                "are currently converted to equal active-NFL-game means until direct multi-source weekly NEXT-2 "
                "forecast means are promoted. Weekly scoring volatility is independently calibrated from actual "
                "historical weekly outcomes and is not derived from season forecast uncertainty."
            ),
            source_component="forecast",
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
    if bye_week_unfilled:
        warnings.append(
            AnalyticsWarning(
                kind=AnalyticsWarningKind.PROVISIONAL,
                code="bye_week_unfilled_lineup_slots",
                message=(
                    "Bye-week availability leaves at least one legal starter slot unfilled for: "
                    + "; ".join(bye_week_unfilled)
                    + ". Those week-specific slots contribute zero points."
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
            ModelLineageEntry(component="lineup", model_version="next4-lineup-v3:bye-aware"),
            ModelLineageEntry(
                component="weekly_volatility",
                model_version="next2-weekly-volatility-v1:2023-2025-position-cv",
            ),
            ModelLineageEntry(
                component="team_scoring",
                model_version="next4-weekly-team-scoring-v4:bye_aware_empirical_weekly_volatility",
            ),
            ModelLineageEntry(component="simulation", model_version=simulation.model_version),
            ModelLineageEntry(component="team_utility", model_version="next4-live-team-utility-v3"),
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
                model_version="next4-live-team-utility-v3",
            )
        except ValueError:
            if not lineups[team.team_id].unfilled_slots:
                raise
            utility = TeamUtilityVector(
                team_id=team.team_id,
                as_of=league_state.as_of,
                competitive_outcome=outcomes[team.team_id],
                model_version="next4-live-team-utility-v3:resilience_unavailable_incomplete_roster",
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
