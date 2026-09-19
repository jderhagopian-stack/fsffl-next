from datetime import UTC, datetime

from fsffl.providers.sleeper_live import SleeperLiveSource


NOW = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)


def test_live_sleeper_source_acquires_provider_payloads_without_model_logic() -> None:
    seen: list[str] = []

    def fake_get(url: str):
        seen.append(url)
        if url.endswith("/league/league123"):
            return {"league_id": "league123", "season": "2026"}
        if url.endswith("/league/league123/users"):
            return [{"user_id": "u1"}]
        if url.endswith("/league/league123/rosters"):
            return [{"roster_id": 1}]
        if url.endswith("/players/nfl"):
            return {"p1": {"player_id": "p1"}}
        if url.endswith("/league/league123/traded_picks"):
            return []
        if url.endswith("/schedule/nfl/regular/2026"):
            return [{"week": 1, "home": "NYJ", "away": "BUF"}]
        raise AssertionError(url)

    source = SleeperLiveSource(http_get_json=fake_get, clock=lambda: NOW)
    snapshot = source.fetch_latest(league_external_id="league123")

    assert snapshot.provider_name == "sleeper"
    assert snapshot.league_external_id == "league123"
    assert snapshot.captured_at == NOW
    assert set(snapshot.payload) == {
        "league",
        "users",
        "rosters",
        "players",
        "traded_picks",
        "matchups",
        "nfl_schedule",
    }
    assert snapshot.payload["matchups"] == {}
    assert snapshot.payload["nfl_schedule"] == [{"week": 1, "home": "NYJ", "away": "BUF"}]
    # A league with no playoff_week_start makes no fantasy-matchup calls, but the
    # factual NFL schedule remains independent league-wide State evidence.
    assert len(seen) == 6
    assert not any("/matchups/" in url for url in seen)


def test_live_source_refuses_to_masquerade_as_historical_evidence() -> None:
    source = SleeperLiveSource(http_get_json=lambda _: {}, clock=lambda: NOW)
    assert source.fetch_at_or_before(league_external_id="league123", as_of=NOW) is None
