from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fsffl.persistence.contracts import SyncCursorRecord
from fsffl.product.hosted_connect import _full_refresh_due, _probe_matches_cursor
from fsffl.providers.sleeper_live import SleeperLiveSource, SleeperSyncProbe


NOW = datetime(2026, 9, 9, 22, 0, tzinfo=UTC)


def _payloads(*, roster_player: str = "p1", traded_owner: int = 2, points: float = 10.0):
    return {
        "/league/123": {
            "league_id": "123",
            "season": "2026",
            "settings": {"num_teams": 2, "playoff_week_start": 15},
        },
        "/state/nfl": {"season": "2026", "week": 3},
        "/league/123/rosters": [
            {"roster_id": 1, "owner_id": "o1", "players": [roster_player]},
            {"roster_id": 2, "owner_id": "o2", "players": ["p2"]},
        ],
        "/league/123/users": [
            {"user_id": "o1", "display_name": "One"},
            {"user_id": "o2", "display_name": "Two"},
        ],
        "/league/123/traded_picks": [
            {"season": "2027", "round": 1, "roster_id": 1, "owner_id": traded_owner}
        ],
        "/league/123/matchups/2": [
            {"roster_id": 1, "matchup_id": 1, "points": points},
            {"roster_id": 2, "matchup_id": 1, "points": 8.0},
        ],
        "/league/123/matchups/3": [
            {"roster_id": 1, "matchup_id": 1, "points": 0.0},
            {"roster_id": 2, "matchup_id": 1, "points": 0.0},
        ],
    }


def _source(payloads):
    def get(url: str):
        path = url.removeprefix("https://api.sleeper.app/v1")
        return payloads[path]

    return SleeperLiveSource(http_get_json=get, clock=lambda: NOW, max_workers=4)


def test_sync_probe_is_deterministic_for_same_league_facts() -> None:
    first = _source(_payloads()).fetch_sync_probe(league_external_id="123")
    second = _source(_payloads()).fetch_sync_probe(league_external_id="123")

    assert first.fingerprint == second.fingerprint
    assert first.season == 2026
    assert first.week == 3
    assert first.captured_at == NOW


def test_sync_probe_changes_for_current_league_mutations() -> None:
    baseline = _source(_payloads()).fetch_sync_probe(league_external_id="123")
    roster_change = _source(_payloads(roster_player="p9")).fetch_sync_probe(league_external_id="123")
    pick_change = _source(_payloads(traded_owner=1)).fetch_sync_probe(league_external_id="123")
    matchup_change = _source(_payloads(points=24.5)).fetch_sync_probe(league_external_id="123")

    assert roster_change.fingerprint != baseline.fingerprint
    assert pick_change.fingerprint != baseline.fingerprint
    assert matchup_change.fingerprint != baseline.fingerprint


def _cursor(probe: SleeperSyncProbe, *, full_refresh_at: datetime) -> SyncCursorRecord:
    return SyncCursorRecord(
        provider="sleeper",
        scope_kind="league_refresh",
        scope_id="123",
        cursor_payload={
            "probe_fingerprint": probe.fingerprint,
            "season": probe.season,
            "week": probe.week,
            "last_full_refresh_at": full_refresh_at.isoformat(),
        },
        synced_at=NOW,
        source_updated_at=probe.captured_at,
    )


def test_matching_probe_can_reuse_recent_full_refresh() -> None:
    probe = _source(_payloads()).fetch_sync_probe(league_external_id="123")
    cursor = _cursor(probe, full_refresh_at=NOW - timedelta(minutes=10))

    assert _probe_matches_cursor(cursor, probe)
    assert not _full_refresh_due(cursor, now=NOW, full_refresh_seconds=3600)


def test_changed_probe_or_aged_cursor_forces_full_refresh() -> None:
    probe = _source(_payloads()).fetch_sync_probe(league_external_id="123")
    changed = _source(_payloads(roster_player="p9")).fetch_sync_probe(league_external_id="123")
    fresh_cursor = _cursor(probe, full_refresh_at=NOW - timedelta(minutes=5))
    old_cursor = _cursor(probe, full_refresh_at=NOW - timedelta(hours=2))

    assert not _probe_matches_cursor(fresh_cursor, changed)
    assert _full_refresh_due(old_cursor, now=NOW, full_refresh_seconds=3600)


def test_missing_or_malformed_cursor_fails_closed_to_full_refresh() -> None:
    assert _full_refresh_due(None, now=NOW, full_refresh_seconds=3600)
    bad = SyncCursorRecord(
        provider="sleeper",
        scope_kind="league_refresh",
        scope_id="123",
        cursor_payload={"last_full_refresh_at": "not-a-time"},
        synced_at=NOW,
    )
    assert _full_refresh_due(bad, now=NOW, full_refresh_seconds=3600)
