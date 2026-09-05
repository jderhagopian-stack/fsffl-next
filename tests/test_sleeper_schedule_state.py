from datetime import UTC, datetime

from fsffl.providers.sleeper import SleeperNormalizer, SleeperPayloadBundle
from fsffl.providers.sleeper_live import SleeperLiveSource


NOW = datetime(2026, 9, 5, 22, tzinfo=UTC)


def _league_payload() -> dict:
    return {
        "league_id": "123",
        "name": "Schedule League",
        "season": 2026,
        "settings": {
            "num_teams": 2,
            "roster_size": 1,
            "playoff_teams": 2,
            "playoff_week_start": 15,
        },
        "roster_positions": ["QB"],
        "scoring_settings": {"pass_yd": 0.04},
    }


def test_sleeper_live_acquires_only_configured_regular_season_weeks() -> None:
    requested: list[str] = []

    def get_json(url: str):
        requested.append(url)
        if url.endswith("/league/123"):
            return _league_payload()
        if url.endswith("/league/123/users"):
            return []
        if url.endswith("/league/123/rosters"):
            return []
        if url.endswith("/players/nfl"):
            return {}
        if url.endswith("/league/123/traded_picks"):
            return []
        if "/league/123/matchups/" in url:
            return []
        if url.endswith("/schedule/nfl/regular/2026"):
            return []
        raise AssertionError(url)

    snapshot = SleeperLiveSource(http_get_json=get_json, clock=lambda: NOW).fetch_latest(
        league_external_id="123"
    )
    assert tuple(snapshot.payload["matchups"]) == tuple(str(week) for week in range(1, 15))
    matchup_urls = [url for url in requested if "/matchups/" in url]
    assert len(matchup_urls) == 14
    assert matchup_urls[0].endswith("/matchups/1")
    assert matchup_urls[-1].endswith("/matchups/14")
    assert requested[-1].endswith("/schedule/nfl/regular/2026")


def test_sleeper_schedule_normalizes_to_canonical_team_ids_and_points() -> None:
    bundle = SleeperPayloadBundle(
        league=_league_payload(),
        users=(
            {"user_id": "u1", "display_name": "One"},
            {"user_id": "u2", "display_name": "Two"},
        ),
        rosters=(
            {"roster_id": 1, "owner_id": "u1", "players": [], "starters": []},
            {"roster_id": 2, "owner_id": "u2", "players": [], "starters": []},
        ),
        players={},
        matchups={
            "1": (
                {"matchup_id": 7, "roster_id": 1, "points": 101.5},
                {"matchup_id": 7, "roster_id": 2, "points": 98.25},
            ),
            "2": (
                {"matchup_id": 8, "roster_id": 2, "points": 110.0},
                {"matchup_id": 8, "roster_id": 1, "points": 87.0},
            ),
        },
        retrieved_at=NOW,
    )

    state = SleeperNormalizer().normalize(bundle, as_of=NOW)
    assert state.league.rules.playoff_team_count == 2
    assert len(state.matchups) == 2
    first = state.matchups[0]
    assert first.week == 1
    assert first.team_a_id == "sleeper:123:team:1"
    assert first.team_b_id == "sleeper:123:team:2"
    assert first.team_a_points == 101.5
    assert first.team_b_points == 98.25
    assert first.provenance.source == "sleeper:matchups"
