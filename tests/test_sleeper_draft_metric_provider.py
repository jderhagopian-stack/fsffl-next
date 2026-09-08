from datetime import UTC, datetime

import pytest

from fsffl.providers.sleeper_draft_metric import normalize_sleeper_weekly_realized_scores


def test_sleeper_weekly_scores_use_state_supplied_eligibility():
    rows = (
        {
            "roster_id": 1,
            "players_points": {"10": 20.5, "11": 7.0, "99": 30.0},
        },
        {
            "roster_id": 2,
            "players_points": {"20": 15.0, "21": 9.0},
        },
    )
    result = normalize_sleeper_weekly_realized_scores(
        rows,
        league_id="sleeper:league",
        week=1,
        as_of=datetime(2026, 9, 1, tzinfo=UTC),
        roster_id_to_team_id={1: "team-a", 2: "team-b"},
        eligible_player_ids_by_team={"team-a": ("10", "11"), "team-b": ("20", "21")},
    )
    team_a = next(item for item in result if item.team_id == "team-a")
    assert team_a.eligible_player_ids == ("sleeper:player:10", "sleeper:player:11")
    assert [row.points for row in team_a.scores] == [20.5, 7.0]
    # Ineligible player 99 is deliberately not pulled into the metric.
    assert all(row.player_id != "sleeper:player:99" for row in team_a.scores)


def test_sleeper_weekly_scores_fail_when_eligible_player_score_is_missing():
    with pytest.raises(ValueError, match="missing an eligible player"):
        normalize_sleeper_weekly_realized_scores(
            ({"roster_id": 1, "players_points": {"10": 20.5}},),
            league_id="sleeper:league",
            week=1,
            as_of=datetime(2026, 9, 1, tzinfo=UTC),
            roster_id_to_team_id={1: "team-a"},
            eligible_player_ids_by_team={"team-a": ("10", "11")},
        )
