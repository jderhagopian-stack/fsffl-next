from datetime import UTC, datetime

from fsffl.providers.sleeper_live import SleeperLiveSource


NOW = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)


def test_live_sleeper_source_acquires_provider_payloads_without_model_logic() -> None:
    seen: list[str] = []

    def fake_get(url: str):
        seen.append(url)
        if url.endswith("/league/league123"):
            return {"league_id": "league123"}
        if url.endswith("/league/league123/users"):
            return [{"user_id": "u1"}]
        if url.endswith("/league/league123/rosters"):
            return [{"roster_id": 1}]
        if url.endswith("/players/nfl"):
            return {"p1": {"player_id": "p1"}}
        if url.endswith("/league/league123/traded_picks"):
            return []
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
    }
    assert snapshot.payload["matchups"] == {}
    # A provider payload with no playoff_week_start carries no provable regular-
    # season horizon, so acquisition fails closed rather than guessing weeks.
    assert len(seen) == 5
    assert not any("/matchups/" in url for url in seen)


def test_live_source_refuses_to_masquerade_as_historical_evidence() -> None:
    source = SleeperLiveSource(http_get_json=lambda _: {}, clock=lambda: NOW)
    assert source.fetch_at_or_before(league_external_id="league123", as_of=NOW) is None
