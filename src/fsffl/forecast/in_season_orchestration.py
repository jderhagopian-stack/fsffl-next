from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Iterable

from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperWeeklyStatsSource
from fsffl.state.models import LeagueState, Position, Provenance

from .backtest import RealizedOutcome
from .in_season_runtime import InSeasonForecastRuntimeResult, ProjectionHistoryWriter, build_in_season_forecasts
from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from .season_rollforward import compose_completed_actuals_with_ros


NFL_REGULAR_SEASON_WEEKS = 18
NFL_GAMES_PER_TEAM = 17
FALLBACK_MODEL_VERSION = "next2-preseason-remaining-prior-v1"


def canonical_week_window(season: int, week: int) -> tuple[datetime, datetime]:
    """Structural week identity used consistently for actual/ROS overlap guards."""

    if not 1 <= week <= NFL_REGULAR_SEASON_WEEKS:
        raise ValueError("NFL week must be between 1 and 18")
    start = datetime(season, 9, 1, tzinfo=UTC) + timedelta(weeks=week - 1)
    return start, start + timedelta(weeks=1)


def _score_raw_stats(league_state: LeagueState, stats: dict[str, float] | object) -> float:
    if not isinstance(stats, dict):
        stats = dict(stats)
    return sum(float(stats.get(rule.stat, 0.0)) * rule.points for rule in league_state.league.rules.scoring)


def realized_fantasy_points_from_weekly_stats(
    league_state: LeagueState,
    *,
    lines: Iterable[SleeperWeeklyStatLine],
    week: int,
    finalized_at: datetime,
) -> tuple[RealizedOutcome, ...]:
    """Convert measured raw stats to league fantasy points inside Forecast authority."""

    if finalized_at.tzinfo is None:
        raise ValueError("actual finalization time must be timezone-aware")
    start, end = canonical_week_window(league_state.league.season, week)
    players = {player.player_id: player for player in league_state.players}
    output: list[RealizedOutcome] = []
    for line in lines:
        if line.season != league_state.league.season or line.week != week:
            raise ValueError("weekly actual stat identity does not match requested league season/week")
        player = players.get(line.player_id)
        if player is None or player.position not in {Position.QB, Position.RB, Position.WR, Position.TE}:
            continue
        output.append(
            RealizedOutcome(
                player_id=line.player_id,
                position=player.position,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=start,
                period_end=end,
                actual=_score_raw_stats(league_state, line.stats),
                finalized_at=max(finalized_at.astimezone(UTC), end),
                provenance=Provenance(
                    source="sleeper:weekly_nfl_stats",
                    retrieved_at=line.captured_at,
                    effective_at=end,
                    source_version=SleeperWeeklyStatsSource.source_version,
                ),
            )
        )
    return tuple(sorted(output, key=lambda item: item.player_id))


def load_completed_actuals(
    league_state: LeagueState,
    *,
    source: SleeperWeeklyStatsSource,
    completed_through_week: int,
) -> tuple[RealizedOutcome, ...]:
    if not 0 <= completed_through_week <= NFL_REGULAR_SEASON_WEEKS:
        raise ValueError("completed_through_week is outside NFL regular season")
    actuals: list[RealizedOutcome] = []
    for week in range(1, completed_through_week + 1):
        lines = source.fetch_week(season=league_state.league.season, week=week)
        _, end = canonical_week_window(league_state.league.season, week)
        captured = max((line.captured_at for line in lines), default=end)
        actuals.extend(
            realized_fantasy_points_from_weekly_stats(
                league_state,
                lines=lines,
                week=week,
                finalized_at=max(captured, end),
            )
        )
    return tuple(actuals)


def _remaining_games_for_player(
    league_state: LeagueState,
    *,
    player_id: str,
    completed_through_week: int,
) -> int:
    player = next((item for item in league_state.players if item.player_id == player_id), None)
    if player is None:
        return 0
    remaining_weeks = set(range(completed_through_week + 1, NFL_REGULAR_SEASON_WEEKS + 1))
    nfl_team = (player.nfl_team or "").upper().strip()
    if nfl_team:
        bye = next(
            (
                item.week
                for item in league_state.nfl_team_byes
                if item.season == league_state.league.season and item.nfl_team == nfl_team
            ),
            None,
        )
        if bye in remaining_weeks:
            remaining_weeks.remove(bye)
    else:
        # Without team/bye evidence, use the structural 17-of-18 expectation.
        return round(len(remaining_weeks) * NFL_GAMES_PER_TEAM / NFL_REGULAR_SEASON_WEEKS)
    return len(remaining_weeks)


