from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep

from fsffl.persistence.state_history import PostgresStateSnapshotStore
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.state.models import League, LeagueRules, LeagueState


NOW = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)


class FakeDatabase:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, object]] = {}
        self.sequence = 0

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return FakeCursor(self.database)


class FakeCursor:
    def __init__(self, database: FakeDatabase) -> None:
        self.database = database
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, params=()) -> None:
        normalized = " ".join(sql.split())
        self.result = None
        if normalized.startswith("insert into fsffl.state_snapshot_history"):
            league_id, state_hash, season, as_of, payload = params
            key = (league_id, state_hash)
            if key not in self.database.rows:
                self.database.sequence += 1
                self.database.rows[key] = {
                    "league_id": league_id,
                    "state_hash": state_hash,
                    "season": season,
                    "as_of": as_of,
                    "payload": json.loads(payload),
                    "recorded_at": NOW + timedelta(seconds=self.database.sequence),
                }
            return
        if normalized.startswith("select state_hash, payload from fsffl.state_snapshot_history where league_id=%s and state_hash=%s"):
            row = self.database.rows.get((params[0], params[1]))
            if row is not None:
                self.result = {"state_hash": row["state_hash"], "payload": row["payload"]}
            return
        if normalized.startswith("select state_hash, payload from fsffl.state_snapshot_history where league_id=%s and as_of <= %s"):
            league_id, cutoff = params
            candidates = [
                row
                for row in self.database.rows.values()
                if row["league_id"] == league_id and row["as_of"] <= cutoff
            ]
            if candidates:
                row = max(candidates, key=lambda item: (item["as_of"], item["recorded_at"]))
                self.result = {"state_hash": row["state_hash"], "payload": row["payload"]}
            return
        raise AssertionError(f"unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result


def _state(*, as_of: datetime) -> LeagueState:
    return LeagueState(
        league=League(
            league_id="sleeper:history",
            name="History League",
            season=2026,
            rules=LeagueRules(team_count=0, roster_size=0, lineup=(), scoring=()),
        ),
        as_of=as_of,
        teams=(),
        team_states=(),
        players=(),
        player_states=(),
    )


def test_postgres_state_history_survives_restart_and_respects_point_in_time_cutoff() -> None:
    database = FakeDatabase()
    first = PostgresStateSnapshotStore("postgresql://test", connect_factory=database.connect)
    older = _state(as_of=NOW)
    newer = _state(as_of=NOW + timedelta(hours=1))
    first.save(older)
    first.save(newer)

    restarted = PostgresStateSnapshotStore("postgresql://test", connect_factory=database.connect)

    assert restarted.latest_at_or_before("sleeper:history", NOW + timedelta(minutes=30)) == older
    assert restarted.latest_at_or_before("sleeper:history", NOW + timedelta(hours=2)) == newer
    assert restarted.latest_at_or_before("sleeper:history", NOW - timedelta(seconds=1)) is None


def test_runtime_checkpoint_retains_canonical_state_history_off_request_path(monkeypatch) -> None:
    monkeypatch.delenv("FSFFL_DATABASE_URL", raising=False)
    captured: list[LeagueState] = []

    class CapturingHistory:
        def save(self, state: LeagueState) -> None:
            captured.append(state)

        def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None:
            return None

    runtime = PersistentPrivateBetaRuntimeStore(state_snapshot_store=CapturingHistory())
    state = _state(as_of=NOW)

    before = monotonic()
    runtime.set_league_state("jimmy", state)
    assert monotonic() - before < 0.25

    deadline = monotonic() + 2
    while not captured and monotonic() < deadline:
        sleep(0.01)

    assert captured == [state]
    assert runtime.get("jimmy").league_state == state
