from __future__ import annotations

from fsffl.analytics.league import LeagueAnalyticsView, LeagueMetric, rank_league_metric

from .visualization import ChartDataPoint, ChartKind, ChartSeries, InteractiveChartSpec


_METRIC_TITLES = {
    LeagueMetric.OPTIMIZED_EXPECTED_POINTS: "Projected scoring by team",
    LeagueMetric.EXPECTED_WINS: "Expected wins by team",
    LeagueMetric.PLAYOFF_PROBABILITY: "Playoff probability by team",
    LeagueMetric.FIRST_PLACE_PROBABILITY: "First-place probability by team",
    LeagueMetric.ASSET_PORTFOLIO_MEAN: "Dynasty asset value by team",
    LeagueMetric.LARGEST_SINGLE_PLAYER_LINEUP_DROP: "Lineup fragility by team",
    LeagueMetric.DRAFT_PICK_COUNT: "Draft capital count by team",
}

_METRIC_UNITS = {
    LeagueMetric.OPTIMIZED_EXPECTED_POINTS: "fantasy points",
    LeagueMetric.EXPECTED_WINS: "wins",
    LeagueMetric.PLAYOFF_PROBABILITY: "probability",
    LeagueMetric.FIRST_PLACE_PROBABILITY: "probability",
    LeagueMetric.ASSET_PORTFOLIO_MEAN: "value",
    LeagueMetric.LARGEST_SINGLE_PLAYER_LINEUP_DROP: "fantasy points",
    LeagueMetric.DRAFT_PICK_COUNT: "picks",
}


def build_league_metric_chart(
    view: LeagueAnalyticsView,
    *,
    metric: LeagueMetric,
    chart_id: str | None = None,
) -> InteractiveChartSpec:
    """Render one explicit NEXT-7 league metric into a chart contract.

    The product layer does not combine or transform league metrics. Ordering comes
    from NEXT-7's named-metric ranking and the raw values are passed through.
    """

    ranking = rank_league_metric(view, metric=metric)
    points = tuple(
        ChartDataPoint(
            key=row.team_id,
            label=row.display_name,
            x=row.display_name,
            y=row.value,
            drilldown_ref=f"team:{row.team_id}",
        )
        for row in ranking.rows
    )
    source_versions = tuple(
        sorted(
            {
                view.view_model_version,
                ranking.ranking_model_version,
                *(entry.model_version for entry in view.context.lineage),
            }
        )
    )
    return InteractiveChartSpec(
        chart_id=chart_id or f"league-{metric.value}",
        kind=ChartKind.BAR,
        title=_METRIC_TITLES[metric],
        description=(
            "Explicit named-metric comparison from NEXT-7. "
            f"Missing teams: {', '.join(ranking.missing_team_ids) if ranking.missing_team_ids else 'none'}."
        ),
        x_label="Team",
        y_label=_METRIC_UNITS[metric],
        series=(
            ChartSeries(
                series_id=metric.value,
                label=_METRIC_TITLES[metric],
                points=points,
                unit=_METRIC_UNITS[metric],
            ),
        ),
        source_view=view.view_model_version,
        source_model_versions=source_versions,
        allow_drilldown=True,
    )
