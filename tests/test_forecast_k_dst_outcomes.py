from __future__ import annotations

from fsffl.forecast.k_dst_outcomes import (
    reconstruct_dst_games_from_nflverse,
    reconstruct_kicker_games_from_nflverse,
)
from fsffl.forecast.models import ForecastMetric


def test_blocked_field_goal_is_a_kicker_miss_with_distance_bucket() -> None:
    rows = (
        {
            "season": 2026,
            "game_id": "2026_01_A_B",
            "kicker_player_id": "k1",
            "field_goal_attempt": 1,
            "field_goal_result": "blocked",
            "kick_distance": 52,
        },
        {
            "season": 2026,
            "game_id": "2026_01_A_B",
            "kicker_player_id": "k1",
            "extra_point_attempt": 1,
            "extra_point_result": "good",
        },
    )

    games = reconstruct_kicker_games_from_nflverse(rows)

    assert len(games) == 1
    game = games[0]
    assert game.value(ForecastMetric.FG_ATTEMPT) == 1
    assert game.value(ForecastMetric.FG_MISS) == 1
    assert game.value(ForecastMetric.FG_MISS_50_59) == 1
    assert game.value(ForecastMetric.XP_ATTEMPT) == 1
    assert game.value(ForecastMetric.XP_MADE) == 1
    assert game.missing_distance_attempts == 0


def test_missing_kick_distance_remains_explicit_instead_of_guessing_a_band() -> None:
    games = reconstruct_kicker_games_from_nflverse(
        (
            {
                "season": 2026,
                "game_id": "g1",
                "kicker_player_id": "k1",
                "field_goal_attempt": 1,
                "field_goal_result": "made",
                "kick_distance": None,
            },
        )
    )

    assert games[0].value(ForecastMetric.FG_MADE) == 1
    assert games[0].missing_distance_attempts == 1
    assert games[0].value(ForecastMetric.FG_MADE_0_19) == 0
    assert games[0].value(ForecastMetric.FG_MADE_60_PLUS) == 0


def test_dst_reconstruction_separates_defensive_and_team_special_teams_touchdowns() -> None:
    rows = (
        {
            "season": 2026,
            "game_id": "g1",
            "defteam": "DEN",
            "interception": 1,
            "touchdown": 1,
            "td_team": "DEN",
            "return_touchdown": 1,
        },
        {
            "season": 2026,
            "game_id": "g1",
            "defteam": "LV",
            "punt_attempt": 1,
            "return_touchdown": 1,
            "touchdown": 1,
            "td_team": "DEN",
        },
    )

    games = reconstruct_dst_games_from_nflverse(rows)
    den = next(game for game in games if game.subject.nfl_team == "DEN")

    assert den.value(ForecastMetric.DST_INTERCEPTION) == 1
    assert den.value(ForecastMetric.DST_DEFENSIVE_TD) == 1
    assert den.value(ForecastMetric.DST_TEAM_ST_TD) == 1


def test_dst_team_aliases_are_canonicalized_in_realized_outcomes() -> None:
    games = reconstruct_dst_games_from_nflverse(
        (
            {
                "season": 2026,
                "game_id": "g1",
                "defteam": "JAC",
                "sack": 1,
            },
        )
    )

    assert games[0].subject.nfl_team == "JAX"
    assert games[0].value(ForecastMetric.DST_SACK) == 1
