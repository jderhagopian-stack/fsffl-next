from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from time import sleep

from fsffl.providers.sleeper_live import SleeperLiveSource


NOW = datetime(2026, 9, 9, 12, tzinfo=UTC)


def test_live_sleeper_fetches_independent_payloads_concurrently() -> None:
    lock = Lock()
    active = 0
    max_active = 0
    requested: list[str] = []

    def get_json(url: str):
        nonlocal active, max_active
        requested.append(url)
        if url.endswith('/v1/league/league-1'):
            return {
                'league_id': 'league-1',
                'season': '2026',
                'settings': {'playoff_week_start': 3, 'num_teams': 2},
            }

        with lock:
            active += 1
            max_active = max(max_active, active)
        try:
            sleep(0.02)
            if url.endswith('/rosters'):
                return [{'roster_id': 1}, {'roster_id': 2}]
            if '/matchups/' in url:
                return []
            if url.endswith('/users'):
                return []
            if url.endswith('/players/nfl'):
                return {}
            if url.endswith('/traded_picks'):
                return []
            if '/schedule/nfl/regular/2026' in url:
                return []
            raise AssertionError(f'unexpected URL {url}')
        finally:
            with lock:
                active -= 1

    source = SleeperLiveSource(http_get_json=get_json, clock=lambda: NOW, max_workers=8)
    snapshot = source.fetch_latest(league_external_id='league-1')

    assert snapshot.payload['league']['league_id'] == 'league-1'
    assert snapshot.payload['matchups'] == {'1': [], '2': []}
    assert len(snapshot.payload['rosters']) == 2
    assert max_active >= 2
    assert any(url.endswith('/players/nfl') for url in requested)
    assert any('/schedule/nfl/regular/2026' in url for url in requested)


def test_live_sleeper_parallel_path_keeps_roster_retry_fail_closed() -> None:
    roster_calls = 0

    def get_json(url: str):
        nonlocal roster_calls
        if url.endswith('/v1/league/league-1'):
            return {
                'league_id': 'league-1',
                'season': '2026',
                'settings': {'playoff_week_start': 2, 'num_teams': 2},
            }
        if url.endswith('/rosters'):
            roster_calls += 1
            return [{'roster_id': 1}]
        if '/matchups/' in url:
            return []
        if url.endswith('/users'):
            return []
        if url.endswith('/players/nfl'):
            return {}
        if url.endswith('/traded_picks'):
            return []
        if '/schedule/nfl/regular/2026' in url:
            return []
        raise AssertionError(f'unexpected URL {url}')

    source = SleeperLiveSource(http_get_json=get_json, clock=lambda: NOW, max_workers=8)

    try:
        source.fetch_latest(league_external_id='league-1')
    except ValueError as exc:
        assert 'expected 2 teams, received 1' in str(exc)
    else:
        raise AssertionError('incomplete rosters must fail closed')

    assert roster_calls == 2
