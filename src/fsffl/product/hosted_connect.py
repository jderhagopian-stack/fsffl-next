from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException

from fsffl.state.models import LeagueState

from .behavioral_runtime import BehavioralRuntimeCoordinator
from .runtime import PrivateBetaRuntimeStore
from .webapp import ConnectSleeperLeagueRequest, require_beta_user


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
    error: str | None = None


ConnectWork = Callable[[], None]
StateLoader = Callable[[str], LeagueState]


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
    ) -> LeagueConnectJob:
        now = datetime.now(UTC)
        with self._lock:
            current = self.current(user_id)
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
                message="League import queued on the server.",
                created_at=now,
                updated_at=now,
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
        self._set(
            job_id,
            status=LeagueConnectStatus.RUNNING,
            message="Loading current league data from Sleeper.",
        )
        try:
            work()
        except Exception as exc:
            self._set(
                job_id,
                status=LeagueConnectStatus.FAILED,
                message="League import failed.",
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        self._set(
            job_id,
            status=LeagueConnectStatus.COMPLETED,
            message="League is ready.",
        )


def _job_payload(job: LeagueConnectJob | None) -> dict[str, object]:
    if job is None:
        return {
            "job_id": None,
            "league_external_id": None,
            "status": "idle",
            "message": "No league import is running.",
            "error": None,
            "created_at": None,
            "updated_at": None,
        }
    return {
        "job_id": job.job_id,
        "league_external_id": job.league_external_id,
        "status": job.status.value,
        "message": job.message,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


def install_hosted_connect_routes(
    application: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    state_loader: StateLoader,
    behavioral_coordinator: BehavioralRuntimeCoordinator,
    coordinator: LeagueConnectCoordinator | None = None,
) -> LeagueConnectCoordinator:
    """Attach hosted-only background connect routes to the private-beta app."""

    jobs = coordinator or LeagueConnectCoordinator(max_workers=2)

    @application.post("/api/connect/sleeper/background")
    def start_background_connect(
        request: ConnectSleeperLeagueRequest,
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        league_external_id = request.league_external_id.strip()
        if not league_external_id:
            raise HTTPException(status_code=422, detail="Sleeper league id cannot be blank")

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
            )
        )

    @application.get("/api/connect/sleeper/background/current")
    def current_background_connect(
        user_id: str = Depends(require_beta_user),
    ) -> dict[str, object]:
        return _job_payload(jobs.current(user_id))

    return jobs
