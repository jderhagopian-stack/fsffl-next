from datetime import UTC, datetime

from fsffl.analytics.league import LeagueAnalyticsView, LeagueMetric, LeagueTeamAnalyticsRow
from fsffl.analytics.models import AnalyticsContext, ModelLineageEntry
from fsffl.product.dashboard import build_league_metric_chart


CONTEXT = AnalyticsContext(
    league_id="l1",
    league_state_id="s1",
    as_of=datetime(2026, 9, 5, tzinfo=UTC),
    generated_at=datetime(2026, 9, 5, 1, tzinfo=UTC),
    lineage=(ModelLineageEntry(component="simulation", model_version="next4-sim-v1"),),
)


def _view() -> LeagueAnalyticsView:
    return LeagueAnalyticsView(
        context=CONTEXT,
        teams=(
            LeagueTeamAnalyticsRow(
                team_id="a",
                display_name="Alpha",
                player_count=10,
                draft_pick_count=3,
                expected_wins=9.0,
                playoff_probability=0.75,
            ),
            LeagueTeamAnalyticsRow(
                team_id="b",
                display_name="Beta",
                player_count=10,
                draft_pick_count=5,
                expected_wins=7.0,
                playoff_probability=0.55,
            ),
        ),
    )


def test_league_chart_uses_named_metric_ranking_without_rescoring() -> None:
    chart = build_league_metric_chart(_view(), metric=LeagueMetric.EXPECTED_WINS)
    assert [point.label for point in chart.series[0].points] == ["Alpha", "Beta"]
    assert [point.y for point in chart.series[0].points] == [9.0, 7.0]
    assert all(point.drilldown_ref for point in chart.series[0].points)


def test_league_chart_propagates_model_lineage() -> None:
    chart = build_league_metric_chart(_view(), metric=LeagueMetric.PLAYOFF_PROBABILITY)
    assert "next4-sim-v1" in chart.source_model_versions
    assert "next7-league-view-v1" in chart.source_model_versions
