from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import sqrt

from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.forecast.weekly_volatility import active_game_distribution
from fsffl.state.models import LeagueState

from .lineup import optimize_team_lineup
from .models import OptimizedTeamLineup
from .simulation import TeamScoringDistribution, WeeklyTeamScoringDistribution


class TeamUncertaintyMethod(StrEnum):
    INDEPENDENT_PLAYER_VARIANCE = "independent_player_variance"


class WeeklyScoringDecomposition(StrEnum):
    INDEPENDENT_EQUAL_WEEK = "independent_equal_week"
    BYE_AWARE_EQUAL_ACTIVE_GAME = "bye_aware_equal_active_game"
    BYE_AWARE_EMPIRICAL_WEEKLY_VOLATILITY = "bye_aware_empirical_weekly_volatility"


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


def _weekly_distribution_from_lineup(
    lineup: OptimizedTeamLineup,
    *,
    week: int,
    latest: dict[str, ForecastObservation],
    model_version: str,
) -> WeeklyTeamScoringDistribution:
    starter_ids = {assignment.player_id for assignment in lineup.assignments}
    missing = starter_ids - set(latest)
    if missing:
        raise ValueError(f"weekly optimized starter forecast evidence missing: {sorted(missing)}")

    mean_points = 0.0
    variance = 0.0
    for player_id in starter_ids:
        observation = latest[player_id]
        mean, stddev = active_game_distribution(
            season_mean=observation.distribution.mean,
            position=observation.position,
            games_per_team=_NFL_REGULAR_SEASON_GAMES_PER_TEAM,
        )
        mean_points += mean
        variance += stddev**2

    suffix = ":explicit_unfilled_zero" if lineup.unfilled_slots else ""
    return WeeklyTeamScoringDistribution(
        week=week,
        team_id=lineup.team_id,
        mean_points=mean_points,
        stddev_points=sqrt(variance),
        model_version=(
            f"{model_version}:"
            f"{WeeklyScoringDecomposition.BYE_AWARE_EMPIRICAL_WEEKLY_VOLATILITY.value}:"
            f"{TeamUncertaintyMethod.INDEPENDENT_PLAYER_VARIANCE.value}{suffix}"
        ),
    )


def build_bye_aware_weekly_team_scoring_panel(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_ids: tuple[str, ...],
    weeks: tuple[int, ...],
    as_of: datetime,
    baseline_lineups: dict[str, OptimizedTeamLineup] | None = None,
    model_version: str = "next4-weekly-team-scoring-v4",
) -> tuple[WeeklyTeamScoringDistribution, ...]:
    """Build a full league/week scoring panel while reusing identical lineup work.

    The old live runtime rebuilt player/forecast indexes and re-ran the lineup
    optimizer once for every team-week pair. Most team-weeks have no rostered
    player on bye, and some bye weeks produce the same exclusion set. This panel
    resolves canonical bye availability once, caches lineups by
    ``(team_id, excluded_player_ids)``, and reuses caller-supplied baseline lineups
    when no owned player is on bye. Output semantics are identical to calling the
    single-week builder independently for every pair.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not league_state.nfl_team_byes:
        raise ValueError("canonical NFL bye-week state is unavailable")
    if any(not 1 <= week <= 18 for week in weeks):
        raise ValueError("week must be within the NFL regular season")

    known_team_ids = {team.team_id for team in league_state.teams}
    unknown = sorted(set(team_ids) - known_team_ids)
    if unknown:
        raise ValueError(f"unknown team_id values: {unknown}")

    players_by_id = {player.player_id: player for player in league_state.players}
    team_state_by_id = {item.team_id: item for item in league_state.team_states}
    roster_ids_by_team = {
        team_id: frozenset(entry.player_id for entry in team_state_by_id[team_id].roster)
        for team_id in team_ids
    }
    all_roster_ids = set().union(*(set(ids) for ids in roster_ids_by_team.values())) if team_ids else set()
    latest = _latest_fantasy_point_forecasts(
        forecasts,
        player_ids=all_roster_ids,
        as_of=as_of,
        horizon=ForecastHorizon.SEASON,
    )

    bye_teams_by_week: dict[int, frozenset[str]] = {}
    for week in weeks:
        bye_teams_by_week[week] = frozenset(
            item.nfl_team
            for item in league_state.nfl_team_byes
            if item.season == league_state.league.season and item.week == week
        )

    cache: dict[tuple[str, frozenset[str]], OptimizedTeamLineup] = {}
    if baseline_lineups:
        for team_id, lineup in baseline_lineups.items():
            if team_id in roster_ids_by_team:
                cache[(team_id, frozenset())] = lineup

    rows: list[WeeklyTeamScoringDistribution] = []
    for team_id in team_ids:
        roster_ids = roster_ids_by_team[team_id]
        for week in weeks:
            bye_teams = bye_teams_by_week[week]
            excluded = frozenset(
                player_id
                for player_id in roster_ids
                if (
                    (player := players_by_id.get(player_id)) is not None
                    and player.nfl_team is not None
                    and player.nfl_team.upper() in bye_teams
                )
            )
            key = (team_id, excluded)
            lineup = cache.get(key)
            if lineup is None:
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
                cache[key] = lineup
            rows.append(
                _weekly_distribution_from_lineup(
                    lineup,
                    week=week,
                    latest=latest,
                    model_version=model_version,
                )
            )
    return tuple(rows)


def build_bye_aware_weekly_team_scoring_distribution(
    league_state: LeagueState,
    forecasts: tuple[ForecastObservation, ...],
    *,
    team_id: str,
    week: int,
    as_of: datetime,
    model_version: str = "next4-weekly-team-scoring-v4",
) -> WeeklyTeamScoringDistribution:
    """Build one week-specific team distribution from Forecast + canonical bye State."""

    return build_bye_aware_weekly_team_scoring_panel(
        league_state,
        forecasts,
        team_ids=(team_id,),
        weeks=(week,),
        as_of=as_of,
        model_version=model_version,
    )[0]


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
