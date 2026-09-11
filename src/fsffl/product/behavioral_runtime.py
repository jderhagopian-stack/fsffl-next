from __future__ import annotations

import logging
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


_logger = logging.getLogger("fsffl.product.behavioral")


class BehavioralRuntimeStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class BehavioralRuntimeRecord:
    user_id: str
    league_state_id: str | None = None
    sleeper_league_external_id: str | None = None
    status: BehavioralRuntimeStatus = BehavioralRuntimeStatus.IDLE
    started_at: datetime | None = None
    updated_at: datetime | None = None
    result: BehavioralSyncResult | None = None
    error: str | None = None


BehavioralWork = Callable[[LeagueState, str], BehavioralSyncResult]
BehavioralStoreFactory = Callable[[], object]
_profile_cache_lock = RLock()
_profile_cache: dict[tuple[str, str], OwnerBehaviorProfile] = {}
_hosted_store_lock = RLock()
_hosted_postgres_stores: dict[str, PostgresBehavioralIntelligenceStore] = {}


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
    """Reuse one hosted Postgres store per process; retain SQLite for local/tests.

    Constructing the hosted Postgres adapter performs its deploy-before-migration
    schema safety bootstrap. Reconstructing that adapter on request therefore also
    repeats PostgreSQL DDL, including CREATE INDEX IF NOT EXISTS. Keep exactly one
    adapter for each configured database URL so that safety bootstrap happens once
    per web process rather than during restore/status/Behavioral request paths.

    This is connection/bootstrap reuse only. The store remains evidence persistence;
    no Behavioral inference, model truth, or cache validity rule changes here.
    """

    database_url = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if database_url:
        with _hosted_store_lock:
            store = _hosted_postgres_stores.get(database_url)
            if store is None:
                store = PostgresBehavioralIntelligenceStore(database_url)
                _hosted_postgres_stores[database_url] = store
            return store
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
    """Build/reuse league Behavioral Intelligence without blocking league load.

    Durable observed Behavioral history is independently readable from the
    in-memory refresh lifecycle. The in-memory record communicates active refresh
    state; it is not the persistence authority for previously built profiles.
    """

    def __init__(
        self,
        *,
        work: BehavioralWork = default_behavioral_work,
        store_factory: BehavioralStoreFactory = default_behavioral_store,
        max_workers: int = 2,
    ) -> None:
        self._work = work
        self._store_factory = store_factory
        self._lock = RLock()
        self._records: dict[str, BehavioralRuntimeRecord] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fsffl-behavior")

    def _hydrate_durable_record(self, user_id: str) -> BehavioralRuntimeRecord | None:
        try:
            store = self._store_factory()
            context = store.load_runtime_context(user_id)
            if context is None:
                return None
            league_family_id = str(context["league_family_id"])
            profiles = store.load_profiles(league_family_id)
            events = store.load_events(league_family_id)
            result = BehavioralSyncResult(
                league_family_id=league_family_id,
                profile_count=len(profiles),
                total_event_count=len(events),
                inserted_event_count=0,
                reused_historical_league_ids=(),
                scanned_league_ids=(),
                current_owner_by_roster=tuple(context["current_owner_by_roster"]),
                profiles=profiles,
            )
        except Exception as exc:
            _logger.warning("Unable to hydrate durable Behavioral history for user=%s: %s", user_id, exc)
            return None
        return BehavioralRuntimeRecord(
            user_id=user_id,
            league_state_id=str(context["league_state_id"]),
            sleeper_league_external_id=str(context["sleeper_league_external_id"]),
            status=BehavioralRuntimeStatus.READY,
            updated_at=datetime.now(UTC),
            result=result,
        )

    def current(self, user_id: str) -> BehavioralRuntimeRecord:
        with self._lock:
            record = self._records.get(user_id)
        if record is not None:
            return record

        hydrated = self._hydrate_durable_record(user_id)
        if hydrated is None:
            return BehavioralRuntimeRecord(user_id=user_id)
        with self._lock:
            return self._records.setdefault(user_id, hydrated)

    def profile_for_team(
        self,
        user_id: str,
        league_state: LeagueState,
        team_id: str,
    ) -> OwnerBehaviorProfile | None:
        """Resolve the current team to its stable Sleeper owner profile.

        Behavioral evidence follows owner identity across seasons rather than
        assuming a roster/team slot is the manager. Missing, refreshing, or
        refresh-failed history returns None to governed Decision consumers; the
        Product surface may still display previously valid durable observations.
        """

        record = self.current(user_id)
        if (
            record.status != BehavioralRuntimeStatus.READY
            or record.result is None
            or record.error is not None
        ):
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
        current = self.current(user_id)
        with self._lock:
            live_current = self._records.get(user_id, current)
            if (
                live_current.sleeper_league_external_id == sleeper_league_external_id
                and live_current.league_state_id == league_state.state_id
                and live_current.status == BehavioralRuntimeStatus.RUNNING
            ):
                return live_current
            reusable_result = (
                live_current.result
                if live_current.sleeper_league_external_id == sleeper_league_external_id
                else None
            )
            record = BehavioralRuntimeRecord(
                user_id=user_id,
                league_state_id=league_state.state_id,
                sleeper_league_external_id=sleeper_league_external_id,
                status=BehavioralRuntimeStatus.RUNNING,
                started_at=now,
                updated_at=now,
                result=reusable_result,
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
            self._store_factory().put_runtime_context(
                user_id=user_id,
                league_state_id=league_state.state_id,
                sleeper_league_external_id=sleeper_league_external_id,
                league_family_id=result.league_family_id,
                current_owner_by_roster=result.current_owner_by_roster,
            )
        except Exception as exc:
            with self._lock:
                current = self._records.get(user_id, BehavioralRuntimeRecord(user_id=user_id))
                self._records[user_id] = replace(
                    current,
                    status=(
                        BehavioralRuntimeStatus.READY
                        if current.result is not None
                        else BehavioralRuntimeStatus.FAILED
                    ),
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
