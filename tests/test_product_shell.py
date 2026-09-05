from datetime import UTC, datetime

import pytest

from fsffl.product import (
    ChartDataPoint,
    ChartKind,
    ChartSeries,
    HeatMapCell,
    HeatMapSpec,
    InteractiveChartSpec,
    ProductContext,
    ProductRoute,
    available_navigation,
)


def test_navigation_unlocks_with_league_and_team_context() -> None:
    empty = ProductContext(user_id="u1")
    assert available_navigation(empty) == ()

    league = ProductContext(user_id="u1", league_id="l1")
    assert {item.route for item in available_navigation(league)} == {
        ProductRoute.LEAGUE,
        ProductRoute.ANALYTICS,
        ProductRoute.REPORTS,
    }

    team = ProductContext(user_id="u1", league_id="l1", team_id="t1")
    assert {item.route for item in available_navigation(team)} == set(ProductRoute)


def test_team_requires_selected_league() -> None:
    with pytest.raises(ValueError, match="team selection requires selected league"):
        ProductContext(user_id="u1", team_id="t1")


def test_product_context_requires_timezone_for_evidence_cutoff() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ProductContext(
            user_id="u1",
            league_id="l1",
            evidence_as_of=datetime(2026, 9, 5),
        )
    ProductContext(
        user_id="u1",
        league_id="l1",
        evidence_as_of=datetime(2026, 9, 5, tzinfo=UTC),
    )


def test_chart_contract_preserves_source_lineage_and_drilldown() -> None:
    chart = InteractiveChartSpec(
        chart_id="league-wins",
        kind=ChartKind.BAR,
        title="Expected wins",
        source_view="next7:league",
        source_model_versions=("next4-sim-v1",),
        series=(
            ChartSeries(
                series_id="wins",
                label="Expected wins",
                points=(
                    ChartDataPoint(
                        key="team-a",
                        label="Team A",
                        y=8.2,
                        drilldown_ref="team:a",
                    ),
                ),
            ),
        ),
    )
    assert chart.series[0].points[0].drilldown_ref == "team:a"
    assert chart.source_model_versions == ("next4-sim-v1",)


def test_heatmap_rejects_duplicate_cells() -> None:
    with pytest.raises(ValueError, match="unique row/column"):
        HeatMapSpec(
            heatmap_id="roster",
            title="Roster strength",
            metric_name="explicit metric",
            source_view="next7:league",
            cells=(
                HeatMapCell(row_key="a", row_label="A", column_key="qb", column_label="QB", value=1.0),
                HeatMapCell(row_key="a", row_label="A", column_key="qb", column_label="QB", value=2.0),
            ),
        )
