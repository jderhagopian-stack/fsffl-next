from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Sequence

from .contracts import (
    ArtifactKey,
    LeagueSnapshotRecord,
    PersistenceStore,
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

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - deployment dependency guard
            raise RuntimeError("PostgreSQL persistence requires psycopg") from exc
        return psycopg.connect(self._database_url, row_factory=dict_row)

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
                     recorded_at=excluded.recorded_at""",
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
                     recorded_at=excluded.recorded_at""",
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
