from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from fsffl.analytics.historical_persistence import (
    HistoricalArtifactIdentity,
    HistoricalArtifactKind,
    HistoricalInvalidationRequest,
    HistoricalSyncCheckpoint,
)
from fsffl.analytics.historical_postgres import PostgresHistoricalPersistence
from fsffl.analytics.historical_trade import (
    EvidenceCompleteness,
    GradeResult,
    GradeStatus,
    HistoricalTradeReport,
    RetrospectiveOutcomeComponents,
)


NOW = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)


class FakeDatabase:
    def __init__(self) -> None:
        self.artifacts: dict[str, dict[str, object]] = {}
        self.dependencies: dict[str, dict[str, str]] = {}
        self.checkpoints: dict[tuple[str, str], dict[str, object]] = {}

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
        self.rows: list[dict[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: str, params=()) -> None:
        normalized = " ".join(sql.split())
        self.rows = []
        if normalized.startswith("insert into fsffl.historical_artifact "):
            key = params[0]
            self.database.artifacts.setdefault(
                key,
                {
                    "artifact_key": key,
                    "league_id": params[1],
                    "transaction_id": params[2],
                    "artifact_kind": params[3],
                    "artifact_version": params[4],
                    "as_of": params[5],
                    "dependency_fingerprint": params[6],
                    "identity_payload": json.loads(params[7]),
                    "report_payload": json.loads(params[8]),
                },
            )
            return
        if normalized.startswith("select identity_payload, report_payload from fsffl.historical_artifact"):
            row = self.database.artifacts.get(params[0])
            if row:
                self.rows = [{"identity_payload": row["identity_payload"], "report_payload": row["report_payload"]}]
            return
        if normalized.startswith("insert into fsffl.historical_artifact_dependency"):
            self.database.dependencies.setdefault(params[0], {})[params[1]] = params[2]
            return
        if normalized.startswith("select a.artifact_key, a.identity_payload from fsffl.historical_artifact"):
            league_id, component, version, derived = params[:4]
            allowed_transactions = set(params[4]) if len(params) == 5 else None
            for key, row in self.database.artifacts.items():
                if row["league_id"] != league_id or row["artifact_kind"] not in set(derived):
                    continue
                if allowed_transactions is not None and row["transaction_id"] not in allowed_transactions:
                    continue
                if self.database.dependencies.get(key, {}).get(component) == version:
                    self.rows.append({"artifact_key": key, "identity_payload": row["identity_payload"]})
            return
        if normalized.startswith("delete from fsffl.historical_artifact"):
            for key in params[0]:
                self.database.artifacts.pop(key, None)
                self.database.dependencies.pop(key, None)
            return
        if normalized.startswith("select league_id, provider, last_completed_at"):
            row = self.database.checkpoints.get((params[0], params[1]))
            if row:
                self.rows = [dict(row)]
            return
        if normalized.startswith("select last_completed_at from fsffl.historical_sync_checkpoint"):
            row = self.database.checkpoints.get((params[0], params[1]))
            if row:
                self.rows = [{"last_completed_at": row["last_completed_at"]}]
            return
        if normalized.startswith("insert into fsffl.historical_sync_checkpoint"):
            self.database.checkpoints[(params[0], params[1])] = {
                "league_id": params[0],
                "provider": params[1],
                "last_completed_at": params[2],
                "provider_cursor": params[3],
                "model_version": params[4],
            }
            return
        raise AssertionError(f"unexpected SQL: {normalized}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


def _report(*, lesson: str = "Keep the evidence.") -> HistoricalTradeReport:
    not_graded = GradeResult(
        status=GradeStatus.NOT_GRADED,
        confidence=0.0,
        reason="Test fixture has no governed score.",
    )
    return HistoricalTradeReport(
        transaction_id="tx-1",
        trade_date=NOW,
        teams=("a", "b"),
        assets_by_team={"a": ("p1",), "b": ("p2",)},
        point_in_time_grade=not_graded,
        point_in_time_evidence=(),
        final_outcome_grade=not_graded,
        outcome_components=RetrospectiveOutcomeComponents(
            evidence=EvidenceCompleteness(required_items=(), available_items=()),
        ),
        lessons=(lesson,),
    )


def _identity(*, artifact_version: str, decision_version: str) -> HistoricalArtifactIdentity:
    return HistoricalArtifactIdentity(
        league_id="sleeper:123",
        transaction_id="tx-1",
        artifact_kind=HistoricalArtifactKind.FINAL_REPORT,
        artifact_version=artifact_version,
        as_of=NOW,
        dependency_fingerprint=f"decision={decision_version}|pick_coordinate=v3",
    )


def _store(database: FakeDatabase) -> PostgresHistoricalPersistence:
    return PostgresHistoricalPersistence("postgresql://test", connect_factory=database.connect)


def test_historical_report_round_trips_under_exact_immutable_identity() -> None:
    database = FakeDatabase()
    store = _store(database)
    identity = _identity(artifact_version="report-v1", decision_version="v5")
    report = _report()

    store.put(identity, report)

    assert store.get(identity) == report
    assert next(iter(database.dependencies.values())) == {"decision": "v5", "pick_coordinate": "v3"}

    with pytest.raises(ValueError, match="immutable"):
        store.put(identity, _report(lesson="Conflicting rewrite."))


def test_dependency_invalidation_removes_only_matching_derived_version() -> None:
    database = FakeDatabase()
    store = _store(database)
    old = _identity(artifact_version="report-v1", decision_version="v5")
    current = _identity(artifact_version="report-v2", decision_version="v6")
    store.put(old, _report())
    store.put(current, _report())

    removed = store.invalidate(
        HistoricalInvalidationRequest(
            league_id="sleeper:123",
            dependency_component="decision",
            old_version="v5",
            new_version="v6",
        )
    )

    assert removed == (old,)
    assert store.get(old) is None
    assert store.get(current) == _report()


def test_historical_sync_checkpoint_survives_restart_and_never_moves_backward() -> None:
    database = FakeDatabase()
    first = _store(database)
    checkpoint = HistoricalSyncCheckpoint(
        league_id="sleeper:123",
        provider="sleeper",
        last_completed_at=NOW,
        provider_cursor="cursor-7",
    )
    first.put_checkpoint(checkpoint)

    restarted = _store(database)
    assert restarted.get_checkpoint("sleeper:123", "sleeper") == checkpoint

    with pytest.raises(ValueError, match="cannot move backward"):
        restarted.put_checkpoint(
            HistoricalSyncCheckpoint(
                league_id="sleeper:123",
                provider="sleeper",
                last_completed_at=NOW - timedelta(minutes=1),
                provider_cursor="cursor-6",
            )
        )
