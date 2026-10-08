"""Tranche B: identical PIT market rows and bounded SQL on full-size fixtures.

Fake cursor executes the parameterized SQL's VALUES rows transactionally; no
production provider, model, Supabase connection or publication job is touched.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
import tracemalloc

import pytest

from fsffl.persistence.contracts import MarketValueSnapshotRecord
from fsffl.persistence.postgres import PostgresPersistenceStore


def _key(row):
    return (row[0], row[1], row[2], row[3], row[4])


class SQLFixtureDB:
    """Commit/rollback simulator retaining the exact first-writer SQL semantics."""

    def __init__(self, *, fail_statement=None):
        self.rows = {}
        self.statements = 0
        self.transactions = 0
        self.connection_checkouts = 0
        self.fail_statement = fail_statement
        self.sql = []

    @contextmanager
    def connect(self):
        self.connection_checkouts += 1
        pending = []
        owner = self

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, sql, params):
                assert "insert into fsffl.market_value_snapshot" in sql.lower()
                assert "on conflict (asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of)" in sql.lower()
                assert "do nothing" in sql.lower()
                assert "do update" not in sql.lower()
                assert sql.count("::jsonb") == len(params) // 8
                assert len(params) % 8 == 0
                owner.statements += 1
                owner.sql.append(sql)
                if owner.statements == owner.fail_statement:
                    raise RuntimeError("simulated failure before SQL completion")
                for index in range(0, len(params), 8):
                    args = params[index:index + 8]
                    pending.append((*args[:7], json.loads(args[7])))

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, typ, exc, tb):
                if typ is None:
                    for row in pending:
                        owner.rows.setdefault(_key(row), row)
                    owner.transactions += 1
                return False

            def cursor(self):
                return Cursor()

        with Connection() as conn:
            yield conn


def _fixture(count=540):
    now = datetime(2026, 10, 8, 13, tzinfo=UTC)
    out = []
    for i in range(count):
        out.append(MarketValueSnapshotRecord(
            asset_ref=f"player:{i:04d}",
            asset_kind="player" if i % 3 else "future_pick",
            scale_id="dynasty-market-v2" if i % 5 else "market-units",
            market_context_id=f"12t:sf:{i % 2}:0.5ppr",
            estimate_as_of=now + timedelta(seconds=i % 7),
            value=float(i) + 0.125,
            source_lineage={
                "model_version": "frozen-market-v1",
                "evidence_sources": ["forecast", "scoring-rules", f"sample-{i:04d}"],
            },
            recorded_at=now + timedelta(minutes=3),
        ))
    return tuple(out)


def _run_legacy(store, records):
    for row in records:
        store.append_market_value_snapshot(
            asset_ref=row.asset_ref,
            asset_kind=row.asset_kind,
            scale_id=row.scale_id,
            market_context_id=row.market_context_id,
            estimate_as_of=row.estimate_as_of,
            value=row.value,
            source_lineage=row.source_lineage,
            recorded_at=row.recorded_at,
        )


def _store(monkeypatch, db):
    monkeypatch.setenv("FSFFL_PERSISTENCE_CONNECTION_MODE", "legacy")
    store = PostgresPersistenceStore("postgresql://unused")
    monkeypatch.setattr(store, "_connect", db.connect)
    return store


def test_full_market_540_legacy_equivalence_two_statements(monkeypatch):
    fixture = _fixture()
    legacy = SQLFixtureDB()
    batch = SQLFixtureDB()
    _run_legacy(_store(monkeypatch, legacy), fixture)
    _store(monkeypatch, batch).append_market_value_snapshots(fixture)

    assert batch.rows == legacy.rows
    assert len(batch.rows) == len(fixture) == 540
    assert legacy.statements == legacy.transactions == 540
    assert batch.statements == batch.transactions == 2
    assert batch.connection_checkouts == 2
    assert all(r[5] == fixture[0].recorded_at for r in batch.rows.values())
    assert batch.rows[_key(next(iter(batch.rows.values())))][7]["model_version"] == "frozen-market-v1"


def test_first_writer_conflicts_within_chunks_between_chunks_and_prior_rows(monkeypatch):
    fixture = list(_fixture(540))
    now = fixture[0].recorded_at
    # Conflicts in the same statement, and in the second statement,
    # carry different value and provenance; earliest writer must survive.
    for i in (0, 2, 299):
        original = fixture[i]
        fixture[i + 1] = MarketValueSnapshotRecord(
            asset_ref=original.asset_ref,
            asset_kind=original.asset_kind,
            scale_id=original.scale_id,
            market_context_id=original.market_context_id,
            estimate_as_of=original.estimate_as_of,
            value=-1000.0,
            source_lineage={"model_version": "later-conflict"},
            recorded_at=now + timedelta(hours=1),
        )
    fixture[301] = MarketValueSnapshotRecord(
        **{**fixture[0].__dict__, "value": -3000.0, "source_lineage": {"model_version": "late-chunk"}}
    )
    older = SQLFixtureDB()
    batched = SQLFixtureDB()
    old_store = _store(monkeypatch, older)
    batch_store = _store(monkeypatch, batched)
    _run_legacy(old_store, fixture)
    batch_store.append_market_value_snapshots(tuple(fixture))
    assert batched.rows == older.rows
    assert len(batched.rows) == len({(
        r.asset_ref, r.asset_kind, r.scale_id, r.market_context_id, r.estimate_as_of
    ) for r in fixture})
    assert batched.rows[_key(next(iter(batched.rows.values())))][7]["model_version"] == "frozen-market-v1"
    assert all("do update" not in sql.lower() for sql in batched.sql)
    # Conflict with preexisting PIT must preserve its first accepted lineage.
    previous = dict(batched.rows)
    replacement = [
        MarketValueSnapshotRecord(**{**r.__dict__, "value": -99999.0, "source_lineage": {"model_version": "overwrite-attempt"}})
        for r in fixture
    ]
    batch_store.append_market_value_snapshots(replacement)
    assert batched.rows == previous


def test_idempotency_and_empty_does_not_checkout(monkeypatch):
    db = SQLFixtureDB()
    s = _store(monkeypatch, db)
    s.append_market_value_snapshots(())
    assert db.statements == db.connection_checkouts == 0
    rows = _fixture(540)
    s.append_market_value_snapshots(rows)
    before = dict(db.rows)
    s.append_market_value_snapshots(rows)
    assert db.rows == before
    assert db.statements == 4
    assert db.transactions == 4


def test_partial_chunk_failure_preserves_prior_committed_chunk(monkeypatch):
    db = SQLFixtureDB(fail_statement=2)
    s = _store(monkeypatch, db)
    with pytest.raises(RuntimeError, match="simulated failure"):
        s.append_market_value_snapshots(_fixture())
    assert db.statements == 2
    assert db.transactions == 1
    assert len(db.rows) == 300
    # Retry after a transient failure is managed by the *caller*, not SQL
    # execution; first rows and all their original lineage survive.
    before = dict(db.rows)
    db.fail_statement = None
    s.append_market_value_snapshots(_fixture())
    assert len(db.rows) == 540
    assert all(db.rows[k] == row for k, row in before.items())


def test_chunk_bounds_deterministic_sql_and_small_memory(monkeypatch):
    fixture = _fixture(1201)
    db1, db2 = SQLFixtureDB(), SQLFixtureDB()
    s1 = _store(monkeypatch, db1)
    s2 = _store(monkeypatch, db2)
    tracemalloc.start()
    try:
        s1.append_market_value_snapshots(fixture)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    s2.append_market_value_snapshots(fixture)
    assert db1.rows == db2.rows
    assert db1.sql == db2.sql
    assert db1.statements == 5  # 300 + 300 + 300 + 300 + 1
    assert max(sql.count("::jsonb") for sql in db1.sql) <= 300
    assert peak < 20 * 1024 * 1024


def test_market_batch_records_require_aware_pit_and_recorded_time():
    row = _fixture(1)[0]
    with pytest.raises(ValueError, match="estimate_as_of"):
        MarketValueSnapshotRecord(**{**row.__dict__, "estimate_as_of": datetime(2026, 10, 8)})
    with pytest.raises(ValueError, match="recorded_at"):
        MarketValueSnapshotRecord(**{**row.__dict__, "recorded_at": datetime(2026, 10, 8)})
