from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fsffl.state.history import StateSnapshotStore
from fsffl.state.models import LeagueState


ConnectFactory = Callable[[], Any]


class PostgresStateSnapshotStore(StateSnapshotStore):
    """Durable adapter for canonical point-in-time State snapshots.

    The store validates canonical ``LeagueState`` payloads on both write and read.
    It never reconstructs State or performs fantasy-football inference; State remains
    authoritative and persistence only retains exact snapshots for later retrieval.
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
            raise RuntimeError("PostgreSQL State history requires psycopg") from exc
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def save(self, state: LeagueState) -> None:
        payload = state.model_dump(mode="json")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.state_snapshot_history
                   (league_id, state_hash, season, as_of, payload)
                   values (%s,%s,%s,%s,%s::jsonb)
                   on conflict (league_id, state_hash) do nothing""",
                (
                    state.league.league_id,
                    state.state_id,
                    state.league.season,
                    state.as_of,
                    json.dumps(payload),
                ),
            )
            cursor.execute(
                """select state_hash, payload from fsffl.state_snapshot_history
                   where league_id=%s and state_hash=%s""",
                (state.league.league_id, state.state_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("State history snapshot write did not persist")
        stored = LeagueState.model_validate(row["payload"])
        if row["state_hash"] != state.state_id or stored != state:
            raise ValueError("State history identity is immutable once persisted")

    def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select state_hash, payload from fsffl.state_snapshot_history
                   where league_id=%s and as_of <= %s
                   order by as_of desc, recorded_at desc
                   limit 1""",
                (league_id, as_of),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        state = LeagueState.model_validate(row["payload"])
        if state.league.league_id != league_id:
            raise ValueError("stored State history league identity does not match query")
        if state.state_id != row["state_hash"]:
            raise ValueError("stored State history hash does not match canonical payload")
        if state.as_of > as_of:
            raise ValueError("stored State history snapshot postdates query cutoff")
        return state


def state_snapshot_store_from_env() -> PostgresStateSnapshotStore | None:
    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        return None
    return PostgresStateSnapshotStore(database_url)
