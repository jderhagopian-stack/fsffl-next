from datetime import UTC, datetime

from fsffl.forecast.models import ForecastHorizon
from fsffl.state.models import Position, RosterSlot
from fsffl.team_utility.models import LineupAssignment, OptimizedTeamLineup
from fsffl.team_utility.position_strength import build_league_relative_position_strengths


NOW = datetime(2026, 9, 8, tzinfo=UTC)


def _lineup(team_id: str, rb_points: float, wr_points: float) -> OptimizedTeamLineup:
    assignments = (
        LineupAssignment(
            slot=RosterSlot.RB,
            slot_index=1,
            player_id=f"{team_id}-rb",
            position=Position.RB,
            expected_points=rb_points,
        ),
        LineupAssignment(
            slot=RosterSlot.WR,
            slot_index=1,
            player_id=f"{team_id}-wr",
            position=Position.WR,
            expected_points=wr_points,
        ),
    )
    return OptimizedTeamLineup(
        team_id=team_id,
        as_of=NOW,
        horizon=ForecastHorizon.SEASON,
        assignments=assignments,
        expected_points=sum(item.expected_points for item in assignments),
        model_version="test-lineup-v1",
    )


def test_position_strength_index_preserves_distance_from_league_average() -> None:
    rows = build_league_relative_position_strengths(
        (
            _lineup("a", rb_points=150.0, wr_points=100.0),
            _lineup("b", rb_points=50.0, wr_points=100.0),
        ),
        positions=(Position.RB,),
    )
    by_team = {row.team_id: row for row in rows}

    assert by_team["a"].league_average_expected_points == 100.0
    assert by_team["a"].strength_index == 150.0
    assert by_team["a"].league_rank == 1
    assert by_team["b"].strength_index == 50.0
    assert by_team["b"].league_rank == 2


def test_position_strength_attributes_flex_to_actual_player_position() -> None:
    lineup_a = _lineup("a", rb_points=100.0, wr_points=100.0)
    lineup_b = OptimizedTeamLineup(
        team_id="b",
        as_of=NOW,
        horizon=ForecastHorizon.SEASON,
        assignments=(
            LineupAssignment(
                slot=RosterSlot.FLEX,
                slot_index=1,
                player_id="b-flex-rb",
                position=Position.RB,
                expected_points=100.0,
            ),
        ),
        expected_points=100.0,
        model_version="test-lineup-v1",
    )
    rows = build_league_relative_position_strengths(
        (lineup_a, lineup_b),
        positions=(Position.RB,),
    )

    assert all(row.expected_points == 100.0 for row in rows)
    assert all(row.strength_index == 100.0 for row in rows)
