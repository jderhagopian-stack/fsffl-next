from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Callable
from uuid import uuid4


class IntelligenceJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IntelligenceJobPhase(StrEnum):
    QUEUED = "queued"
    BUILDING_FORECASTS = "building_forecasts"
    REFRESHING_STATE = "refreshing_state"
    RUNNING_SIMULATION = "running_simulation"
    BUILDING_VALUES = "building_values"
    ATTACHING_RESULTS = "attaching_results"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class IntelligenceJob:
    job_id: str
    user_id: str
    league_state_id: str
    status: IntelligenceJobStatus
    phase: IntelligenceJobPhase
    message: str
    created_at: datetime
    updated_at: datetime
    error: str | None = None


ProgressCallback = Callable[[IntelligenceJobPhase, str], None]
JobWork = Callable[[ProgressCallback], None]


class IntelligenceJobCoordinator:
    """Own beta background execution without owning forecast/simulation/value math.

    This is intentionally an in-process coordinator for the private beta. Browser
    lifetime is decoupled from work lifetime, while the model layers remain
    authoritative for forecast, simulation and Value outputs. A durable queue can
    later replace this interface without changing those model authorities.
    """

    def __init__(self, *, max_workers: int = 2) -> None:
        self._lock = RLock()
        self._jobs: dict[str, IntelligenceJob] = {}
        self._current_by_user: dict[str, str] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fsffl-intelligence")

    def get(self, job_id: str) -> IntelligenceJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def current(self, user_id: str) -> IntelligenceJob | None:
        with self._lock:
            job_id = self._current_by_user.get(user_id)
            return self._jobs.get(job_id) if job_id is not None else None

    def start(self, *, user_id: str, league_state_id: str, work: JobWork) -> IntelligenceJob:
        now = datetime.now(UTC)
        with self._lock:
            current = self.current(user_id)
            if (
                current is not None
                and current.league_state_id == league_state_id
                and current.status in {IntelligenceJobStatus.QUEUED, IntelligenceJobStatus.RUNNING}
            ):
                return current

            job = IntelligenceJob(
                job_id=f"intelligence:{uuid4().hex}",
                user_id=user_id,
                league_state_id=league_state_id,
                status=IntelligenceJobStatus.QUEUED,
                phase=IntelligenceJobPhase.QUEUED,
                message="Intelligence refresh queued on the server.",
                created_at=now,
                updated_at=now,
            )
            self._jobs[job.job_id] = job
            self._current_by_user[user_id] = job.job_id
            self._executor.submit(self._run, job.job_id, work)
            return job

    def _update(
        self,
        job_id: str,
        *,
        status: IntelligenceJobStatus,
        phase: IntelligenceJobPhase,
        message: str,
        error: str | None = None,
    ) -> IntelligenceJob:
        with self._lock:
            current = self._jobs[job_id]
            updated = replace(
                current,
                status=status,
                phase=phase,
                message=message,
                updated_at=datetime.now(UTC),
                error=error,
            )
            self._jobs[job_id] = updated
            return updated

    def _run(self, job_id: str, work: JobWork) -> None:
        self._update(
            job_id,
            status=IntelligenceJobStatus.RUNNING,
            phase=IntelligenceJobPhase.BUILDING_FORECASTS,
            message="Building governed multi-source projections.",
        )

        def progress(phase: IntelligenceJobPhase, message: str) -> None:
            self._update(
                job_id,
                status=IntelligenceJobStatus.RUNNING,
                phase=phase,
                message=message,
            )

        try:
            work(progress)
        except Exception as exc:
            self._update(
                job_id,
                status=IntelligenceJobStatus.FAILED,
                phase=IntelligenceJobPhase.FAILED,
                message="Intelligence refresh failed.",
                error=f"{type(exc).__name__}: {exc}",
            )
            return

        self._update(
            job_id,
            status=IntelligenceJobStatus.COMPLETED,
            phase=IntelligenceJobPhase.COMPLETED,
            message="Forecasts, simulation and current Value evidence are ready.",
        )
