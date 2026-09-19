from datetime import UTC, datetime

import pytest

from fsffl.state.models import LeagueRules, LineupRequirement, Player, Position, RosterSlot
from fsffl.team_utility.realized_metric import (
    RealizedPlayerScore,
    WeeklyEligibleRosterScores,
    calculate_season_realized_max_points,
    calculate_weekly_realized_max_points,
)


RULES = LeagueRules(
    team_count=2,
    roster_size=6,
    rookie_draft_rounds=3,
    lineup=(
        LineupRequirement(slot=RosterSlot.QB, count=1),
        LineupRequirement(slot=RosterSlot.RB, count=1),
        LineupRequirement(slot=RosterSlot.FLEX, count=1),
    ),
    scoring=(),
)
PLAYERS = (
    Player(player_id="q", full_name="Q", position=Position.QB),
    Player(player_id="r1", full_name="R1", position=Position.RB),
    Player(player_id="r2", full_name="R2", position=Position.RB),
    Player(player_id="w", full_name="W", position=Position.WR),
)


def _week(week: int, scores: dict[str, float]):
    return WeeklyEligibleRosterScores(
        league_id="league-generic",
        team_id="team-a",
        week=week,
        as_of=datetime(2026, 9, week, tzinfo=UTC),
        eligible_player_ids=tuple(scores),
        scores=tuple(RealizedPlayerScore(player_id=pid, points=points) for pid, points in scores.items()),
        model_version="provider-week-v1",
        provenance="historical matchup plus verified eligibility",
    )


def test_weekly_realized_max_points_uses_best_legal_lineup_not_actual_starters():
    result = calculate_weekly_realized_max_points(
        _week(1, {"q": 20, "r1": 5, "r2": 15, "w": 12}),
        players=PLAYERS,
        league_rules=RULES,
    )
    assert result.points == 47
    assert set(result.chosen_player_ids) == {"q", "r2", "w"}


def test_weekly_metric_requires_exact_eligible_score_coverage():
    with pytest.raises(ValueError, match="every and only eligible player"):
        WeeklyEligibleRosterScores(
            league_id="league-generic",
            team_id="team-a",
            week=1,
            as_of=datetime(2026, 9, 1, tzinfo=UTC),
            eligible_player_ids=("q", "r1"),
            scores=(RealizedPlayerScore(player_id="q", points=20),),
            model_version="provider-week-v1",
            provenance="historical evidence",
        )


def test_season_metric_sums_weekly_optimal_scores():
    result = calculate_season_realized_max_points(
        (
            _week(1, {"q": 20, "r1": 5, "r2": 15, "w": 12}),
            _week(2, {"q": 10, "r1": 18, "r2": 4, "w": 9}),
        ),
        players=PLAYERS,
        league_rules=RULES,
    )
    assert result.metric_id == "max_pf"
    assert result.total_value == 84
    assert [row.week for row in result.weeks] == [1, 2]
