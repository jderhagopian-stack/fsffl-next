from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock, get_native_id
from time import monotonic
from typing import Callable
from uuid import uuid4


_logger = logging.getLogger("fsffl.product.performance")


def _deprioritize_background_thread() -> None:
    """Give request-serving threads precedence during CPU-heavy refresh work.

    Render's free instance is CPU-capped. Intelligence refresh is best-effort
    background work, so its dedicated executor thread may run at a lower Linux
    scheduler priority without changing Forecast/Simulation/Value inputs or math.
    Unsupported platforms fail open to the existing scheduler behavior.
    """

    raw = os.getenv("FSFFL_INTELLIGENCE_NICE", "10").strip()
    try:
        nice = max(0, min(19, int(raw)))
    except ValueError:
        nice = 10
    if nice <= 0 or not hasattr(os, "setpriority") or not hasattr(os, "PRIO_PROCESS"):
        return
    try:
        native_id = get_native_id()
        os.setpriority(os.PRIO_PROCESS, native_id, nice)
        _logger.info(
            "FSFFL intelligence scheduler priority native_thread=%s nice=%s",
            native_id,
            nice,
        )
    except (OSError, PermissionError) as exc:
        _logger.warning("FSFFL intelligence scheduler priority unchanged error=%s", exc)


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
class IntelligencePhaseTiming:
    """Observed wall-clock duration for one completed runtime phase."""

    phase: IntelligenceJobPhase
    elapsed_seconds: float


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
    phase_timings: tuple[IntelligencePhaseTiming, ...] = ()
    total_elapsed_seconds: float | None = None


ProgressCallback = Callable[[IntelligenceJobPhase, str], None]
JobWork = Callable[[ProgressCallback], None]


class IntelligenceJobCoordinator:
    """Own beta background execution without owning forecast/simulation/value math.

    This is intentionally an in-process coordinator for the private beta. Browser
    lifetime is decoupled from work lifetime, while the model layers remain
    authoritative for forecast, simulation and Value outputs. A durable queue can
    later replace this interface without changing those model authorities.

    The coordinator also records wall-clock phase timings. Timing is observability
    metadata only: it cannot alter model inputs, simulation count, outputs, or
    authority. This lets the beta identify the real end-to-end bottleneck instead
    of inferring it from isolated microbenchmarks.
    """

    def __init__(self, *, max_workers: int = 2) -> None:
        self._lock = RLock()
        self._jobs: dict[str, IntelligenceJob] = {}
        self._current_by_user: dict[str, str] = {}
        self._job_started_monotonic: dict[str, float] = {}
        self._phase_started_monotonic: dict[str, float] = {}
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
        now = datetime.now(UTC)
        now_monotonic = monotonic()
        with self._lock:
            current = self._jobs[job_id]
            timings = current.phase_timings
            total_elapsed = current.total_elapsed_seconds

            if status == IntelligenceJobStatus.RUNNING and job_id not in self._job_started_monotonic:
                self._job_started_monotonic[job_id] = now_monotonic
                self._phase_started_monotonic[job_id] = now_monotonic
            elif current.status == IntelligenceJobStatus.RUNNING and phase != current.phase:
                phase_started = self._phase_started_monotonic.get(job_id)
                if phase_started is not None:
                    timings = timings + (
                        IntelligencePhaseTiming(
                            phase=current.phase,
                            elapsed_seconds=max(0.0, now_monotonic - phase_started),
                        ),
                    )
                if status == IntelligenceJobStatus.RUNNING:
                    self._phase_started_monotonic[job_id] = now_monotonic

            if status in {IntelligenceJobStatus.COMPLETED, IntelligenceJobStatus.FAILED}:
                job_started = self._job_started_monotonic.pop(job_id, None)
                if job_started is not None:
                    total_elapsed = max(0.0, now_monotonic - job_started)
                self._phase_started_monotonic.pop(job_id, None)

            updated = replace(
                current,
                status=status,
                phase=phase,
                message=message,
                updated_at=now,
                error=error,
                phase_timings=timings,
                total_elapsed_seconds=total_elapsed,
            )
            self._jobs[job_id] = updated
            return updated

    def _log_final_timing(self, job: IntelligenceJob) -> None:
        phase_text = " ".join(
            f"{timing.phase.value}={timing.elapsed_seconds:.3f}s"
            for timing in job.phase_timings
        )
        _logger.info(
            "FSFFL intelligence refresh timing job=%s user=%s league_state=%s status=%s total=%.3fs %s",
            job.job_id,
            job.user_id,
            job.league_state_id,
            job.status.value,
            job.total_elapsed_seconds or 0.0,
            phase_text,
        )

    def _run(self, job_id: str, work: JobWork) -> None:
        _deprioritize_background_thread()
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
            failed = self._update(
                job_id,
                status=IntelligenceJobStatus.FAILED,
                phase=IntelligenceJobPhase.FAILED,
                message="Intelligence refresh failed.",
                error=f"{type(exc).__name__}: {exc}",
            )
            self._log_final_timing(failed)
            return

        completed = self._update(
            job_id,
            status=IntelligenceJobStatus.COMPLETED,
            phase=IntelligenceJobPhase.COMPLETED,
            message="Forecasts, simulation and current Value evidence are ready.",
        )
        self._log_final_timing(completed)
