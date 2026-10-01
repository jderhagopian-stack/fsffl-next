from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException

from fsffl.persistence import PersistenceStore, SyncCursorRecord
from fsffl.providers.sleeper_live import SleeperSyncProbe
from fsffl.state.models import LeagueState

from .behavioral_runtime import BehavioralRuntimeCoordinator
from .runtime import PrivateBetaRuntimeStore, league_material_fingerprint
from .webapp import ConnectSleeperLeagueRequest, require_beta_user


_logger = logging.getLogger("fsffl.product.persistence")
_performance_logger = logging.getLogger("fsffl.product.performance")
_SYNC_SCOPE_KIND = "league_refresh"


class LeagueConnectStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class LeagueConnectJob:
    job_id: str
    user_id: str
    league_external_id: str
    status: LeagueConnectStatus
    message: str
    created_at: datetime
    updated_at: datetime
    operation: str = "connect"
    error: str | None = None


ConnectWork = Callable[[], None]
StateLoader = Callable[[str], LeagueState]
SyncProbeLoader = Callable[[str], SleeperSyncProbe]
IntelligenceReconciler = Callable[[str], object]
StateTransitionReclaimer = Callable[[str], object]
StateActivator = Callable[..., object | None]


class LeagueConnectCoordinator:
    """Run hosted Sleeper imports independently of a browser request lifetime."""

    def __init__(self, *, max_workers: int = 2, max_records: int = 32) -> None:
        if max_records < 4:
            raise ValueError("connect max_records must be at least 4")
        self._lock = RLock()
        self._max_records = int(max_records)
        self._jobs: dict[str, LeagueConnectJob] = {}
        self._current_by_user: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fsffl-connect",
        )

    def current(self, user_id: str) -> LeagueConnectJob | None:
        with self._lock:
            job_id = self._current_by_user.get(user_id)
            return self._jobs.get(job_id) if job_id is not None else None

    def start(
        self,
        *,
        user_id: str,
        league_external_id: str,
        work: ConnectWork,
        operation: str = "connect",
    ) -> LeagueConnectJob:
        now = datetime.now(UTC)
        with self._lock:
            current = self.current(user_id)
            terminal = sorted(
                (
                    item
                    for item in self._jobs.values()
                    if item.status in {
                        LeagueConnectStatus.COMPLETED,
                        LeagueConnectStatus.FAILED,
                    }
                    and self._current_by_user.get(item.user_id) != item.job_id
                ),
                key=lambda item: item.updated_at,
            )
            while len(self._jobs) >= self._max_records and terminal:
                stale = terminal.pop(0)
                self._jobs.pop(stale.job_id, None)
            if (
                current is not None
                and current.league_external_id == league_external_id
                and current.status in {LeagueConnectStatus.QUEUED, LeagueConnectStatus.RUNNING}
            ):
                return current
            job = LeagueConnectJob(
                job_id=f"connect:{uuid4().hex}",
                user_id=user_id,
                league_external_id=league_external_id,
                status=LeagueConnectStatus.QUEUED,
                message=(
                    "League refresh queued on the server."
                    if operation == "refresh"
                    else "League import queued on the server."
                ),
                created_at=now,
                updated_at=now,
                operation=operation,
            )
            self._jobs[job.job_id] = job
            self._current_by_user[user_id] = job.job_id
            self._executor.submit(self._run, job.job_id, work)
            return job

    def _set(
        self,
        job_id: str,
        *,
        status: LeagueConnectStatus,
        message: str,
        error: str | None = None,
    ) -> LeagueConnectJob:
        with self._lock:
            current = self._jobs[job_id]
            updated = replace(
                current,
                status=status,
                message=message,
                updated_at=datetime.now(UTC),
                error=error,
            )
            self._jobs[job_id] = updated
            return updated

    def _run(self, job_id: str, work: ConnectWork) -> None:
        current = self._jobs[job_id]
        self._set(
            job_id,
            status=LeagueConnectStatus.RUNNING,
            message=(
                "Checking Sleeper for league updates."
                if current.operation == "refresh"
                else "Loading current league data from Sleeper."
            ),
        )
        try:
            work()
        except Exception as exc:
            _logger.warning(
                "FSFFL Sleeper background job failed job=%s user=%s league=%s operation=%s error=%s",
                current.job_id,
                current.user_id,
                current.league_external_id,
                current.operation,
                exc,
            )
            self._set(
                job_id,
                status=LeagueConnectStatus.FAILED,
                message=(
                    "League refresh failed. Stored league data remains available."
                    if current.operation == "refresh"
                    else "League import failed."
                ),
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        _logger.info(
            "FSFFL Sleeper background job completed job=%s user=%s league=%s operation=%s",
            current.job_id,
            current.user_id,
            current.league_external_id,
            current.operation,
        )
        self._set(
            job_id,
            status=LeagueConnectStatus.COMPLETED,
            message=(
                "League sync is complete."
                if current.operation == "refresh"
                else "League is ready."
            ),
        )


def _job_payload(job: LeagueConnectJob | None) -> dict[str, object]:
    if job is None:
        return {
            "job_id": None,
            "league_external_id": None,
            "status": "idle",
            "operation": None,
            "message": "No league import is running.",
            "error": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "job_id": job.job_id,
        "league_external_id": job.league_external_id,
        "status": job.status.value,
        "operation": job.operation,
        "message": job.message,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def _matches_sleeper_league(league_state: LeagueState | None, league_external_id: str) -> bool:
    if league_state is None:
        return False
    if league_state.league.league_id == f"sleeper:{league_external_id}":
        return True
    return any(
        ref.provider == "sleeper" and ref.external_id == league_external_id
        for ref in league_state.league.provider_refs
    )


def _full_refresh_due(
    cursor: SyncCursorRecord | None,
    *,
    now: datetime,
    full_refresh_seconds: int,
) -> bool:
    if cursor is None:
        return True
    raw = cursor.cursor_payload.get("last_full_refresh_at")
    if not raw:
        return True
    try:
        last_full = datetime.fromisoformat(str(raw))
    except ValueError:
        return True
    if last_full.tzinfo is None:
        return True
    return (now - last_full).total_seconds() >= full_refresh_seconds


def _probe_matches_cursor(cursor: SyncCursorRecord | None, probe: SleeperSyncProbe) -> bool:
    return bool(
        cursor is not None
        and cursor.cursor_payload.get("probe_fingerprint") == probe.fingerprint
        and cursor.cursor_payload.get("season") == probe.season
        and cursor.cursor_payload.get("week") == probe.week
    )


def install_hosted_connect_routes(
    application: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    state_loader: StateLoader,
    behavioral_coordinator: BehavioralRuntimeCoordinator,
    coordinator: LeagueConnectCoordinator | None = None,
    persistence_store: PersistenceStore | None = None,
    sync_probe_loader: SyncProbeLoader | None = None,
    intelligence_reconciler: IntelligenceReconciler | None = None,
    state_activator: StateActivator | None = None,
    state_transition_reclaimer: StateTransitionReclaimer | None = None,
    full_refresh_seconds: int = 3600,
) -> LeagueConnectCoordinator:
    """Attach hosted-only background connect and refresh routes to the beta app."""

    if full_refresh_seconds < 1:
        raise ValueError("full_refresh_seconds must be positive")
    jobs = coordinator or LeagueConnectCoordinator(max_workers=2)
    # The intelligence refresh route shares this coordinator at request time so a
    # browser's automatic Sleeper revalidation and explicit Refresh Intelligence
    # tap cannot launch two concurrent State materializations for one user.
    application.state.hosted_connect_jobs = jobs

    @application.post("/api/connect/sleeper/background")
    def start_background_connect(
        request: ConnectSleeperLeagueRequest,
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        league_external_id = request.league_external_id.strip()
        if not league_external_id:
            raise HTTPException(status_code=422, detail="Sleeper league id cannot be blank")

        runtime = runtime_store.get(user_id)
        already_loaded = _matches_sleeper_league(runtime.league_state, league_external_id)
        if not already_loaded:
            prepare_fresh_connect = getattr(
                runtime_store,
                "prepare_fresh_connect",
                None,
            )
            if callable(prepare_fresh_connect):
                prepare_fresh_connect(user_id)
        active_league_id = (
            runtime.league_state.league.league_id
            if runtime.league_state is not None
            else None
        )
        _performance_logger.info(
            "FSFFL Sleeper connect request user=%s requested=%s active=%s already_loaded=%s",
            user_id,
            league_external_id,
            active_league_id,
            already_loaded,
        )

        def work() -> None:
            if already_loaded:
                _logger.info(
                    "FSFFL Sleeper connect reused active league user=%s league=%s",
                    user_id,
                    league_external_id,
                )
                restored_runtime = runtime_store.get(user_id)
                if (
                    intelligence_reconciler is not None
                    and restored_runtime.selected_team_id is not None
                ):
                    intelligence_reconciler(user_id)
                return
            league_state = state_loader(league_external_id)
            if not _matches_sleeper_league(league_state, league_external_id):
                raise ValueError("Sleeper state loader returned a different league")
            current_job = jobs.current(user_id)
            if current_job is not None and current_job.league_external_id != league_external_id:
                _logger.info(
                    "FSFFL Sleeper connect superseded before activation user=%s requested=%s current=%s",
                    user_id,
                    league_external_id,
                    current_job.league_external_id,
                )
                return
            with runtime_store.lifecycle_operation(user_id):
                if state_activator is not None:
                    activated = state_activator(
                        user_id,
                        league_state,
                        reason="background_connect",
                    )
                else:
                    activate_state = getattr(
                        runtime_store,
                        "activate_league_state_for_connect",
                        runtime_store.set_league_state,
                    )
                    activate_state(user_id, league_state)
                    activated = runtime_store.get(user_id)
                active_runtime = runtime_store.get(user_id)
                active_state = active_runtime.league_state
                if (
                    activated is None
                    or not _matches_sleeper_league(active_state, league_external_id)
                    or active_state is None
                    or active_state.state_id != league_state.state_id
                ):
                    raise RuntimeError("Sleeper league activation lost requested identity")
                if (
                    state_activator is None
                    and state_transition_reclaimer is not None
                    and active_league_id is not None
                    and active_league_id != league_state.league.league_id
                ):
                    state_transition_reclaimer(
                        f"{user_id}:{league_state.state_id}:league_switch"
                    )
                _logger.info(
                    "FSFFL Sleeper connect activated user=%s league=%s state=%s",
                    user_id,
                    league_external_id,
                    league_state.state_id,
                )
                behavioral_coordinator.start(
                    user_id=user_id,
                    league_state=league_state,
                    sleeper_league_external_id=league_external_id,
                )
                # Revalidate under the same lifecycle ownership before handing off
                # any new heavy work. A newer transition cannot become canonical
                # between cleanup and these replacement execution starts.
                active_runtime = runtime_store.get(user_id)
                if (
                    active_runtime.league_state is None
                    or active_runtime.league_state.state_id != league_state.state_id
                ):
                    raise RuntimeError("Sleeper league ownership changed after activation")
                if (
                    intelligence_reconciler is not None
                    and active_runtime.selected_team_id is not None
                ):
                    intelligence_reconciler(user_id)
                elif intelligence_reconciler is not None:
                    _logger.info(
                        "FSFFL Sleeper connect deferred intelligence until managed-team selection user=%s league=%s state=%s",
                        user_id,
                        league_external_id,
                        league_state.state_id,
                    )

        return _job_payload(
            jobs.start(
                user_id=user_id,
                league_external_id=league_external_id,
                work=work,
                operation="connect",
            )
        )

    @application.post("/api/connect/sleeper/background/refresh")
    def start_background_refresh(
        request: ConnectSleeperLeagueRequest,
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        """Revalidate a restored league without making the browser wait for it."""

        league_external_id = request.league_external_id.strip()
        if not league_external_id:
            raise HTTPException(status_code=422, detail="Sleeper league id cannot be blank")

        runtime = runtime_store.get(user_id)
        if not _matches_sleeper_league(runtime.league_state, league_external_id):
            raise HTTPException(status_code=409, detail="Requested league is not loaded")

        previous_state = runtime.league_state
        previous_fingerprint = (
            league_material_fingerprint(previous_state) if previous_state is not None else None
        )
        refresh_generation = runtime_store.league_generation(user_id)

        def work() -> None:
            now = datetime.now(UTC)
            probe: SleeperSyncProbe | None = None
            cursor: SyncCursorRecord | None = None
            if persistence_store is not None and sync_probe_loader is not None:
                try:
                    probe = sync_probe_loader(league_external_id)
                    cursor = persistence_store.get_sync_cursor(
                        provider="sleeper",
                        scope_kind=_SYNC_SCOPE_KIND,
                        scope_id=league_external_id,
                    )
                    if (
                        _probe_matches_cursor(cursor, probe)
                        and not _full_refresh_due(
                            cursor,
                            now=now,
                            full_refresh_seconds=full_refresh_seconds,
                        )
                    ):
                        _logger.info(
                            "FSFFL Sleeper incremental sync reused stored state league=%s week=%s",
                            league_external_id,
                            probe.week,
                        )
                        current_runtime = runtime_store.get(user_id)
                        if (
                            intelligence_reconciler is not None
                            and current_runtime.selected_team_id is not None
                        ):
                            intelligence_reconciler(user_id)
                        return
                except Exception as exc:
                    # The probe is an optimization only. Any probe/cursor failure must
                    # fall back to the authoritative full provider refresh.
                    _logger.warning(
                        "FSFFL Sleeper sync probe failed; forcing full refresh league=%s error=%s",
                        league_external_id,
                        exc,
                    )
                    probe = None

            league_state = state_loader(league_external_id)
            if not _matches_sleeper_league(league_state, league_external_id):
                raise ValueError("Sleeper state loader returned a different league")
            changed = (
                previous_fingerprint is None
                or league_material_fingerprint(league_state) != previous_fingerprint
            )
            current_job = jobs.current(user_id)
            active_state = runtime_store.get(user_id).league_state
            if (
                runtime_store.league_generation(user_id) != refresh_generation
                or not _matches_sleeper_league(active_state, league_external_id)
                or (
                    current_job is not None
                    and current_job.league_external_id != league_external_id
                )
            ):
                _performance_logger.info(
                    "FSFFL Sleeper refresh superseded before activation user=%s requested=%s current_job=%s generation_start=%s generation_now=%s",
                    user_id,
                    league_external_id,
                    current_job.league_external_id if current_job is not None else None,
                    refresh_generation,
                    runtime_store.league_generation(user_id),
                )
                return
            with runtime_store.lifecycle_operation(user_id):
                if not changed:
                    # A fresh provider capture with identical material facts is
                    # verification, not a new canonical State. Keep the published
                    # State/artifact identities intact and reconcile only if some
                    # governed product capability is actually missing.
                    refreshed_runtime = runtime_store.get(user_id)
                    if (
                        runtime_store.league_generation(user_id) != refresh_generation
                        or not _matches_sleeper_league(
                            refreshed_runtime.league_state,
                            league_external_id,
                        )
                    ):
                        _performance_logger.info(
                            "FSFFL Sleeper unchanged refresh superseded before reconciliation user=%s requested=%s",
                            user_id,
                            league_external_id,
                        )
                        return
                    _performance_logger.info(
                        "FSFFL Sleeper full refresh verified no material State change user=%s league=%s retained_state=%s",
                        user_id,
                        league_external_id,
                        (
                            refreshed_runtime.league_state.state_id
                            if refreshed_runtime.league_state is not None
                            else None
                        ),
                    )
                    if (
                        intelligence_reconciler is not None
                        and refreshed_runtime.selected_team_id is not None
                    ):
                        intelligence_reconciler(user_id)
                else:
                    if state_activator is not None:
                        activated = state_activator(
                            user_id,
                            league_state,
                            reason="background_material_refresh",
                            expected_generation=refresh_generation,
                            expected_league_id=runtime.league_state.league.league_id,
                        )
                    else:
                        activated = runtime_store.set_league_state_if_generation(
                            user_id,
                            league_state,
                            expected_generation=refresh_generation,
                            expected_league_id=runtime.league_state.league.league_id,
                        )
                    if activated is None:
                        _performance_logger.info(
                            "FSFFL Sleeper refresh superseded at activation user=%s requested=%s",
                            user_id,
                            league_external_id,
                        )
                        return
                    if (
                        state_activator is None
                        and state_transition_reclaimer is not None
                    ):
                        state_transition_reclaimer(
                            f"{user_id}:{league_state.state_id}:state_refresh"
                        )
                    state_identity_changed = (
                        previous_state is None
                        or previous_state.state_id != league_state.state_id
                    )
                    if state_identity_changed:
                        behavioral_coordinator.start(
                            user_id=user_id,
                            league_state=league_state,
                            sleeper_league_external_id=league_external_id,
                        )
                    refreshed_runtime = runtime_store.get(user_id)
                    if (
                        refreshed_runtime.league_state is None
                        or refreshed_runtime.league_state.state_id != league_state.state_id
                    ):
                        _performance_logger.info(
                            "FSFFL Sleeper refresh superseded after boundary user=%s requested=%s",
                            user_id,
                            league_external_id,
                        )
                        return
                    if (
                        intelligence_reconciler is not None
                        and refreshed_runtime.selected_team_id is not None
                    ):
                        intelligence_reconciler(user_id)

            if persistence_store is not None and probe is not None:
                try:
                    persistence_store.put_sync_cursor(
                        SyncCursorRecord(
                            provider="sleeper",
                            scope_kind=_SYNC_SCOPE_KIND,
                            scope_id=league_external_id,
                            cursor_payload={
                                "probe_fingerprint": probe.fingerprint,
                                "season": probe.season,
                                "week": probe.week,
                                "last_full_refresh_at": now.isoformat(),
                            },
                            synced_at=now,
                            source_updated_at=probe.captured_at,
                        )
                    )
                except Exception as exc:
                    _logger.warning(
                        "FSFFL Sleeper sync cursor checkpoint failed league=%s error=%s",
                        league_external_id,
                        exc,
                    )

        return _job_payload(
            jobs.start(
                user_id=user_id,
                league_external_id=league_external_id,
                work=work,
                operation="refresh",
            )
        )

    @application.get("/api/connect/sleeper/background/current")
    def current_background_connect(
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        return _job_payload(jobs.current(user_id))

    return jobs
