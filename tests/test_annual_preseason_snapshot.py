from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.annual_preseason_service import (
    capture_first_valid_annual_preseason_snapshot,
)
from fsffl.forecast.annual_preseason_snapshot import (
    annual_preseason_capture_window,
    capture_annual_preseason_projection_snapshot,
    provider_projection_payload_sha256,
    replay_annual_preseason_snapshot_for_league_rules,
)
from fsffl.forecast.current_runtime import NamedCurrentProjectionFetcher
from fsffl.providers.current_projection_rows import (
    CurrentProjectionRow,
    CurrentProjectionSnapshot,
)
from fsffl.state.models import LeagueRules, Player, Position, ScoringRule


CAPTURED_AT = datetime(2027, 8, 26, 15, 0, tzinfo=UTC)
EFFECTIVE_AT = datetime(2027, 8, 25, 12, 0, tzinfo=UTC)
SCHEDULE = (
    {"week": 1, "date": "2027-09-09", "home": "PHI", "away": "DAL"},
    {"week": 1, "date": "2027-09-12", "home": "BUF", "away": "NYJ"},
)
PLAYERS = (
    Player(
        player_id="sleeper:player:josh",
        full_name="Josh Allen",
        position=Position.QB,
        nfl_team="BUF",
    ),
)


def _snapshot(
    provider: str,
    *,
    pass_yd: float,
    reverse_rows: bool = False,
) -> CurrentProjectionSnapshot:
    rows = [
        CurrentProjectionRow(
            provider=provider,
            external_id=f"{provider}:josh",
            player_name="Josh Allen",
            position=Position.QB,
            nfl_team="BUF",
            stats={
                "pass_yd": pass_yd,
                "pass_td": 30.0 if provider == "alpha" else 32.0,
                "pass_int": 10.0 if provider == "alpha" else 11.0,
                "rush_yd": 500.0 if provider == "alpha" else 600.0,
                "rush_td": 7.0 if provider == "alpha" else 8.0,
            },
        ),
        CurrentProjectionRow(
            provider=provider,
            external_id=f"{provider}:unmatched",
            player_name="Unmatched Player",
            position=Position.WR,
            nfl_team="FA",
            stats={"rec": 1.0, "rec_yd": 5.0, "rec_td": 0.0},
        ),
    ]
    if reverse_rows:
        rows.reverse()
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=CAPTURED_AT,
        effective_at=EFFECTIVE_AT,
        rows=tuple(rows),
        source_version=f"{provider}-fixture-v1",
        usage_class="fixture",
    )


def _fetcher(provider: str, pass_yd: float) -> NamedCurrentProjectionFetcher:
    return NamedCurrentProjectionFetcher(
        source_id=provider,
        fetch=lambda _season: _snapshot(provider, pass_yd=pass_yd),
    )


class _Store:
    def __init__(self):
        self.record = None
        self.puts = []

    def get_latest_reusable_artifact(self, **_kwargs):
        return self.record

    def put_artifact(self, record):
        self.puts.append(record)
        self.record = record


def test_capture_window_begins_fourteen_days_before_schedule_opener() -> None:
    target, opener = annual_preseason_capture_window(SCHEDULE, season=2027)

    assert opener.isoformat() == "2027-09-09"
    assert target.isoformat() == "2027-08-26"


def test_provider_payload_hash_ignores_row_order_but_not_content() -> None:
    original = _snapshot("alpha", pass_yd=4000.0)
    reordered = _snapshot("alpha", pass_yd=4000.0, reverse_rows=True)
    corrected = _snapshot("alpha", pass_yd=4100.0)

    assert provider_projection_payload_sha256(original) == provider_projection_payload_sha256(reordered)
    assert provider_projection_payload_sha256(original) != provider_projection_payload_sha256(corrected)


def test_capture_refuses_to_run_before_t_minus_fourteen() -> None:
    with pytest.raises(ValueError, match="window has not opened"):
        capture_annual_preseason_projection_snapshot(
            season=2027,
            canonical_players=PLAYERS,
            schedule_rows=SCHEDULE,
            fetchers=(_fetcher("alpha", 4000.0), _fetcher("beta", 4200.0)),
            clock=lambda: CAPTURED_AT - timedelta(days=1),
        )


def test_valid_capture_preserves_provider_rows_and_replays_later_league_scoring() -> None:
    snapshot = capture_annual_preseason_projection_snapshot(
        season=2027,
        canonical_players=PLAYERS,
        schedule_rows=SCHEDULE,
        fetchers=(_fetcher("alpha", 4000.0), _fetcher("beta", 4200.0)),
        clock=lambda: CAPTURED_AT,
    )

    assert snapshot.successful_source_ids == ("alpha", "beta")
    assert snapshot.capture_offset_days_before_opener == 14
    assert snapshot.opener_coordinate_precision == "date"
    assert len(snapshot.provider_evidence) == 2
    assert all(item.raw_rows for item in snapshot.provider_evidence)
    assert all(item.provider_payload_sha256 for item in snapshot.provider_evidence)
    assert all(item.normalized_observations_sha256 for item in snapshot.provider_evidence)
    assert snapshot.governed_raw_ensemble
    assert snapshot.governed_raw_ensemble_sha256

    rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
        ),
    )
    scored = replay_annual_preseason_snapshot_for_league_rules(snapshot, rules=rules)

    assert len(scored) == 1
    assert scored[0].distribution.mean == pytest.approx(367.0)
    assert scored[0].source == "fsffl:annual_preseason_snapshot_league_scored"


def test_failed_attempt_writes_nothing_and_later_valid_attempt_can_retry() -> None:
    store = _Store()

    with pytest.raises(ValueError, match="retry before kickoff"):
        capture_first_valid_annual_preseason_snapshot(
            store,
            season=2027,
            canonical_players=PLAYERS,
            schedule_rows=SCHEDULE,
            fetchers=(_fetcher("alpha", 4000.0),),
            clock=lambda: CAPTURED_AT,
        )

    assert store.puts == []

    result = capture_first_valid_annual_preseason_snapshot(
        store,
        season=2027,
        canonical_players=PLAYERS,
        schedule_rows=SCHEDULE,
        fetchers=(_fetcher("alpha", 4000.0), _fetcher("beta", 4200.0)),
        clock=lambda: CAPTURED_AT + timedelta(days=1),
    )

    assert result.created is True
    assert len(store.puts) == 1
    assert result.snapshot.capture_offset_days_before_opener == 13


def test_first_valid_snapshot_is_reused_without_provider_refetch_or_rewrite() -> None:
    store = _Store()
    first = capture_first_valid_annual_preseason_snapshot(
        store,
        season=2027,
        canonical_players=PLAYERS,
        schedule_rows=SCHEDULE,
        fetchers=(_fetcher("alpha", 4000.0), _fetcher("beta", 4200.0)),
        clock=lambda: CAPTURED_AT,
    )
    assert first.created is True

    def should_not_fetch(_season: int):
        raise AssertionError("existing first-valid snapshot must prevent refetch")

    second = capture_first_valid_annual_preseason_snapshot(
        store,
        season=2027,
        canonical_players=PLAYERS,
        schedule_rows=SCHEDULE,
        fetchers=(
            NamedCurrentProjectionFetcher(source_id="alpha", fetch=should_not_fetch),
            NamedCurrentProjectionFetcher(source_id="beta", fetch=should_not_fetch),
        ),
        clock=lambda: CAPTURED_AT + timedelta(days=2),
    )

    assert second.created is False
    assert second.snapshot.governed_raw_ensemble_sha256 == first.snapshot.governed_raw_ensemble_sha256
    assert len(store.puts) == 1
