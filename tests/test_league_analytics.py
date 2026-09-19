from datetime import UTC, datetime

from fsffl.analytics.league import (
    LeagueAnalyticsView,
    LeagueMetric,
    LeagueTeamAnalyticsRow,
    MetricDirection,
    rank_league_metric,
)
from fsffl.analytics.models import AnalyticsContext
from fsffl.value.models import ValueScale


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
CONTEXT = AnalyticsContext(
    schema_version="1",
    league_id="l1",
    league_state_id="state-1",
    as_of=AS_OF,
    generated_at=AS_OF,
    lineage=(),
)


def _row(team_id: str, *, wins=None, portfolio=None, scale=None, concept="intrinsic"):
    return LeagueTeamAnalyticsRow(
        team_id=team_id,
        display_name=team_id.upper(),
        player_count=18,
        draft_pick_count=2,
        expected_wins=wins,
        asset_portfolio_mean=portfolio,
        asset_value_scale=scale,
        asset_value_concept=concept if portfolio is not None else None,
    )


def test_rank_named_metric_without_master_score() -> None:
    view = LeagueAnalyticsView(
        context=CONTEXT,
        teams=(
            _row("a", wins=8.0),
            _row("b", wins=10.0),
            _row("c", wins=6.0),
        ),
    )
    ranking = rank_league_metric(view, metric=LeagueMetric.EXPECTED_WINS)

    assert ranking.direction == MetricDirection.HIGHER_IS_BETTER
    assert [(row.rank, row.team_id, row.value) for row in ranking.rows] == [
        (1, "b", 10.0),
        (2, "a", 8.0),
        (3, "c", 6.0),
    ]


def test_rank_named_metric_surfaces_missing_teams() -> None:
    view = LeagueAnalyticsView(
        context=CONTEXT,
        teams=(_row("a", wins=8.0), _row("b", wins=None)),
    )
    ranking = rank_league_metric(view, metric=LeagueMetric.EXPECTED_WINS)

    assert [row.team_id for row in ranking.rows] == ["a"]
    assert ranking.missing_team_ids == ("b",)


def test_asset_portfolio_ranking_fails_on_incompatible_scales() -> None:
    scale_a = ValueScale(scale_id="fsffl", version="1", unit_label="points")
    scale_b = ValueScale(scale_id="other", version="1", unit_label="other")
    view = LeagueAnalyticsView(
        context=CONTEXT,
        teams=(
            _row("a", portfolio=1000.0, scale=scale_a),
            _row("b", portfolio=1200.0, scale=scale_b),
        ),
    )

    try:
        rank_league_metric(view, metric=LeagueMetric.ASSET_PORTFOLIO_MEAN)
    except ValueError as exc:
        assert "same value scale" in str(exc)
    else:
        raise AssertionError("expected incompatible-scale rejection")
