"""Tranche A: adapter-only transport regressions; no production DB required."""
from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from threading import BoundedSemaphore, Lock
from time import sleep
from types import SimpleNamespace

import pytest

from fsffl.persistence.contracts import UserPerceivedLatencyRecord
from fsffl.persistence.postgres import PostgresPersistenceStore


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.conn.pending.append((sql, params))

    def fetchone(self):
        return None


class FakeConnection:
    def __init__(self, backend):
        self.backend = backend
        self.pending = []
        self.stale = False
        self.check_count = 0

    def __enter__(self):
        assert self.pending == []
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            with self.backend["lock"]:
                self.backend["committed"].extend(self.pending)
        self.pending = []
        return False

    def cursor(self):
        return FakeCursor(self)


class FakePool:
    instances = []

    @staticmethod
    def check_connection(conn):
        conn.check_count += 1
        if conn.stale:
            raise RuntimeError("stale connection")

    def __init__(self, _dsn, **options):
        self.options = options
        self.backend = {"lock": Lock(), "committed": []}
        self.lock = Lock()
        self.capacity = BoundedSemaphore(options["max_size"])
        self.idle = []
        self.created = 0
        self.checked_out = 0
        self.highwater = 0
        self.opened = False
        self.closed = False
        FakePool.instances.append(self)

    def open(self, wait=False):
        assert wait is False
        assert not self.closed
        self.opened = True

    @contextmanager
    def connection(self):
        assert self.opened and not self.closed
        if not self.capacity.acquire(timeout=0.1):
            raise TimeoutError("pool checkout timeout")
        with self.lock:
            conn = self.idle.pop() if self.idle else FakeConnection(self.backend)
            self.created += 0 if conn in self.idle else 0  # tracked below by instances
            self.checked_out += 1
            self.highwater = max(self.highwater, self.checked_out)
        try:
            try:
                self.options["check"](conn)
            except RuntimeError:
                # psycopg_pool rejects stale connections BEFORE any SQL is run.
                conn = FakeConnection(self.backend)
                self.options["check"](conn)
            with conn as active:
                yield active
        finally:
            with self.lock:
                self.idle.append(conn)
                self.checked_out -= 1
            self.capacity.release()

    def get_stats(self):
        return {"requests_num": len(self.backend["committed"]), "pool_size": self.options["max_size"]}

    def close(self, timeout=5):
        assert timeout == 5.0
        self.closed = True


@pytest.fixture
def pooled(monkeypatch):
    import psycopg  # installed by [dev,web] CI dependency

    FakePool.instances = []
    monkeypatch.setenv("FSFFL_PERSISTENCE_CONNECTION_MODE", "pool")
    monkeypatch.setitem(sys.modules, "psycopg_pool", SimpleNamespace(ConnectionPool=FakePool))
    return PostgresPersistenceStore("postgresql://unused")


def _latency(user):
    return UserPerceivedLatencyRecord(
        user_id=user,
        operation="isolated-tranche-a-test",
        elapsed_ms=0.0,
        outcome="success",
        observed_at=datetime(2026, 10, 8, tzinfo=UTC),
        detail=None,
    )


def test_pool_lazy_exact_bounds_and_disabled_prepared_statements(pooled):
    assert FakePool.instances == []
    pooled.append_user_perceived_latency(_latency("u1"))
    assert len(FakePool.instances) == 1
    pool = FakePool.instances[0]
    assert pool.options["min_size"] == 0
    assert pool.options["max_size"] == 3
    assert pool.options["timeout"] == 5.0
    assert pool.options["max_idle"] == 75.0
    assert pool.options["max_lifetime"] == 720.0
    assert pool.options["max_waiting"] == 12
    assert pool.options["kwargs"]["prepare_threshold"] is None
    assert pool.options["open"] is False
    assert pool.opened is True
    pooled.append_user_perceived_latency(_latency("u2"))
    assert len(FakePool.instances) == 1
    assert len(pool.backend["committed"]) == 2


