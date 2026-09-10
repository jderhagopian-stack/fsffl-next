from __future__ import annotations

import json
from threading import Lock
from typing import Iterable

from .models import OwnerBehaviorEvent, OwnerBehaviorProfile


_RLS_BOOTSTRAP_LOCK = Lock()
_RLS_BOOTSTRAPPED_DATABASE_URLS: set[str] = set()


class PostgresBehavioralIntelligenceStore:
    """Durable hosted store for raw Behavioral evidence and derived profiles.

    This mirrors the narrow SQLite Behavioral store contract. It stores evidence
    and reusable profile outputs only; it performs no preference inference or other
    Behavioral calculations.

    The private beta initializes these additive cache tables idempotently so a web
    deploy cannot depend on an out-of-band migration step. The matching SQL migration
    remains the canonical production schema history.
    """

    def __init__(self, database_url: str) -> None:
        if not database_url.strip():
            raise ValueError("database_url cannot be blank")
        self._database_url = database_url
        self._initialize()

    def _connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - hosted dependency guard
            raise RuntimeError("PostgreSQL Behavioral persistence requires psycopg") from exc
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def _initialize(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("create schema if not exists fsffl")
            cursor.execute(
                """
                create table if not exists fsffl.behavior_event (
                    league_family_id text not null,
                    event_id text not null,
                    occurred_at timestamptz not null,
                    payload jsonb not null,
                    recorded_at timestamptz not null default now(),
                    primary key (league_family_id, event_id)
                )
                """
            )
            cursor.execute(
                """
                create index if not exists behavior_event_family_time_idx
                on fsffl.behavior_event (league_family_id, occurred_at, event_id)
                """
            )
            cursor.execute(
                """
                create table if not exists fsffl.behavior_profile (
                    league_family_id text not null,
                    owner_id text not null,
                    as_of timestamptz not null,
                    payload jsonb not null,
                    updated_at timestamptz not null default now(),
                    primary key (league_family_id, owner_id)
                )
                """
            )
            cursor.execute(
                """
                create table if not exists fsffl.behavior_season (
                    league_family_id text not null,
                    league_external_id text not null,
                    season integer not null,
                    complete boolean not null default false,
                    updated_at timestamptz not null default now(),
                    primary key (league_family_id, league_external_id)
                )
                """
            )
            cursor.execute(
                """
                create table if not exists fsffl.behavior_runtime_context (
                    user_id text primary key,
                    league_state_id text not null,
                    sleeper_league_external_id text not null,
                    league_family_id text not null,
                    current_owner_by_roster jsonb not null,
                    updated_at timestamptz not null default now()
                )
                """
            )
            # Hosted startup intentionally supports deploy-before-migration. Apply the
            # same deny-by-default RLS protection as migration _007, but only once per
            # database URL in this process. Failed bootstrap attempts are not cached,
            # so a later construction retries rather than silently assuming protection.
            with _RLS_BOOTSTRAP_LOCK:
                if self._database_url not in _RLS_BOOTSTRAPPED_DATABASE_URLS:
                    for table_name in (
                        "behavior_event",
                        "behavior_profile",
                        "behavior_season",
                        "behavior_runtime_context",
                    ):
                        cursor.execute(f"alter table fsffl.{table_name} enable row level security")
                    _RLS_BOOTSTRAPPED_DATABASE_URLS.add(self._database_url)

    def put_events(self, events: Iterable[OwnerBehaviorEvent]) -> int:
        inserted = 0
        with self._connect() as connection, connection.cursor() as cursor:
            for event in events:
                cursor.execute(
                    """
                    insert into fsffl.behavior_event
                    (league_family_id, event_id, occurred_at, payload)
                    values (%s,%s,%s,%s::jsonb)
                    on conflict (league_family_id, event_id) do nothing
                    returning event_id
                    """,
                    (
                        event.league_family_id,
                        event.event_id,
                        event.occurred_at,
                        event.model_dump_json(),
                    ),
                )
                if cursor.fetchone() is not None:
                    inserted += 1
        return inserted

    def load_events(self, league_family_id: str) -> tuple[OwnerBehaviorEvent, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select payload from fsffl.behavior_event
                where league_family_id=%s
                order by occurred_at, event_id
                """,
                (league_family_id,),
            )
            rows = cursor.fetchall()
        return tuple(OwnerBehaviorEvent.model_validate(row["payload"]) for row in rows)

    def put_profiles(self, profiles: Iterable[OwnerBehaviorProfile]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            for profile in profiles:
                cursor.execute(
                    """
                    insert into fsffl.behavior_profile
                    (league_family_id, owner_id, as_of, payload, updated_at)
                    values (%s,%s,%s,%s::jsonb,now())
                    on conflict (league_family_id, owner_id) do update set
                        as_of=excluded.as_of,
                        payload=excluded.payload,
                        updated_at=excluded.updated_at
                    """,
                    (
                        profile.league_family_id,
                        profile.owner_id,
                        profile.as_of,
                        profile.model_dump_json(),
                    ),
                )

    def load_profiles(self, league_family_id: str) -> tuple[OwnerBehaviorProfile, ...]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select payload from fsffl.behavior_profile
                where league_family_id=%s
                order by owner_id
                """,
                (league_family_id,),
            )
            rows = cursor.fetchall()
        return tuple(OwnerBehaviorProfile.model_validate(row["payload"]) for row in rows)

    def put_runtime_context(
        self,
        *,
        user_id: str,
        league_state_id: str,
        sleeper_league_external_id: str,
        league_family_id: str,
        current_owner_by_roster: Iterable[tuple[int, str]],
    ) -> None:
        owner_rows = [[int(roster_id), str(owner_id)] for roster_id, owner_id in current_owner_by_roster]
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into fsffl.behavior_runtime_context
                (user_id, league_state_id, sleeper_league_external_id, league_family_id,
                 current_owner_by_roster, updated_at)
                values (%s,%s,%s,%s,%s::jsonb,now())
                on conflict (user_id) do update set
                    league_state_id=excluded.league_state_id,
                    sleeper_league_external_id=excluded.sleeper_league_external_id,
                    league_family_id=excluded.league_family_id,
                    current_owner_by_roster=excluded.current_owner_by_roster,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    league_state_id,
                    sleeper_league_external_id,
                    league_family_id,
                    json.dumps(owner_rows, separators=(",", ":")),
                ),
            )

    def load_runtime_context(self, user_id: str) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select league_state_id, sleeper_league_external_id, league_family_id,
                       current_owner_by_roster
                from fsffl.behavior_runtime_context
                where user_id=%s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        owner_rows = row["current_owner_by_roster"]
        return {
            "league_state_id": str(row["league_state_id"]),
            "sleeper_league_external_id": str(row["sleeper_league_external_id"]),
            "league_family_id": str(row["league_family_id"]),
            "current_owner_by_roster": tuple((int(item[0]), str(item[1])) for item in owner_rows),
        }

    def mark_season_complete(self, league_family_id: str, league_external_id: str, season: int) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into fsffl.behavior_season
                (league_family_id, league_external_id, season, complete, updated_at)
                values (%s,%s,%s,true,now())
                on conflict (league_family_id, league_external_id) do update set
                    season=excluded.season,
                    complete=true,
                    updated_at=excluded.updated_at
                """,
                (league_family_id, league_external_id, season),
            )

    def season_is_complete(self, league_family_id: str, league_external_id: str) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select complete from fsffl.behavior_season
                where league_family_id=%s and league_external_id=%s
                """,
                (league_family_id, league_external_id),
            )
            row = cursor.fetchone()
        return bool(row and row["complete"])

    def complete_league_ids(self) -> frozenset[str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select league_external_id from fsffl.behavior_season where complete=true"
            )
            rows = cursor.fetchall()
        return frozenset(str(row["league_external_id"]) for row in rows)