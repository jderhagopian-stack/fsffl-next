from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.forecast.models import ForecastHorizon, ForecastMetric
from fsffl.state.models import FrozenModel
from fsffl.team_utility.utility import CalculatedCompetitiveState
from fsffl.value.models import ValueScale

from .models import AnalyticsContext
from .team import TeamAnalyticsView


class LeagueMetric(StrEnum):
    OPTIMIZED_EXPECTED_POINTS = "optimized_expected_points"
    EXPECTED_WINS = "expected_wins"
    PLAYOFF_PROBABILITY = "playoff_probability"
    FIRST_PLACE_PROBABILITY = "first_place_probability"
    ASSET_PORTFOLIO_MEAN = "asset_portfolio_mean"
    LARGEST_SINGLE_PLAYER_LINEUP_DROP = "largest_single_player_lineup_drop"
    DRAFT_PICK_COUNT = "draft_pick_count"


class MetricDirection(StrEnum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


_METRIC_DIRECTIONS = {
    LeagueMetric.OPTIMIZED_EXPECTED_POINTS: MetricDirection.HIGHER_IS_BETTER,
    LeagueMetric.EXPECTED_WINS: MetricDirection.HIGHER_IS_BETTER,
    LeagueMetric.PLAYOFF_PROBABILITY: MetricDirection.HIGHER_IS_BETTER,
    LeagueMetric.FIRST_PLACE_PROBABILITY: MetricDirection.HIGHER_IS_BETTER,
    LeagueMetric.ASSET_PORTFOLIO_MEAN: MetricDirection.HIGHER_IS_BETTER,
    LeagueMetric.LARGEST_SINGLE_PLAYER_LINEUP_DROP: MetricDirection.LOWER_IS_BETTER,
    LeagueMetric.DRAFT_PICK_COUNT: MetricDirection.HIGHER_IS_BETTER,
}


class LeagueTeamAnalyticsRow(FrozenModel):
    team_id: str
    display_name: str
    player_count: int
    draft_pick_count: int
    optimized_expected_points: float | None = None
    expected_wins: float | None = None
    playoff_probability: float | None = None
    first_place_probability: float | None = None
    calculated_competitive_state: CalculatedCompetitiveState | None = None
    asset_portfolio_mean: float | None = None
    asset_value_scale: ValueScale | None = None
    asset_value_concept: str | None = None
    largest_single_player_lineup_drop: float | None = None
    bench_forecasted_count: int | None = None
    missing_forecast_count: int | None = None

    @model_validator(mode="after")
    def validate_row(self) -> "LeagueTeamAnalyticsRow":
        if not self.team_id.strip() or not self.display_name.strip():
            raise ValueError("league analytics team identifiers cannot be blank")
        if self.player_count < 0 or self.draft_pick_count < 0:
            raise ValueError("league analytics counts cannot be negative")
        if (self.asset_portfolio_mean is None) != (self.asset_value_scale is None):
            raise ValueError("asset portfolio mean and scale must be present together")
        return self


class LeagueAnalyticsView(FrozenModel):
    context: AnalyticsContext
    teams: tuple[LeagueTeamAnalyticsRow, ...]
    view_model_version: str = "next7-league-view-v1"

    @model_validator(mode="after")
    def validate_view(self) -> "LeagueAnalyticsView":
        if not self.view_model_version.strip():
            raise ValueError("league analytics view_model_version cannot be blank")
        ids = [team.team_id for team in self.teams]
        if len(ids) != len(set(ids)):
            raise ValueError("league analytics teams must be unique")
        return self


class RankedMetricRow(FrozenModel):
    rank: int
    team_id: str
    display_name: str
    value: float


class LeagueMetricRanking(FrozenModel):
    metric: LeagueMetric
    direction: MetricDirection
    rows: tuple[RankedMetricRow, ...]
    missing_team_ids: tuple[str, ...] = ()
    value_scale: ValueScale | None = None
    ranking_model_version: str = "next7-named-metric-ranking-v1"


def _optimized_regular_season_points(view: TeamAnalyticsView) -> float | None:
    """Prefer the league-specific Forecast horizon for projected scoring.

    The lineup assignment remains owned by Team Utility. Analytics only joins the
    authoritative starter ids to the authoritative fantasy-regular-season player
    forecasts. Older/replayed views with no such horizon retain their existing
    lineup total for backward compatibility.
    """

    lineup = view.optimized_lineup
    if lineup is None:
        return None
    starter_ids = {assignment.player_id for assignment in lineup.assignments}
    if not starter_ids:
        return 0.0

    latest: dict[str, object] = {}
    any_regular_season = False
    for row in view.players:
        if row.player_id not in starter_ids:
            continue
        for observation in row.forecasts:
            if observation.metric != ForecastMetric.FANTASY_POINTS:
                continue
            if observation.horizon != ForecastHorizon.FANTASY_REGULAR_SEASON:
                continue
            any_regular_season = True
            current = latest.get(row.player_id)
            if current is None or observation.as_of > current.as_of:
                latest[row.player_id] = observation

    if not any_regular_season:
        return lineup.expected_points
    if set(latest) != starter_ids:
        return None
    return sum(observation.distribution.mean for observation in latest.values())


def _row_from_team(view: TeamAnalyticsView) -> LeagueTeamAnalyticsRow:
    utility = view.utility
    outcome = utility.competitive_outcome if utility is not None else None
    portfolio = utility.asset_portfolio if utility is not None else None
    resilience = utility.roster_resilience if utility is not None else None
    return LeagueTeamAnalyticsRow(
        team_id=view.team_id,
        display_name=view.display_name,
        player_count=len(view.players),
        draft_pick_count=len(view.draft_picks),
        optimized_expected_points=_optimized_regular_season_points(view),
        expected_wins=outcome.expected_wins if outcome is not None else None,
        playoff_probability=outcome.playoff_probability if outcome is not None else None,
        first_place_probability=outcome.first_place_probability if outcome is not None else None,
        calculated_competitive_state=(
            utility.calculated_competitive_state if utility is not None else None
        ),
        asset_portfolio_mean=portfolio.distribution.mean if portfolio is not None else None,
        asset_value_scale=portfolio.scale if portfolio is not None else None,
        asset_value_concept=portfolio.value_concept if portfolio is not None else None,
        largest_single_player_lineup_drop=(
            resilience.largest_single_player_lineup_drop if resilience is not None else None
        ),
        bench_forecasted_count=(resilience.bench_forecasted_count if resilience is not None else None),
        missing_forecast_count=(resilience.missing_forecast_count if resilience is not None else None),
    )


def build_league_analytics_view(
    *,
    context: AnalyticsContext,
    team_views: tuple[TeamAnalyticsView, ...],
    view_model_version: str = "next7-league-view-v1",
) -> LeagueAnalyticsView:
    for team_view in team_views:
        if team_view.context != context:
            raise ValueError("all team views must use the same analytics context")
    rows = tuple(sorted((_row_from_team(view) for view in team_views), key=lambda row: row.team_id))
    return LeagueAnalyticsView(context=context, teams=rows, view_model_version=view_model_version)


def _metric_value(row: LeagueTeamAnalyticsRow, metric: LeagueMetric) -> float | None:
    if metric == LeagueMetric.DRAFT_PICK_COUNT:
        return float(row.draft_pick_count)
    return getattr(row, metric.value)


def rank_league_metric(
    view: LeagueAnalyticsView,
    *,
    metric: LeagueMetric,
    ranking_model_version: str = "next7-named-metric-ranking-v1",
) -> LeagueMetricRanking:
    """Rank teams on one explicit named metric; never combine metrics."""

    if not ranking_model_version.strip():
        raise ValueError("ranking_model_version cannot be blank")
    direction = _METRIC_DIRECTIONS[metric]
    values: list[tuple[LeagueTeamAnalyticsRow, float]] = []
    missing: list[str] = []
    scale: ValueScale | None = None
    value_concept: str | None = None

    for row in view.teams:
        value = _metric_value(row, metric)
        if value is None:
            missing.append(row.team_id)
            continue
        if metric == LeagueMetric.ASSET_PORTFOLIO_MEAN:
            if row.asset_value_scale is None:
                raise ValueError("asset portfolio ranking requires explicit value scale")
            if scale is None:
                scale = row.asset_value_scale
                value_concept = row.asset_value_concept
            elif row.asset_value_scale != scale or row.asset_value_concept != value_concept:
                raise ValueError("asset portfolio ranking requires same value scale and concept")
        values.append((row, float(value)))

    reverse = direction == MetricDirection.HIGHER_IS_BETTER
    ordered = sorted(
        values,
        key=lambda item: ((-item[1]) if reverse else item[1], item[0].team_id),
    )
    ranked = tuple(
        RankedMetricRow(
            rank=index,
            team_id=row.team_id,
            display_name=row.display_name,
            value=value,
        )
        for index, (row, value) in enumerate(ordered, start=1)
    )
    return LeagueMetricRanking(
        metric=metric,
        direction=direction,
        rows=ranked,
        missing_team_ids=tuple(sorted(missing)),
        value_scale=scale,
        ranking_model_version=ranking_model_version,
    )
