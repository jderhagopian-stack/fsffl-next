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

from fsffl.persistence.contracts import ArtifactKey, PersistenceStore, ReusableArtifactRecord


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
    INTERRUPTED = "interrupted"


class IntelligenceJobInterrupted(RuntimeError):
    """Signal that a running intelligence job lost write authority."""

    pass


class IntelligenceJobPhase(StrEnum):
    QUEUED = "queued"
    BUILDING_FORECASTS = "building_forecasts"
    REFRESHING_STATE = "refreshing_state"
    RUNNING_SIMULATION = "running_simulation"
    BUILDING_VALUES = "building_values"
    ATTACHING_RESULTS = "attaching_results"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


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
    failure_stage: IntelligenceJobPhase | None = None
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

    def __init__(self, *, max_workers: int = 2, persistence_store: PersistenceStore | None = None) -> None:
        self._lock = RLock()
        self._persistence = persistence_store
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
            if job_id is not None:
                return self._jobs.get(job_id)
        restored = self._restore_latest(user_id)
        if restored is None:
            return None
        if restored.status in {IntelligenceJobStatus.QUEUED, IntelligenceJobStatus.RUNNING}:
            restored = replace(
                restored,
                status=IntelligenceJobStatus.INTERRUPTED,
                phase=IntelligenceJobPhase.INTERRUPTED,
                message="Intelligence refresh was interrupted by a server restart. Last-good intelligence remains active; start a new refresh when ready.",
                updated_at=datetime.now(UTC),
                error="server_restart",
            )
            self._persist(restored)
        with self._lock:
            self._jobs[restored.job_id] = restored
            self._current_by_user[user_id] = restored.job_id
        return restored

    def _persist(self, job: IntelligenceJob) -> None:
        if self._persistence is None:
            return
        try:
            self._persistence.put_artifact(
                ReusableArtifactRecord(
                    key=ArtifactKey(
                        artifact_kind="intelligence_job_lifecycle",
                        scope_kind="user",
                        scope_id=job.user_id,
                        input_fingerprint=job.job_id,
                        model_version="intelligence-job-lifecycle-v1",
                    ),
                    payload={
                        "job_id": job.job_id,
                        "user_id": job.user_id,
                        "league_state_id": job.league_state_id,
                        "status": job.status.value,
                        "phase": job.phase.value,
                        "message": job.message,
                        "created_at": job.created_at.isoformat(),
                        "updated_at": job.updated_at.isoformat(),
                        "error": job.error,
                        "failure_stage": job.failure_stage.value if job.failure_stage is not None else None,
                        "phase_timings": [{"phase": t.phase.value, "elapsed_seconds": t.elapsed_seconds} for t in job.phase_timings],
                        "total_elapsed_seconds": job.total_elapsed_seconds,
                    },
                    computed_at=job.updated_at,
                )
            )
        except Exception as exc:
            _logger.warning("FSFFL intelligence lifecycle persistence failed job=%s error=%s", job.job_id, exc)

    def _restore_latest(self, user_id: str) -> IntelligenceJob | None:
        if self._persistence is None:
            return None
        try:
            record = self._persistence.get_latest_reusable_artifact(
                artifact_kind="intelligence_job_lifecycle", scope_kind="user", scope_id=user_id,
                model_version="intelligence-job-lifecycle-v1",
            )
            if record is None:
                return None
            p = record.payload
            return IntelligenceJob(
                job_id=str(p["job_id"]), user_id=str(p["user_id"]), league_state_id=str(p["league_state_id"]),
                status=IntelligenceJobStatus(str(p["status"])), phase=IntelligenceJobPhase(str(p["phase"])),
                message=str(p["message"]), created_at=datetime.fromisoformat(str(p["created_at"])),
                updated_at=datetime.fromisoformat(str(p["updated_at"])), error=p.get("error"),
                failure_stage=(
                    IntelligenceJobPhase(str(p["failure_stage"]))
                    if p.get("failure_stage") is not None
                    else None
                ),
                phase_timings=tuple(IntelligencePhaseTiming(phase=IntelligenceJobPhase(str(t["phase"])), elapsed_seconds=float(t["elapsed_seconds"])) for t in p.get("phase_timings", ())),
                total_elapsed_seconds=(float(p["total_elapsed_seconds"]) if p.get("total_elapsed_seconds") is not None else None),
            )
        except Exception as exc:
            _logger.warning("FSFFL intelligence lifecycle restore failed user=%s error=%s", user_id, exc)
            return None

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
            self._persist(job)
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
        failure_stage: IntelligenceJobPhase | None = None,
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

            if status in {IntelligenceJobStatus.COMPLETED, IntelligenceJobStatus.FAILED, IntelligenceJobStatus.INTERRUPTED}:
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
                failure_stage=failure_stage,
                phase_timings=timings,
                total_elapsed_seconds=total_elapsed,
            )
            self._jobs[job_id] = updated
            self._persist(updated)
            if current.status != updated.status or current.phase != updated.phase:
                _logger.info(
                    "FSFFL intelligence lifecycle transition job=%s user=%s state=%s status=%s phase=%s",
                    updated.job_id,
                    updated.user_id,
                    updated.league_state_id,
                    updated.status.value,
                    updated.phase.value,
                )
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
        except IntelligenceJobInterrupted as exc:
            interrupted = self._update(
                job_id,
                status=IntelligenceJobStatus.INTERRUPTED,
                phase=IntelligenceJobPhase.INTERRUPTED,
                message="Intelligence refresh was superseded by a league switch. Last-good intelligence remains active.",
                error=str(exc) or "league_switch",
            )
            self._log_final_timing(interrupted)
            return
        except Exception as exc:
            current = self.get(job_id)
            failure_stage = (
                current.phase
                if current is not None and current.phase not in {
                    IntelligenceJobPhase.FAILED,
                    IntelligenceJobPhase.INTERRUPTED,
                    IntelligenceJobPhase.COMPLETED,
                }
                else None
            )
            failed = self._update(
                job_id,
                status=IntelligenceJobStatus.FAILED,
                phase=IntelligenceJobPhase.FAILED,
                message="Intelligence refresh failed.",
                error=f"{type(exc).__name__}: {exc}",
                failure_stage=failure_stage,
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
