from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt

from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState

from .lineup import optimize_team_lineup
from .simulation import TeamScoringDistribution, WeeklyTeamScoringDistribution


class TeamUncertaintyMethod(StrEnum):
    INDEPENDENT_PLAYER_VARIANCE = "independent_player_variance"


class WeeklyScoringDecomposition(StrEnum):
    INDEPENDENT_EQUAL_WEEK = "independent_equal_week"
    BYE_AWARE_EQUAL_ACTIVE_GAME = "bye_aware_equal_active_game"


# STATIC_RULE_DEFINED for the current NFL schedule format. This is not a fitted
# coefficient: each NFL club plays 17 regular-season games across 18 weeks.
_NFL_REGULAR_SEASON_GAMES_PER_TEAM = 17


def build_team_scoring_distribution(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    horizon: ForecastHorizon,
    allow_unfilled_slots: bool = False,
    uncertainty_method: TeamUncertaintyMethod = TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE,
    model_version: str = "next4-team-scoring-v2",
) -> TeamScoringDistribution:
    """Build a team scoring distribution from the optimized starting lineup."""

    if uncertainty_method != TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE:
        raise ValueError("unsupported team uncertainty method")

    lineup = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=horizon,
        allow_unfilled_slots=allow_unfilled_slots,
    )

    starter_ids = {assignment.player_id for assignment in lineup.assignments}
    latest = _latest_fantasy_point_forecasts(
        forecasts,
        player_ids=starter_ids,
        as_of=as_of,
        horizon=horizon,
    )
    missing = starter_ids - set(latest)
    if missing:
        raise ValueError(f"optimized starter forecast evidence missing: {sorted(missing)}")

    mean_points = sum(latest[player_id].distribution.mean for player_id in starter_ids)
    variance = sum(latest[player_id].distribution.stddev**2 for player_id in starter_ids)
    suffix = ":explicit_unfilled_zero" if lineup.unfilled_slots else ""

    return TeamScoringDistribution(
        team_id=team_id,
        mean_points=mean_points,
        stddev_points=sqrt(variance),
        model_version=f"{model_version}:{uncertainty_method.value}{suffix}",
    )


def build_weekly_team_scoring_distribution(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    as_of: datetime,
    regular_season_game_count: int,
    allow_unfilled_slots: bool = False,
    decomposition: WeeklyScoringDecomposition = WeeklyScoringDecomposition.INDEPENDENT_EQUAL_WEEK,
    model_version: str = "next4-weekly-team-scoring-v2",
) -> TeamScoringDistribution:
    """Legacy generic-week bridge retained for reproducibility/comparison only."""

    if decomposition != WeeklyScoringDecomposition.INDEPENDENT_EQUAL_WEEK:
        raise ValueError("unsupported generic weekly scoring decomposition")
    if regular_season_game_count < 1:
        raise ValueError("regular_season_game_count must be positive")

    season = build_team_scoring_distribution(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=ForecastHorizon.SEASON,
        allow_unfilled_slots=allow_unfilled_slots,
        model_version=f"{model_version}:season_input",
    )
    return TeamScoringDistribution(
        team_id=season.team_id,
        mean_points=season.mean_points / regular_season_game_count,
        stddev_points=season.stddev_points / sqrt(regular_season_game_count),
        model_version=(
            f"{model_version}:{decomposition.value}:"
            f"{TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE.value}"
        ),
    )


def build_bye_aware_weekly_team_scoring_distribution(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    week: int,
    as_of: datetime,
    model_version: str = "next4-weekly-team-scoring-v3",
) -> WeeklyTeamScoringDistribution:
    """Build the actual week-specific lineup distribution from canonical bye state.

    Season player distributions are decomposed into equal active-NFL-game
    distributions, then the lineup is re-optimized after excluding players whose
    canonical NFL team is on bye in the requested fantasy week. This is an
    explicit PROVISIONAL_GOVERNED bridge until authoritative NEXT-2 weekly
    forecasts are available. It does not reuse the old fantasy-season/N divisor.
    """

    if not 1 <= week <= 18:
        raise ValueError("week must be within the NFL regular season")
    if not league_state.nfl_team_byes:
        raise ValueError("canonical NFL bye-week state is unavailable")

    bye_teams = {
        item.nfl_team
        for item in league_state.nfl_team_byes
        if item.season == league_state.league.season and item.week == week
    }
    players_by_id = {player.player_id: player for player in league_state.players}
    excluded = frozenset(
        player_id
        for player_id, player in players_by_id.items()
        if player.nfl_team is not None and player.nfl_team.upper() in bye_teams
    )

    lineup = optimize_team_lineup(
        league_state,
        forecasts,
        team_id=team_id,
        as_of=as_of,
        horizon=ForecastHorizon.SEASON,
        excluded_player_ids=excluded,
        allow_unfilled_slots=True,
        model_version="next4-lineup-v3:bye-aware",
    )
    starter_ids = {assignment.player_id for assignment in lineup.assignments}
    latest = _latest_fantasy_point_forecasts(
        forecasts,
        player_ids=starter_ids,
        as_of=as_of,
        horizon=ForecastHorizon.SEASON,
    )
    missing = starter_ids - set(latest)
    if missing:
        raise ValueError(f"weekly optimized starter forecast evidence missing: {sorted(missing)}")

    mean_points = sum(
        latest[player_id].distribution.mean / _NFL_REGULAR_SEASON_GAMES_PER_TEAM
        for player_id in starter_ids
    )
    variance = sum(
        (latest[player_id].distribution.stddev**2) / _NFL_REGULAR_SEASON_GAMES_PER_TEAM
        for player_id in starter_ids
    )
    suffix = ":explicit_unfilled_zero" if lineup.unfilled_slots else ""
    return WeeklyTeamScoringDistribution(
        week=week,
        team_id=team_id,
        mean_points=mean_points,
        stddev_points=sqrt(variance),
        model_version=(
            f"{model_version}:{WeeklyScoringDecomposition.BYE_AWARE_EQUAL_ACTIVE_GAME.value}:"
            f"{TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE.value}{suffix}"
        ),
    )


def _latest_fantasy_point_forecasts(
    forecasts: tuple[ForecastObservation, ...],
    *,
    player_ids: set[str],
    as_of: datetime,
    horizon: ForecastHorizon,
) -> dict[str, ForecastObservation]:
    latest: dict[str, ForecastObservation] = {}
    for observation in forecasts:
        if observation.player_id not in player_ids:
            continue
        if observation.metric != ForecastMetric.FANTASY_POINTS or observation.horizon != horizon:
            continue
        if observation.as_of > as_of:
            continue
        current = latest.get(observation.player_id)
        if current is None or observation.as_of > current.as_of:
            latest[observation.player_id] = observation
    return latest