def test_parallel_checkouts_reuse_one_bounded_pool_without_cross_user_leaks(pooled):
    def worker(i):
        with pooled._connect() as conn, conn.cursor() as cur:
            cur.execute("select tenant from fake where user_id=%s", (f"u{i}",))
            sleep(0.01)

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(worker, range(8)))

    pool = FakePool.instances[0]
    assert 1 <= pool.highwater <= 3
    assert len(pool.backend["committed"]) == 8
    assert sorted(row[1][0] for row in pool.backend["committed"]) == [f"u{i}" for i in range(8)]
    assert all(c.pending == [] for c in pool.idle)


def test_exception_rolls_back_and_next_checkout_has_no_prior_transaction(pooled):
    with pytest.raises(RuntimeError, match="intentional"):
        with pooled._connect() as conn, conn.cursor() as cur:
            cur.execute("insert fake", ("unsaved",))
            raise RuntimeError("intentional")
    pooled.append_user_perceived_latency(_latency("saved"))
    committed = FakePool.instances[0].backend["committed"]
    assert len(committed) == 1
    assert committed[0][1][0] == "saved"


def test_checkout_timeout_does_not_execute_sql(pooled):
    guards = [pooled._connect() for _ in range(3)]
    entered = []
    try:
        entered = [guard.__enter__() for guard in guards]
        with pytest.raises(TimeoutError, match="checkout timeout"):
            pooled.append_user_perceived_latency(_latency("never-written"))
    finally:
        for guard in reversed(guards[:len(entered)]):
            guard.__exit__(None, None, None)
    assert FakePool.instances[0].backend["committed"] == []


def test_stale_connection_checked_before_business_sql_and_replaced(pooled):
    pooled.append_user_perceived_latency(_latency("before"))
    pool = FakePool.instances[0]
    pool.idle[0].stale = True
    pooled.append_user_perceived_latency(_latency("after"))
    assert [params[0] for _, params in pool.backend["committed"]] == ["before", "after"]
    assert pool.idle[0].stale is False


def test_shutdown_closes_pool_and_new_store_represents_new_process(pooled):
    pooled.append_user_perceived_latency(_latency("first"))
    first = FakePool.instances[0]
    pooled.close()
    assert first.closed
    pooled.close()  # idempotent shutdown
    with pytest.raises(RuntimeError, match="closed"):
        pooled.append_user_perceived_latency(_latency("forbidden"))
    next_process = PostgresPersistenceStore("postgresql://unused")
    next_process.append_user_perceived_latency(_latency("second"))
    assert len(FakePool.instances) == 2
    assert FakePool.instances[1] is not first
    next_process.close()


def test_legacy_fallback_keeps_exact_statement_and_transaction_contract(monkeypatch, pooled):
    pooled.append_user_perceived_latency(_latency("same-user"))
    pooled_sql = FakePool.instances[0].backend["committed"][0]
    pooled.close()

    import psycopg
    legacy_backend = {"lock": Lock(), "committed": []}
    calls = []

    def fake_connect(dsn, **kwargs):
        calls.append((dsn, kwargs))
        return FakeConnection(legacy_backend)

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    monkeypatch.setenv("FSFFL_PERSISTENCE_CONNECTION_MODE", "legacy")
    legacy = PostgresPersistenceStore("postgresql://unused")
    legacy.append_user_perceived_latency(_latency("same-user"))
    assert len(calls) == 1
    assert len(FakePool.instances) == 1
    assert legacy_backend["committed"][0] == pooled_sql
    legacy.close()


def test_invalid_mode_rejected_without_database_activity(monkeypatch):
    monkeypatch.setenv("FSFFL_PERSISTENCE_CONNECTION_MODE", "transaction-pool")
    with pytest.raises(ValueError, match="pool or legacy"):
        PostgresPersistenceStore("postgresql://unused")
