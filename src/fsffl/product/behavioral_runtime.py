from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import RLock
from typing import Callable

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.postgres_store import PostgresBehavioralIntelligenceStore
from fsffl.behavioral.service import BehavioralIntelligenceService, BehavioralSyncResult
from fsffl.behavioral.sleeper_history import SleeperBehaviorHistorySource
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.state.models import LeagueState


class BehavioralRuntimeStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class BehavioralRuntimeRecord:
    user_id: str
    league_state_id: str | None = None
    status: BehavioralRuntimeStatus = BehavioralRuntimeStatus.IDLE
    started_at: datetime | None = None
    updated_at: datetime | None = None
    result: BehavioralSyncResult | None = None
    error: str | None = None


BehavioralWork = Callable[[LeagueState, str], BehavioralSyncResult]
_profile_cache_lock = RLock()
_profile_cache: dict[tuple[str, str], OwnerBehaviorProfile] = {}


def cached_behavior_profile_for_team(
    league_state: LeagueState,
    team_id: str,
) -> OwnerBehaviorProfile | None:
    """Return already-built Behavioral evidence for this exact State/team.

    This is a read-only runtime convenience for Product evaluators. It does not
    rebuild history, create substitute evidence, or change Behavioral authority.
    If the asynchronous Behavioral build has not completed, callers receive None.
    """

    with _profile_cache_lock:
        return _profile_cache.get((league_state.state_id, team_id))


def _publish_profiles_for_state(
    league_state: LeagueState,
    result: BehavioralSyncResult,
) -> None:
    profiles_by_owner = {profile.owner_id: profile for profile in result.profiles}
    owners_by_roster = dict(result.current_owner_by_roster)
    entries: dict[tuple[str, str], OwnerBehaviorProfile] = {}
    for team in league_state.teams:
        sleeper_ref = next((ref for ref in team.provider_refs if ref.provider == "sleeper"), None)
        if sleeper_ref is None:
            continue
        try:
            roster_id = int(sleeper_ref.external_id)
        except ValueError:
            continue
        owner_id = owners_by_roster.get(roster_id)
        profile = profiles_by_owner.get(owner_id) if owner_id is not None else None
        if profile is not None:
            entries[(league_state.state_id, team.team_id)] = profile
    with _profile_cache_lock:
        _profile_cache.update(entries)


def default_behavioral_cache_path() -> Path:
    """Return the local/test Behavioral cache path."""

    return Path(os.getenv("FSFFL_BEHAVIOR_CACHE_PATH", "/tmp/fsffl-next/behavior.sqlite3"))


def default_behavioral_store():
    """Use hosted Postgres when configured; retain SQLite for local/test workflows."""

    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if database_url:
        return PostgresBehavioralIntelligenceStore(database_url)
    return BehavioralIntelligenceStore(default_behavioral_cache_path())


def default_behavioral_work(league_state: LeagueState, sleeper_league_external_id: str) -> BehavioralSyncResult:
    service = BehavioralIntelligenceService(
        source=SleeperBehaviorHistorySource(),
        store=default_behavioral_store(),
    )
    return service.sync_sleeper_league(
        league_state,
        sleeper_league_external_id=sleeper_league_external_id,
    )


class BehavioralRuntimeCoordinator:
    """Build/reuse league Behavioral Intelligence without blocking league load."""

    def __init__(self, *, work: BehavioralWork = default_behavioral_work, max_workers: int = 2) -> None:
        self._work = work
        self._lock = RLock()
        self._records: dict[str, BehavioralRuntimeRecord] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fsffl-behavior")

    def current(self, user_id: str) -> BehavioralRuntimeRecord:
        with self._lock:
            return self._records.get(user_id, BehavioralRuntimeRecord(user_id=user_id))

    def profile_for_team(
        self,
        user_id: str,
        league_state: LeagueState,
        team_id: str,
    ) -> OwnerBehaviorProfile | None:
        """Resolve the current team to its stable Sleeper owner profile.

        Behavioral evidence follows owner identity across seasons rather than
        assuming a roster/team slot is the manager. Missing or still-building
        history returns None; consumers must remain functional without inventing
        a behavioral substitute.
        """

        record = self.current(user_id)
        if record.status != BehavioralRuntimeStatus.READY or record.result is None:
            return None
        team = next((item for item in league_state.teams if item.team_id == team_id), None)
        if team is None:
            return None
        sleeper_ref = next((ref for ref in team.provider_refs if ref.provider == "sleeper"), None)
        if sleeper_ref is None:
            return None
        try:
            roster_id = int(sleeper_ref.external_id)
        except ValueError:
            return None
        owner_id = next(
            (owner for roster, owner in record.result.current_owner_by_roster if roster == roster_id),
            None,
        )
        if owner_id is None:
            return None
        return next((profile for profile in record.result.profiles if profile.owner_id == owner_id), None)

    def start(
        self,
        *,
        user_id: str,
        league_state: LeagueState,
        sleeper_league_external_id: str,
    ) -> BehavioralRuntimeRecord:
        now = datetime.now(UTC)
        with self._lock:
            current = self.current(user_id)
            if current.league_state_id == league_state.state_id and current.status == BehavioralRuntimeStatus.RUNNING:
                return current
            record = BehavioralRuntimeRecord(
                user_id=user_id,
                league_state_id=league_state.state_id,
                status=BehavioralRuntimeStatus.RUNNING,
                started_at=now,
                updated_at=now,
            )
            self._records[user_id] = record
            self._executor.submit(
                self._run,
                user_id,
                league_state,
                sleeper_league_external_id,
            )
            return record

    def _run(self, user_id: str, league_state: LeagueState, sleeper_league_external_id: str) -> None:
        try:
            result = self._work(league_state, sleeper_league_external_id)
        except Exception as exc:
            with self._lock:
                current = self._records.get(user_id, BehavioralRuntimeRecord(user_id=user_id))
                self._records[user_id] = replace(
                    current,
                    status=BehavioralRuntimeStatus.FAILED,
                    updated_at=datetime.now(UTC),
                    error=f"{type(exc).__name__}: {exc}",
                )
            return
        with self._lock:
            current = self._records.get(user_id, BehavioralRuntimeRecord(user_id=user_id))
            if current.league_state_id != league_state.state_id:
                return
            self._records[user_id] = replace(
                current,
                status=BehavioralRuntimeStatus.READY,
                updated_at=datetime.now(UTC),
                result=result,
                error=None,
            )
        _publish_profiles_for_state(league_state, result)
