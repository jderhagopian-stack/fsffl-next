from __future__ import annotations

from contextlib import contextmanager

import pytest

from fsffl.behavioral.postgres_store import PostgresBehavioralIntelligenceStore


DDL_TOKENS = ("create ", "alter ", "drop ", "truncate ", "reindex ")


class _Cursor:
    def __init__(self, *, missing: str | None = None, rls_disabled: str | None = None, index_present: bool = True):
        self.missing = missing
        self.rls_disabled = rls_disabled
        self.index_present = index_present
        self.statements: list[str] = []
        self._query_number = 0

    def execute(self, sql: str, params=None) -> None:
        self.statements.append(" ".join(sql.lower().split()))
        self._query_number += 1

    def fetchall(self):
        names = (
            "behavior_event",
            "behavior_profile",
            "behavior_season",
            "behavior_runtime_context",
        )
        return [
            {"relname": name, "relrowsecurity": name != self.rls_disabled}
            for name in names
            if name != self.missing
        ]

    def fetchone(self):
        return {"relation": "fsffl.behavior_event_family_time_idx" if self.index_present else None}


class _Connection:
    def __init__(self, cursor: _Cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    @contextmanager
    def cursor(self):
        yield self._cursor


def _store_with_cursor(monkeypatch, cursor: _Cursor) -> PostgresBehavioralIntelligenceStore:
    monkeypatch.setattr(
        PostgresBehavioralIntelligenceStore,
        "_connect",
        lambda _self: _Connection(cursor),
    )
    return PostgresBehavioralIntelligenceStore("postgresql://stage1-test")


def test_repeated_runtime_initialization_executes_zero_ddl(monkeypatch) -> None:
    cursor = _Cursor()

    _store_with_cursor(monkeypatch, cursor)
    _store_with_cursor(monkeypatch, cursor)

    assert len(cursor.statements) == 4
    assert all(not statement.startswith(DDL_TOKENS) for statement in cursor.statements)
    assert all("create " not in statement for statement in cursor.statements)
    assert all("alter " not in statement for statement in cursor.statements)
    assert all("drop " not in statement for statement in cursor.statements)


@pytest.mark.parametrize(
    ("cursor", "expected"),
    [
        (_Cursor(missing="behavior_profile"), "missing=behavior_profile"),
        (_Cursor(rls_disabled="behavior_event"), "rls_disabled=behavior_event"),
        (_Cursor(index_present=False), "missing=behavior_event_family_time_idx"),
    ],
)
def test_runtime_schema_validation_fails_closed(monkeypatch, cursor: _Cursor, expected: str) -> None:
    with pytest.raises(RuntimeError, match=expected):
        _store_with_cursor(monkeypatch, cursor)

    assert all("create " not in statement for statement in cursor.statements)
    assert all("alter " not in statement for statement in cursor.statements)
