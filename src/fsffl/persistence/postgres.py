from __future__ import annotations

import json
import logging
import os
from time import perf_counter
from datetime import datetime
from threading import Lock
from typing import Sequence

from fsffl.journey_telemetry import trace_persistence_read

from .contracts import (
    ArtifactKey,
    LeagueSnapshotRecord,
    PersistenceStore,
    MarketValueSnapshotRecord,
    ReusableArtifactMetadataRecord,
    ReusableArtifactReadBundle,
    ReusableArtifactRecord,
    SyncCursorRecord,
    TeamSnapshotRecord,
    UserPerceivedLatencyRecord,
    UserRuntimeContextRecord,
    utc_now,
)


class PostgresPersistenceStore(PersistenceStore):
    """Thin server-side PostgreSQL adapter for durable FSFFL runtime persistence.

    The adapter stores and retrieves already-authoritative state/artifacts. It performs
    no fantasy-football calculations and is intentionally provider-neutral SQL.
    """

    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise ValueError("database_url cannot be blank")
        self._database_url = database_url
        # Transport only. A store is shared by one hosted Uvicorn process; pool
        # checkouts never share a transaction between concurrent callers.
        mode = os.getenv("FSFFL_PERSISTENCE_CONNECTION_MODE", "pool").strip().lower()
        if mode not in {"pool", "legacy"}:
            raise ValueError("FSFFL_PERSISTENCE_CONNECTION_MODE must be pool or legacy")
        self._connection_mode = mode
        self._pool_lock = Lock()
        self._pool = None
        self._closed = False

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - deployment dependency guard
            raise RuntimeError("PostgreSQL persistence requires psycopg") from exc

        if self._connection_mode == "legacy":
            with self._pool_lock:
                if self._closed:
                    raise RuntimeError("PostgreSQL persistence store is closed")
            # Exact pre-Tranche-A single-connection behavior and rollback escape.
            return psycopg.connect(self._database_url, row_factory=dict_row)

        with self._pool_lock:
            if self._closed:
                raise RuntimeError("PostgreSQL persistence store is closed")
            if self._pool is None:
                try:
                    from psycopg_pool import ConnectionPool
                except ImportError as exc:
                    raise RuntimeError("Pooled PostgreSQL persistence requires psycopg-pool") from exc
                # Explicitly disable automatic server PREPARE so the same adapter
                # remains compatible with Supavisor session or transaction mode.
                # Every checkout is tested BEFORE any caller statement executes:
                # never retry a potentially committed write.
                pool = ConnectionPool(
                    self._database_url,
                    kwargs={"row_factory": dict_row, "prepare_threshold": None},
                    min_size=0,
                    max_size=3,
                    timeout=5.0,
                    max_waiting=12,
                    max_idle=75.0,
                    max_lifetime=720.0,
                    reconnect_timeout=5.0,
                    num_workers=1,
                    check=ConnectionPool.check_connection,
                    open=False,
                    name="fsffl-persistence",
                )
                pool.open(wait=False)
                self._pool = pool
                logging.getLogger("fsffl.product.persistence").info(
                    "FSFFL persistence pool opened min_idle=0 max_active=3 "
                    "checkout_timeout_seconds=5 max_idle_seconds=75 "
                    "max_lifetime_seconds=720"
                )
            pool = self._pool
        # pool.connection() has the same commit/rollback context semantics as
        # psycopg.Connection, but returns healthy connections to bounded reuse.
        return pool.connection()

    def close(self) -> None:
        """Close this process-owned pool during hosted application shutdown."""
        with self._pool_lock:
            self._closed = True
            pool = self._pool
            self._pool = None
        if pool is not None:
            pool.close(timeout=5.0)
            logging.getLogger("fsffl.product.persistence").info(
                "FSFFL persistence pool closed stats=%s", pool.get_stats()
            )

    @trace_persistence_read("get_user_runtime_context")
    def get_user_runtime_context(self, *, user_id: str) -> UserRuntimeContextRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select user_id, provider, league_external_id, league_id, season,
                          selected_team_id, state_hash, updated_at
                   from fsffl.user_runtime_context where user_id = %s""",
                (user_id,),
            )
            row = cursor.fetchone()
        return UserRuntimeContextRecord(**row) if row else None

    def put_user_runtime_context(self, record: UserRuntimeContextRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.user_runtime_context
                   (user_id, provider, league_external_id, league_id, season,
                    selected_team_id, state_hash, updated_at)
                   values (%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (user_id) do update set
                     provider=excluded.provider,
                     league_external_id=excluded.league_external_id,
                     league_id=excluded.league_id,
                     season=excluded.season,
                     selected_team_id=excluded.selected_team_id,
                     state_hash=excluded.state_hash,
                     updated_at=excluded.updated_at""",
                (
                    record.user_id,
                    record.provider,
                    record.league_external_id,
                    record.league_id,
                    record.season,
                    record.selected_team_id,
                    record.state_hash,
                    record.updated_at,
                ),
            )

    @trace_persistence_read("get_league_snapshot")
    def get_league_snapshot(self, *, provider: str, league_id: str, season: int) -> LeagueSnapshotRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select provider, league_id, season, state_hash, payload,
                          recorded_at, source_updated_at
                   from fsffl.league_snapshot
                   where provider=%s and league_id=%s and season=%s""",
                (provider, league_id, season),
            )
            row = cursor.fetchone()
        return LeagueSnapshotRecord(**row) if row else None

    def put_league_snapshot(self, record: LeagueSnapshotRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.league_snapshot
                   (provider, league_id, season, state_hash, payload, source_updated_at, recorded_at)
                   values (%s,%s,%s,%s,%s::jsonb,%s,%s)
                   on conflict (provider, league_id, season) do update set
                     state_hash=excluded.state_hash,
                     payload=excluded.payload,
                     source_updated_at=excluded.source_updated_at,
                     recorded_at=excluded.recorded_at
                   where
                     coalesce(excluded.source_updated_at, excluded.recorded_at)
                       > coalesce(fsffl.league_snapshot.source_updated_at, fsffl.league_snapshot.recorded_at)
                     or (
                       coalesce(excluded.source_updated_at, excluded.recorded_at)
                         = coalesce(fsffl.league_snapshot.source_updated_at, fsffl.league_snapshot.recorded_at)
                       and excluded.recorded_at >= fsffl.league_snapshot.recorded_at
                     )""",
                (
                    record.provider,
                    record.league_id,
                    record.season,
                    record.state_hash,
                    json.dumps(record.payload),
                    record.source_updated_at,
                    record.recorded_at,
                ),
            )

    @trace_persistence_read("get_team_snapshot")
    def get_team_snapshot(self, *, provider: str, league_id: str, team_id: str) -> TeamSnapshotRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select provider, league_id, team_id, state_hash, payload,
                          recorded_at, source_updated_at
                   from fsffl.team_snapshot
                   where provider=%s and league_id=%s and team_id=%s""",
                (provider, league_id, team_id),
            )
            row = cursor.fetchone()
        return TeamSnapshotRecord(**row) if row else None

    def put_team_snapshot(self, record: TeamSnapshotRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.team_snapshot
                   (provider, league_id, team_id, state_hash, payload, source_updated_at, recorded_at)
                   values (%s,%s,%s,%s,%s::jsonb,%s,%s)
                   on conflict (provider, league_id, team_id) do update set
                     state_hash=excluded.state_hash,
                     payload=excluded.payload,
                     source_updated_at=excluded.source_updated_at,
                     recorded_at=excluded.recorded_at
                   where
                     coalesce(excluded.source_updated_at, excluded.recorded_at)
                       > coalesce(fsffl.team_snapshot.source_updated_at, fsffl.team_snapshot.recorded_at)
                     or (
                       coalesce(excluded.source_updated_at, excluded.recorded_at)
                         = coalesce(fsffl.team_snapshot.source_updated_at, fsffl.team_snapshot.recorded_at)
                       and excluded.recorded_at >= fsffl.team_snapshot.recorded_at
                     )""",
                (
                    record.provider,
                    record.league_id,
                    record.team_id,
                    record.state_hash,
                    json.dumps(record.payload),
                    record.source_updated_at,
                    record.recorded_at,
                ),
            )

    @trace_persistence_read("get_sync_cursor")
    def get_sync_cursor(self, *, provider: str, scope_kind: str, scope_id: str) -> SyncCursorRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select provider, scope_kind, scope_id, cursor_payload,
                          synced_at, source_updated_at
                   from fsffl.sync_cursor
                   where provider=%s and scope_kind=%s and scope_id=%s""",
                (provider, scope_kind, scope_id),
            )
            row = cursor.fetchone()
        return SyncCursorRecord(**row) if row else None

    def put_sync_cursor(self, record: SyncCursorRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.sync_cursor
                   (provider, scope_kind, scope_id, cursor_payload, source_updated_at, synced_at)
                   values (%s,%s,%s,%s::jsonb,%s,%s)
                   on conflict (provider, scope_kind, scope_id) do update set
                     cursor_payload=excluded.cursor_payload,
                     source_updated_at=excluded.source_updated_at,
                     synced_at=excluded.synced_at""",
                (
                    record.provider,
                    record.scope_kind,
                    record.scope_id,
                    json.dumps(record.cursor_payload),
                    record.source_updated_at,
                    record.synced_at,
                ),
            )

    @staticmethod
    def _artifact_from_row(row) -> ReusableArtifactRecord:
        return ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind=row["artifact_kind"],
                scope_kind=row["scope_kind"],
                scope_id=row["scope_id"],
                input_fingerprint=row["input_fingerprint"],
                model_version=row["model_version"],
            ),
            payload=row["payload"],
            computed_at=row["computed_at"],
            invalidated_at=row["invalidated_at"],
            invalidation_reason=row["invalidation_reason"],
        )

    @staticmethod
    def _artifact_metadata_from_row(row) -> ReusableArtifactMetadataRecord:
        return ReusableArtifactMetadataRecord(
            key=ArtifactKey(
                artifact_kind=row["artifact_kind"],
                scope_kind=row["scope_kind"],
                scope_id=row["scope_id"],
                input_fingerprint=row["input_fingerprint"],
                model_version=row["model_version"],
            ),
            computed_at=row["computed_at"],
            invalidated_at=row["invalidated_at"],
            invalidation_reason=row["invalidation_reason"],
        )

    @trace_persistence_read("get_reusable_artifact_metadata")
    def get_reusable_artifact_metadata(
        self, key: ArtifactKey
    ) -> ReusableArtifactMetadataRecord | None:
        """Read artifact identity/freshness without fetching its JSONB payload."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select artifact_kind, scope_kind, scope_id, input_fingerprint,
                          model_version, computed_at, invalidated_at, invalidation_reason
                   from fsffl.derived_artifact
                   where artifact_kind=%s and scope_kind=%s and scope_id=%s
                     and input_fingerprint=%s and model_version=%s and invalidated_at is null""",
                (key.artifact_kind, key.scope_kind, key.scope_id, key.input_fingerprint, key.model_version),
            )
            row = cursor.fetchone()
        return self._artifact_metadata_from_row(row) if row else None

    @trace_persistence_read("get_reusable_artifact_read_bundle")
    def get_reusable_artifact_read_bundle(
        self,
        *,
        manifest_key: ArtifactKey,
        metadata_keys: Sequence[ArtifactKey],
        payload_key: ArtifactKey | None,
    ) -> ReusableArtifactReadBundle:
        """Read publication authority and sibling identities from one SQL snapshot.

        Payload JSON is returned for the small manifest and, when requested, one
        surface. Readiness-only consumers pass no payload key, avoiding unnecessary
        surface JSON transfer while keeping completeness in the same statement view.
        """
        payload_keys = {manifest_key}
        if payload_key is not None:
            payload_keys.add(payload_key)
        requested_keys = tuple(
            dict.fromkeys(
                (manifest_key, *metadata_keys, *((payload_key,) if payload_key else ()))
            )
        )
        requested: dict[ArtifactKey, bool] = {
            key: key in payload_keys for key in requested_keys
        }
        values = tuple(
            value
            for key, include_payload in requested.items()
            for value in (
                key.artifact_kind,
                key.scope_kind,
                key.scope_id,
                key.input_fingerprint,
                key.model_version,
                include_payload,
            )
        )
        rows_sql = ",".join(["(%s,%s,%s,%s,%s,%s)"] * len(requested))
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""with requested(artifact_kind, scope_kind, scope_id,
                                   input_fingerprint, model_version, include_payload)
                     as (values {rows_sql})
                     select artifact.artifact_kind, artifact.scope_kind,
                            artifact.scope_id, artifact.input_fingerprint,
                            artifact.model_version,
                            case when requested.include_payload
                                 then artifact.payload else null end as payload,
                            artifact.computed_at, artifact.invalidated_at,
                            artifact.invalidation_reason
                     from requested
                     join fsffl.derived_artifact as artifact
                       using (artifact_kind, scope_kind, scope_id,
                              input_fingerprint, model_version)
                     where artifact.invalidated_at is null""",
                values,
            )
            rows = cursor.fetchall()

        manifest = None
        requested_payload = None
        metadata = {}
        for row in rows:
            key = ArtifactKey(
                artifact_kind=row["artifact_kind"],
                scope_kind=row["scope_kind"],
                scope_id=row["scope_id"],
                input_fingerprint=row["input_fingerprint"],
                model_version=row["model_version"],
            )
            metadata[key] = self._artifact_metadata_from_row(row)
            if key == manifest_key:
                manifest = self._artifact_from_row(row)
            if key == payload_key:
                requested_payload = self._artifact_from_row(row)
        return ReusableArtifactReadBundle(
            manifest=manifest,
            requested_payload=requested_payload,
            metadata=metadata,
        )

    @trace_persistence_read("get_latest_reusable_artifact_metadata")
    def get_latest_reusable_artifact_metadata(
        self,
        *,
        artifact_kind: str,
        scope_kind: str,
        scope_id: str,
        model_version: str,
    ) -> ReusableArtifactMetadataRecord | None:
        """Read latest reusable artifact identity/freshness without its payload."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select artifact_kind, scope_kind, scope_id, input_fingerprint,
                          model_version, computed_at, invalidated_at, invalidation_reason
                   from fsffl.derived_artifact
                   where artifact_kind=%s and scope_kind=%s and scope_id=%s
                     and model_version=%s and invalidated_at is null
                   order by computed_at desc limit 1""",
                (artifact_kind, scope_kind, scope_id, model_version),
            )
            row = cursor.fetchone()
        return self._artifact_metadata_from_row(row) if row else None

    @trace_persistence_read("get_reusable_artifact")
    def get_reusable_artifact(self, key: ArtifactKey) -> ReusableArtifactRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select artifact_kind, scope_kind, scope_id, input_fingerprint,
                          model_version, payload, computed_at, invalidated_at, invalidation_reason
                   from fsffl.derived_artifact
                   where artifact_kind=%s and scope_kind=%s and scope_id=%s
                     and input_fingerprint=%s and model_version=%s and invalidated_at is null""",
                (key.artifact_kind, key.scope_kind, key.scope_id, key.input_fingerprint, key.model_version),
            )
            row = cursor.fetchone()
        return self._artifact_from_row(row) if row else None

    @trace_persistence_read("get_latest_reusable_artifact")
    def get_latest_reusable_artifact(
        self,
        *,
        artifact_kind: str,
        scope_kind: str,
        scope_id: str,
        model_version: str,
    ) -> ReusableArtifactRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select artifact_kind, scope_kind, scope_id, input_fingerprint,
                          model_version, payload, computed_at, invalidated_at, invalidation_reason
                   from fsffl.derived_artifact
                   where artifact_kind=%s and scope_kind=%s and scope_id=%s
                     and model_version=%s and invalidated_at is null
                   order by computed_at desc limit 1""",
                (artifact_kind, scope_kind, scope_id, model_version),
            )
            row = cursor.fetchone()
        return self._artifact_from_row(row) if row else None

    def put_artifact(self, record: ReusableArtifactRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.derived_artifact
                   (artifact_kind, scope_kind, scope_id, input_fingerprint, model_version,
                    payload, computed_at, invalidated_at, invalidation_reason)
                   values (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                   on conflict (artifact_kind, scope_kind, scope_id, input_fingerprint, model_version)
                   do update set payload=excluded.payload, computed_at=excluded.computed_at,
                     invalidated_at=excluded.invalidated_at,
                     invalidation_reason=excluded.invalidation_reason""",
                (
                    record.key.artifact_kind,
                    record.key.scope_kind,
                    record.key.scope_id,
                    record.key.input_fingerprint,
                    record.key.model_version,
                    json.dumps(record.payload),
                    record.computed_at,
                    record.invalidated_at,
                    record.invalidation_reason,
                ),
            )

    def invalidate_scope(
        self,
        *,
        scope_kind: str,
        scope_id: str,
        cause_kind: str,
        cause_ref: str | None,
        artifact_kinds: Sequence[str],
        observed_at: datetime | None = None,
    ) -> None:
        if not artifact_kinds:
            return
        timestamp = observed_at or utc_now()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """update fsffl.derived_artifact set invalidated_at=%s, invalidation_reason=%s
                   where scope_kind=%s and scope_id=%s and artifact_kind = any(%s)
                     and invalidated_at is null""",
                (timestamp, cause_kind, scope_kind, scope_id, list(artifact_kinds)),
            )
            cursor.execute(
                """insert into fsffl.invalidation_event
                   (scope_kind, scope_id, cause_kind, cause_ref, invalidated_artifact_kinds, observed_at)
                   values (%s,%s,%s,%s,%s,%s)""",
                (scope_kind, scope_id, cause_kind, cause_ref, list(artifact_kinds), timestamp),
            )

    def append_market_value_snapshot(
        self,
        *,
        asset_ref: str,
        asset_kind: str,
        scale_id: str,
        market_context_id: str,
        estimate_as_of: datetime,
        value: float,
        source_lineage,
        recorded_at: datetime | None = None,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.market_value_snapshot
                   (asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of,
                    recorded_at, value, source_lineage)
                   values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                   on conflict (asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of)
                   do nothing""",
                (
                    asset_ref,
                    asset_kind,
                    scale_id,
                    market_context_id,
                    estimate_as_of,
                    recorded_at or utc_now(),
                    value,
                    json.dumps(source_lineage),
                ),
            )

    def append_market_value_snapshots(
        self, records: Sequence[MarketValueSnapshotRecord]
    ) -> None:
        """Append bounded multirow SQL with original first-writer conflict policy.

        One committed transaction per <=300-row chunk. Earlier chunks remain
        durable if a later chunk fails, matching the legacy forward-progress
        behavior; the failing chunk rolls back atomically. No write is retried.
        """
        if not records:
            return
        chunk_size = 300
        row_template = "(%s,%s,%s,%s,%s,%s,%s,%s::jsonb)"
        sql_prefix = (
            "insert into fsffl.market_value_snapshot "
            "(asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of, "
            "recorded_at, value, source_lineage) values "
        )
        conflict_clause = (
            " on conflict "
            "(asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of) "
            "do nothing"
        )
        logger = logging.getLogger("fsffl.product.persistence")
        for start in range(0, len(records), chunk_size):
            chunk = records[start : start + chunk_size]
            # Collapse repeated conflict coordinates within this statement,
            # keeping ONLY the earliest observation, including its original
            # recorded_at and lineage. Earlier committed chunks/database rows
            # still win under ON CONFLICT DO NOTHING.
            unique: list[MarketValueSnapshotRecord] = []
            seen: set[tuple[str, str, str, str, datetime]] = set()
            for row in chunk:
                key = (
                    row.asset_ref, row.asset_kind, row.scale_id,
                    row.market_context_id, row.estimate_as_of,
                )
                if key not in seen:
                    seen.add(key)
                    unique.append(row)
            params: list[object] = []
            for row in unique:
                params.extend((
                    row.asset_ref, row.asset_kind, row.scale_id,
                    row.market_context_id, row.estimate_as_of,
                    row.recorded_at, row.value, json.dumps(row.source_lineage),
                ))
            sql = sql_prefix + ",".join([row_template] * len(unique)) + conflict_clause
            t0 = perf_counter()
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(sql, tuple(params))
            # This log is emitted AFTER commit, never as proof for an
            # uncommitted transaction. SQL and pool counters are not conflated.
            logger.info(
                "FSFFL market snapshot batch committed input_rows=%d "
                "statement_rows=%d chunk_index=%d elapsed_ms=%.2f",
                len(chunk), len(unique), start // chunk_size, (perf_counter() - t0) * 1000,
            )

    def append_user_perceived_latency(self, record: UserPerceivedLatencyRecord) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.user_perceived_latency
                   (user_id, operation, elapsed_ms, outcome, detail, observed_at)
                   values (%s,%s,%s,%s,%s,%s)""",
                (
                    record.user_id,
                    record.operation,
                    record.elapsed_ms,
                    record.outcome,
                    record.detail,
                    record.observed_at,
                ),
            )


def persistence_store_from_env() -> PostgresPersistenceStore | None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return PostgresPersistenceStore(database_url)
