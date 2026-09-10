from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from typing import Any

from .historical_persistence import (
    HistoricalArtifactIdentity,
    HistoricalArtifactKind,
    HistoricalInvalidationRequest,
    HistoricalSyncCheckpoint,
    _parse_dependency_fingerprint,
)
from .historical_trade import HistoricalTradeReport


ConnectFactory = Callable[[], Any]


def _identity_key(identity: HistoricalArtifactIdentity) -> str:
    payload = identity.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class PostgresHistoricalPersistence:
    """Durable implementation of the existing historical persistence contracts.

    Storage remains infrastructure only: reports and identities are validated by the
    existing Analytics domain models before write/read, and dependency invalidation
    only removes derived historical artifacts that explicitly declare the old version.
    """

    def __init__(self, database_url: str, *, connect_factory: ConnectFactory | None = None) -> None:
        if not database_url.strip():
            raise ValueError("database_url cannot be blank")
        self._database_url = database_url
        self._connect_factory = connect_factory

    def _connect(self):
        if self._connect_factory is not None:
            return self._connect_factory()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - deployment dependency guard
            raise RuntimeError("PostgreSQL historical persistence requires psycopg") from exc
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def get(self, identity: HistoricalArtifactIdentity) -> HistoricalTradeReport | None:
        key = _identity_key(identity)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select identity_payload, report_payload
                   from fsffl.historical_artifact where artifact_key=%s""",
                (key,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        stored_identity = HistoricalArtifactIdentity.model_validate(row["identity_payload"])
        if stored_identity != identity:
            raise ValueError("historical artifact key resolved to a different identity")
        report = HistoricalTradeReport.model_validate(row["report_payload"])
        if report.transaction_id != identity.transaction_id:
            raise ValueError("stored historical report transaction_id does not match identity")
        return report

    def put(self, identity: HistoricalArtifactIdentity, report: HistoricalTradeReport) -> None:
        if identity.transaction_id != report.transaction_id:
            raise ValueError("historical report transaction_id must match artifact identity")
        key = _identity_key(identity)
        identity_payload = identity.model_dump(mode="json")
        report_payload = report.model_dump(mode="json")
        dependencies = (
            _parse_dependency_fingerprint(identity.dependency_fingerprint)
            if identity.dependency_fingerprint is not None
            else {}
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.historical_artifact
                   (artifact_key, league_id, transaction_id, artifact_kind, artifact_version,
                    as_of, dependency_fingerprint, identity_payload, report_payload)
                   values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
                   on conflict (artifact_key) do nothing""",
                (
                    key,
                    identity.league_id,
                    identity.transaction_id,
                    identity.artifact_kind.value,
                    identity.artifact_version,
                    identity.as_of,
                    identity.dependency_fingerprint,
                    json.dumps(identity_payload),
                    json.dumps(report_payload),
                ),
            )
            cursor.execute(
                """select identity_payload, report_payload
                   from fsffl.historical_artifact where artifact_key=%s""",
                (key,),
            )
            existing = cursor.fetchone()
            if existing is None:
                raise RuntimeError("historical artifact write did not persist")
            existing_identity = HistoricalArtifactIdentity.model_validate(existing["identity_payload"])
            existing_report = HistoricalTradeReport.model_validate(existing["report_payload"])
            if existing_identity != identity or existing_report != report:
                raise ValueError("historical artifact identity is immutable once persisted")
            for component, version in dependencies.items():
                cursor.execute(
                    """insert into fsffl.historical_artifact_dependency
                       (artifact_key, component, version)
                       values (%s,%s,%s)
                       on conflict (artifact_key, component) do update set version=excluded.version""",
                    (key, component, version),
                )

    def invalidate(self, request: HistoricalInvalidationRequest) -> tuple[HistoricalArtifactIdentity, ...]:
        derived = tuple(kind.value for kind in (
            HistoricalArtifactKind.POINT_IN_TIME_ANALYSIS,
            HistoricalArtifactKind.RETROSPECTIVE_ANALYSIS,
            HistoricalArtifactKind.ASSET_LINEAGE,
            HistoricalArtifactKind.FINAL_REPORT,
        ))
        params: list[object] = [
            request.league_id,
            request.dependency_component,
            request.old_version,
            list(derived),
        ]
        transaction_filter = ""
        if request.affected_transaction_ids:
            transaction_filter = " and a.transaction_id = any(%s)"
            params.append(list(request.affected_transaction_ids))
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select a.artifact_key, a.identity_payload
                   from fsffl.historical_artifact a
                   join fsffl.historical_artifact_dependency d
                     on d.artifact_key=a.artifact_key
                   where a.league_id=%s and d.component=%s and d.version=%s
                     and a.artifact_kind = any(%s)""" + transaction_filter,
                tuple(params),
            )
            rows = cursor.fetchall()
            keys = [row["artifact_key"] for row in rows]
            if keys:
                cursor.execute(
                    "delete from fsffl.historical_artifact where artifact_key = any(%s)",
                    (keys,),
                )
        identities = [HistoricalArtifactIdentity.model_validate(row["identity_payload"]) for row in rows]
        return tuple(sorted(identities, key=lambda item: (item.transaction_id, item.artifact_kind.value, item.artifact_version)))

    def get_checkpoint(self, league_id: str, provider: str) -> HistoricalSyncCheckpoint | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select league_id, provider, last_completed_at, provider_cursor, model_version
                   from fsffl.historical_sync_checkpoint
                   where league_id=%s and provider=%s""",
                (league_id, provider),
            )
            row = cursor.fetchone()
        return HistoricalSyncCheckpoint.model_validate(row) if row else None

    def put_checkpoint(self, checkpoint: HistoricalSyncCheckpoint) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select last_completed_at from fsffl.historical_sync_checkpoint
                   where league_id=%s and provider=%s for update""",
                (checkpoint.league_id, checkpoint.provider),
            )
            previous = cursor.fetchone()
            if previous is not None and checkpoint.last_completed_at < previous["last_completed_at"]:
                raise ValueError("sync checkpoints cannot move backward")
            cursor.execute(
                """insert into fsffl.historical_sync_checkpoint
                   (league_id, provider, last_completed_at, provider_cursor, model_version)
                   values (%s,%s,%s,%s,%s)
                   on conflict (league_id, provider) do update set
                     last_completed_at=excluded.last_completed_at,
                     provider_cursor=excluded.provider_cursor,
                     model_version=excluded.model_version,
                     updated_at=now()""",
                (
                    checkpoint.league_id,
                    checkpoint.provider,
                    checkpoint.last_completed_at,
                    checkpoint.provider_cursor,
                    checkpoint.model_version,
                ),
            )


class PostgresHistoricalReportRepository:
    def __init__(self, persistence: PostgresHistoricalPersistence) -> None:
        self._persistence = persistence

    def get(self, identity: HistoricalArtifactIdentity) -> HistoricalTradeReport | None:
        return self._persistence.get(identity)

    def put(self, identity: HistoricalArtifactIdentity, report: HistoricalTradeReport) -> None:
        self._persistence.put(identity, report)

    def invalidate(self, request: HistoricalInvalidationRequest) -> tuple[HistoricalArtifactIdentity, ...]:
        return self._persistence.invalidate(request)


class PostgresHistoricalSyncCheckpointRepository:
    def __init__(self, persistence: PostgresHistoricalPersistence) -> None:
        self._persistence = persistence

    def get(self, league_id: str, provider: str) -> HistoricalSyncCheckpoint | None:
        return self._persistence.get_checkpoint(league_id, provider)

    def put(self, checkpoint: HistoricalSyncCheckpoint) -> None:
        self._persistence.put_checkpoint(checkpoint)


def historical_postgres_repositories_from_env() -> tuple[
    PostgresHistoricalReportRepository,
    PostgresHistoricalSyncCheckpointRepository,
] | None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        return None
    persistence = PostgresHistoricalPersistence(database_url)
    return (
        PostgresHistoricalReportRepository(persistence),
        PostgresHistoricalSyncCheckpointRepository(persistence),
    )
