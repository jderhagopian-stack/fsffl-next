from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .models import OwnerBehaviorEvent, OwnerBehaviorProfile


class BehavioralIntelligenceStore:
    """Small durable cache for raw behavioral evidence and derived profiles.

    SQLite is the initial local/private-beta implementation. The interface is
    deliberately narrow so a hosted database can replace it without changing
    Behavioral Intelligence or downstream Decision/Search contracts.
    """

    schema_version = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS behavior_events (
                    league_family_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (league_family_id, event_id)
                );
                CREATE INDEX IF NOT EXISTS behavior_events_owner_time
                    ON behavior_events (league_family_id, occurred_at);

                CREATE TABLE IF NOT EXISTS behavior_profiles (
                    league_family_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (league_family_id, owner_id)
                );

                CREATE TABLE IF NOT EXISTS behavior_seasons (
                    league_family_id TEXT NOT NULL,
                    league_external_id TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    complete INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (league_family_id, league_external_id)
                );
                """
            )

    def put_events(self, events: Iterable[OwnerBehaviorEvent]) -> int:
        rows = list(events)
        inserted = 0
        with self._connect() as connection:
            for event in rows:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO behavior_events
                    (league_family_id, event_id, occurred_at, payload_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        event.league_family_id,
                        event.event_id,
                        event.occurred_at.isoformat(),
                        event.model_dump_json(),
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def load_events(self, league_family_id: str) -> tuple[OwnerBehaviorEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM behavior_events
                WHERE league_family_id = ?
                ORDER BY occurred_at, event_id
                """,
                (league_family_id,),
            ).fetchall()
        return tuple(OwnerBehaviorEvent.model_validate_json(row[0]) for row in rows)

    def put_profiles(self, profiles: Iterable[OwnerBehaviorProfile]) -> None:
        with self._connect() as connection:
            for profile in profiles:
                connection.execute(
                    """
                    INSERT INTO behavior_profiles
                    (league_family_id, owner_id, as_of, payload_json)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(league_family_id, owner_id) DO UPDATE SET
                        as_of = excluded.as_of,
                        payload_json = excluded.payload_json
                    """,
                    (
                        profile.league_family_id,
                        profile.owner_id,
                        profile.as_of.isoformat(),
                        profile.model_dump_json(),
                    ),
                )

    def load_profiles(self, league_family_id: str) -> tuple[OwnerBehaviorProfile, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM behavior_profiles
                WHERE league_family_id = ?
                ORDER BY owner_id
                """,
                (league_family_id,),
            ).fetchall()
        return tuple(OwnerBehaviorProfile.model_validate_json(row[0]) for row in rows)

    def mark_season_complete(self, league_family_id: str, league_external_id: str, season: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO behavior_seasons
                (league_family_id, league_external_id, season, complete)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(league_family_id, league_external_id) DO UPDATE SET
                    season = excluded.season,
                    complete = 1
                """,
                (league_family_id, league_external_id, season),
            )

    def season_is_complete(self, league_family_id: str, league_external_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT complete FROM behavior_seasons
                WHERE league_family_id = ? AND league_external_id = ?
                """,
                (league_family_id, league_external_id),
            ).fetchone()
        return bool(row and row[0])

    def complete_league_ids(self) -> frozenset[str]:
        """Sleeper league ids whose immutable historical scan is already cached."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT league_external_id FROM behavior_seasons WHERE complete = 1"
            ).fetchall()
        return frozenset(str(row[0]) for row in rows)
