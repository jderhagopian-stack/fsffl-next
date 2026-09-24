from __future__ import annotations

import json
from typing import Iterable

from .models import OwnerBehaviorEvent, OwnerBehaviorProfile



class PostgresBehavioralIntelligenceStore:
    """Durable hosted store for raw Behavioral evidence and derived profiles.

    This mirrors the narrow SQLite Behavioral store contract. It stores evidence
    and reusable profile outputs only; it performs no preference inference or other
    Behavioral calculations.

    Governed migrations own schema/index/RLS creation. Runtime construction performs
    read-only schema validation and fails closed when required persistence is missing
    or unsafe; ordinary application use never executes DDL.
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
        """Validate the migrated Behavioral schema without mutating it.

        Schema, indexes, and RLS are migration authority. Keeping this check read-only
        makes startup safe to repeat and prevents request/store construction from
        performing CREATE/ALTER work.
        """
        required_relations = (
            "behavior_event",
            "behavior_profile",
            "behavior_season",
            "behavior_runtime_context",
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select c.relname, c.relrowsecurity
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'fsffl' and c.relname = any(%s)
                """,
                (list(required_relations),),
            )
            rows = cursor.fetchall()
            by_name = {str(row["relname"]): bool(row["relrowsecurity"]) for row in rows}
            missing = [name for name in required_relations if name not in by_name]
            unsafe = [name for name in required_relations if name in by_name and not by_name[name]]
            if missing or unsafe:
                details = []
                if missing:
                    details.append("missing=" + ",".join(missing))
                if unsafe:
                    details.append("rls_disabled=" + ",".join(unsafe))
                raise RuntimeError(
                    "Behavioral persistence schema is unavailable or incompatible; "
                    "apply governed migrations before serving traffic (" + "; ".join(details) + ")"
                )

            cursor.execute(
                """
                select to_regclass('fsffl.behavior_event_family_time_idx') as relation
                """
            )
            index_row = cursor.fetchone()
            if index_row is None or index_row["relation"] is None:
                raise RuntimeError(
                    "Behavioral persistence index is unavailable; apply governed migrations "
                    "before serving traffic (missing=behavior_event_family_time_idx)"
                )

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