def remaining_prior_from_preseason(
    league_state: LeagueState,
    *,
    preseason_season_forecasts: tuple[ForecastObservation, ...],
    completed_through_week: int,
    as_of: datetime,
) -> tuple[ForecastObservation, ...]:
    """Project only the unplayed share of the immutable preseason prior.

    This never subtracts observed production from a preseason total. It converts the
    preseason per-active-game expectation to the remaining schedule, so completed
    actuals can be added exactly once by the season roll-forward.
    """

    if as_of.tzinfo is None:
        raise ValueError("remaining prior as_of must be timezone-aware")
    next_week = min(completed_through_week + 1, NFL_REGULAR_SEASON_WEEKS)
    period_start, _ = canonical_week_window(league_state.league.season, next_week)
    _, period_end = canonical_week_window(league_state.league.season, NFL_REGULAR_SEASON_WEEKS)
    output: list[ForecastObservation] = []
    for forecast in preseason_season_forecasts:
        if forecast.horizon != ForecastHorizon.SEASON or forecast.metric != ForecastMetric.FANTASY_POINTS:
            continue
        games = _remaining_games_for_player(
            league_state,
            player_id=forecast.player_id,
            completed_through_week=completed_through_week,
        )
        factor = max(0.0, min(1.0, games / NFL_GAMES_PER_TEAM))
        dist = forecast.distribution
        output.append(
            ForecastObservation(
                player_id=forecast.player_id,
                position=forecast.position,
                horizon=ForecastHorizon.REST_OF_SEASON,
                metric=ForecastMetric.FANTASY_POINTS,
                period_start=period_start,
                period_end=period_end,
                distribution=ForecastDistribution(
                    mean=dist.mean * factor,
                    stddev=dist.stddev * factor,
                    p10=dist.p10 * factor if dist.p10 is not None else None,
                    p50=dist.p50 * factor if dist.p50 is not None else None,
                    p90=dist.p90 * factor if dist.p90 is not None else None,
                ),
                source="fsffl:preseason_remaining_prior",
                model_version=FALLBACK_MODEL_VERSION,
                as_of=as_of.astimezone(UTC),
                provenance=Provenance(
                    source=f"fsffl:preseason_remaining_prior[{forecast.source}]",
                    retrieved_at=min(forecast.provenance.retrieved_at, as_of),
                    effective_at=min(forecast.provenance.effective_at, as_of),
                    provider_ref=forecast.provenance.provider_ref,
                    source_version=FALLBACK_MODEL_VERSION,
                ),
            )
        )
    if not output:
        raise ValueError("no valid preseason season fantasy-point evidence is available for fallback")
    return tuple(sorted(output, key=lambda item: item.player_id))


class GovernedInSeasonResult:
    def __init__(
        self,
        *,
        completed_through_week: int,
        season_outlook: tuple[ForecastObservation, ...],
        forward_forecasts: tuple[ForecastObservation, ...],
        evidence_basis: str,
        current_runtime: InSeasonForecastRuntimeResult | None,
        current_failure: str | None,
    ) -> None:
        self.completed_through_week = completed_through_week
        self.season_outlook = season_outlook
        self.forward_forecasts = forward_forecasts
        self.evidence_basis = evidence_basis
        self.current_runtime = current_runtime
        self.current_failure = current_failure


def build_governed_in_season_outlook(
    league_state: LeagueState,
    *,
    preseason_season_forecasts: tuple[ForecastObservation, ...],
    stats_source: SleeperWeeklyStatsSource | None = None,
    history_writer: ProjectionHistoryWriter | None = None,
    clock: callable | None = None,
) -> GovernedInSeasonResult:
    """Compose finalized actual weeks with current ROS, or a legitimate prior fallback."""

    source = stats_source or SleeperWeeklyStatsSource()
    nfl_state = source.fetch_nfl_state()
    if nfl_state.season != league_state.league.season:
        raise ValueError("Sleeper NFL state season does not match league season")
    completed = nfl_state.completed_through_week
    actuals = load_completed_actuals(
        league_state,
        source=source,
        completed_through_week=completed,
    )
    next_week = min(completed + 1, NFL_REGULAR_SEASON_WEEKS)
    period_start, _ = canonical_week_window(league_state.league.season, next_week)
    _, period_end = canonical_week_window(league_state.league.season, NFL_REGULAR_SEASON_WEEKS)
    now = (clock or (lambda: datetime.now(UTC)))()
    if now.tzinfo is None:
        raise ValueError("in-season orchestration clock must be timezone-aware")

    current_runtime: InSeasonForecastRuntimeResult | None = None
    current_failure: str | None = None
    try:
        current_runtime = build_in_season_forecasts(
            league_state,
            horizon=ForecastHorizon.REST_OF_SEASON,
            period_start=period_start,
            period_end=period_end,
            history_writer=history_writer,
            clock=lambda: now,
        )
        forward = current_runtime.fantasy_point_forecasts
        basis = "current_rest_of_season"
    except Exception as exc:
        current_failure = f"{type(exc).__name__}: {exc}"
        forward = remaining_prior_from_preseason(
            league_state,
            preseason_season_forecasts=preseason_season_forecasts,
            completed_through_week=completed,
            as_of=now,
        )
        basis = "preseason_remaining_prior"

    season_outlook = compose_completed_actuals_with_ros(
        completed_actuals=actuals,
        ros_forecasts=forward,
        season_start=canonical_week_window(league_state.league.season, 1)[0],
    )
    return GovernedInSeasonResult(
        completed_through_week=completed,
        season_outlook=season_outlook,
        forward_forecasts=forward,
        evidence_basis=basis,
        current_runtime=current_runtime,
        current_failure=current_failure,
    )
