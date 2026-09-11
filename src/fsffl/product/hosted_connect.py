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
_SYNC_SCOPE_KIND = "league_refresh"
_ACTIVE_STATUSES = {"queued", "running"}


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


class LeagueConnectCoordinator:
    """Run hosted Sleeper imports independently of a browser request lifetime."""

    def __init__(self, *, max_workers: int = 2) -> None:
        self._lock = RLock()
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
            if (
                current is not None
                and current.league_external_id == league_external_id
                and current.operation == operation
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


def _already_ready_payload(league_external_id: str) -> dict[str, object]:
    """Return connect completion without attaching the browser to secondary refresh work."""

    now = datetime.now(UTC).isoformat()
    return {
        "job_id": None,
        "league_external_id": league_external_id,
        "status": LeagueConnectStatus.COMPLETED.value,
        "operation": "connect",
        "message": "League is ready from stored state.",
        "error": None,
        "created_at": now,
        "updated_at": now,
    }


def _active_job_conflict(
    current: LeagueConnectJob | None,
    *,
    league_external_id: str,
    operation: str,
) -> bool:
    if current is None or current.status.value not in _ACTIVE_STATUSES:
        return False
    return current.league_external_id != league_external_id or current.operation != operation


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
    full_refresh_seconds: int = 3600,
) -> LeagueConnectCoordinator:
    """Attach hosted-only background connect and refresh routes to the beta app."""

    if full_refresh_seconds < 1:
        raise ValueError("full_refresh_seconds must be positive")
    jobs = coordinator or LeagueConnectCoordinator(max_workers=2)

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
        if already_loaded:
            # Canonical persisted league state is sufficient to enter the product.
            # A refresh/intelligence job must never hold a connect caller hostage.
            return _already_ready_payload(league_external_id)

        current = jobs.current(user_id)
        if _active_job_conflict(
            current,
            league_external_id=league_external_id,
            operation="connect",
        ):
            raise HTTPException(
                status_code=409,
                detail="Another league operation is already in progress",
            )

        def work() -> None:
            league_state = state_loader(league_external_id)
            runtime_store.set_league_state(user_id, league_state)
            behavioral_coordinator.start(
                user_id=user_id,
                league_state=league_state,
                sleeper_league_external_id=league_external_id,
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

        current = jobs.current(user_id)
        if _active_job_conflict(
            current,
            league_external_id=league_external_id,
            operation="refresh",
        ):
            # Do not launch overlapping provider work or replace the current-job slot.
            # Stored canonical state remains usable while the existing operation finishes.
            raise HTTPException(
                status_code=409,
                detail="Another league operation is already in progress",
            )

        previous_state = runtime.league_state
        previous_fingerprint = (
            league_material_fingerprint(previous_state) if previous_state is not None else None
        )

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
            changed = (
                previous_fingerprint is None
                or league_material_fingerprint(league_state) != previous_fingerprint
            )
            runtime_store.set_league_state(user_id, league_state)
            if changed:
                behavioral_coordinator.start(
                    user_id=user_id,
                    league_state=league_state,
                    sleeper_league_external_id=league_external_id,
                )

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
