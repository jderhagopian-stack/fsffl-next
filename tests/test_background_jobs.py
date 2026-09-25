from __future__ import annotations

import os
from threading import Event
from unittest.mock import patch
from time import monotonic, sleep

from fsffl.product.background_jobs import (
    IntelligenceJobCoordinator,
    IntelligenceJobInterrupted,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)


def _wait_for_status(
    coordinator: IntelligenceJobCoordinator,
    *,
    user_id: str,
    status: IntelligenceJobStatus,
    timeout: float = 2.0,
):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        current = coordinator.current(user_id)
        if current is not None and current.status == status:
            return current
        sleep(0.01)
    return coordinator.current(user_id)


def test_background_job_runs_independently_and_reports_progress() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)
    release = Event()
    started = Event()

    def work(progress) -> None:
        progress(IntelligenceJobPhase.RUNNING_SIMULATION, "Running simulation")
        started.set()
        assert release.wait(timeout=2)

    job = coordinator.start(user_id="u1", league_state_id="state-1", work=work)
    assert job.status in {IntelligenceJobStatus.QUEUED, IntelligenceJobStatus.RUNNING}
    assert started.wait(timeout=2)

    running = coordinator.current("u1")
    assert running is not None
    assert running.status == IntelligenceJobStatus.RUNNING
    assert running.phase == IntelligenceJobPhase.RUNNING_SIMULATION

    release.set()
    current = _wait_for_status(
        coordinator,
        user_id="u1",
        status=IntelligenceJobStatus.COMPLETED,
    )
    assert current is not None
    assert current.status == IntelligenceJobStatus.COMPLETED
    assert current.phase == IntelligenceJobPhase.COMPLETED


def test_same_state_does_not_launch_duplicate_active_job() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)
    release = Event()
    started = Event()

    def work(_progress) -> None:
        started.set()
        assert release.wait(timeout=2)

    first = coordinator.start(user_id="u1", league_state_id="state-1", work=work)
    assert started.wait(timeout=2)
    second = coordinator.start(user_id="u1", league_state_id="state-1", work=work)
    assert second.job_id == first.job_id
    release.set()


def test_job_failure_is_persisted_for_polling_client() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)
    finished = Event()

    def work(_progress) -> None:
        try:
            raise ValueError("boom")
        finally:
            finished.set()

    coordinator.start(user_id="u1", league_state_id="state-1", work=work)
    assert finished.wait(timeout=2)

    current = _wait_for_status(
        coordinator,
        user_id="u1",
        status=IntelligenceJobStatus.FAILED,
    )
    assert current is not None
    assert current.status == IntelligenceJobStatus.FAILED
    assert current.phase == IntelligenceJobPhase.FAILED
    assert current.error == "ValueError: boom"
    assert current.failure_phase == IntelligenceJobPhase.BUILDING_FORECASTS
    assert current.total_elapsed_seconds is not None
    assert current.total_elapsed_seconds >= 0.0
    assert current.phase_timings


def test_completed_job_records_each_runtime_phase_and_total_elapsed_time() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)

    def work(progress) -> None:
        sleep(0.01)
        progress(IntelligenceJobPhase.REFRESHING_STATE, "Refreshing state")
        sleep(0.01)
        progress(IntelligenceJobPhase.RUNNING_SIMULATION, "Running simulation")
        sleep(0.01)
        progress(IntelligenceJobPhase.BUILDING_VALUES, "Building values")
        sleep(0.01)
        progress(IntelligenceJobPhase.ATTACHING_RESULTS, "Attaching results")
        sleep(0.01)

    coordinator.start(user_id="u1", league_state_id="state-1", work=work)
    current = _wait_for_status(
        coordinator,
        user_id="u1",
        status=IntelligenceJobStatus.COMPLETED,
    )
    assert current is not None
    assert current.total_elapsed_seconds is not None
    assert current.total_elapsed_seconds >= 0.04
    assert [timing.phase for timing in current.phase_timings] == [
        IntelligenceJobPhase.BUILDING_FORECASTS,
        IntelligenceJobPhase.REFRESHING_STATE,
        IntelligenceJobPhase.RUNNING_SIMULATION,
        IntelligenceJobPhase.BUILDING_VALUES,
        IntelligenceJobPhase.ATTACHING_RESULTS,
    ]
    assert all(timing.elapsed_seconds > 0.0 for timing in current.phase_timings)


def test_background_job_lowers_only_its_dedicated_thread_priority() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)
    observed = Event()

    def work(_progress) -> None:
        observed.set()

    with patch("fsffl.product.background_jobs.get_native_id", return_value=4242), patch(
        "fsffl.product.background_jobs.os.setpriority"
    ) as setpriority:
        coordinator.start(user_id="u-priority", league_state_id="state-1", work=work)
        assert observed.wait(timeout=2)
        current = _wait_for_status(
            coordinator,
            user_id="u-priority",
            status=IntelligenceJobStatus.COMPLETED,
        )
        assert current is not None
        setpriority.assert_called_once_with(os.PRIO_PROCESS, 4242, 10)


def test_background_priority_failure_does_not_fail_intelligence_work() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)
    observed = Event()

    def work(_progress) -> None:
        observed.set()

    with patch(
        "fsffl.product.background_jobs.os.setpriority",
        side_effect=PermissionError("not permitted"),
    ):
        coordinator.start(user_id="u-priority-fail", league_state_id="state-1", work=work)
        assert observed.wait(timeout=2)
        current = _wait_for_status(
            coordinator,
            user_id="u-priority-fail",
            status=IntelligenceJobStatus.COMPLETED,
        )
        assert current is not None
        assert current.status == IntelligenceJobStatus.COMPLETED



class _LifecyclePersistence:
    def __init__(self):
        self.rows = []
    def put_artifact(self, record):
        self.rows.append(record)
    def get_latest_reusable_artifact(self, *, artifact_kind, scope_kind, scope_id, model_version):
        rows = [r for r in self.rows if r.key.artifact_kind == artifact_kind and r.key.scope_kind == scope_kind and r.key.scope_id == scope_id and r.key.model_version == model_version]
        return max(rows, key=lambda r: r.computed_at) if rows else None


def test_restart_reconciles_durable_running_job_as_interrupted() -> None:
    persistence = _LifecyclePersistence()
    first = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    release = Event()
    started = Event()
    def work(_progress) -> None:
        started.set()
        release.wait(timeout=2)
    first.start(user_id="u-restart", league_state_id="state-1", work=work)
    assert started.wait(timeout=2)
    assert first.current("u-restart").status == IntelligenceJobStatus.RUNNING

    restarted = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    recovered = restarted.current("u-restart")
    assert recovered is not None
    assert recovered.status == IntelligenceJobStatus.INTERRUPTED
    assert recovered.phase == IntelligenceJobPhase.INTERRUPTED
    assert recovered.failure_phase == IntelligenceJobPhase.BUILDING_FORECASTS
    assert recovered.error == "server_restart"
    release.set()


def test_completed_job_survives_coordinator_restart_without_recomputation() -> None:
    persistence = _LifecyclePersistence()
    first = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    first.start(user_id="u-complete", league_state_id="state-1", work=lambda _progress: None)
    completed = _wait_for_status(first, user_id="u-complete", status=IntelligenceJobStatus.COMPLETED)
    assert completed is not None

    restarted = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    recovered = restarted.current("u-complete")
    assert recovered is not None
    assert recovered.job_id == completed.job_id
    assert recovered.status == IntelligenceJobStatus.COMPLETED


def test_superseded_job_is_interrupted_not_failed() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)

    def work(_progress) -> None:
        raise IntelligenceJobInterrupted("league_switch")

    coordinator.start(user_id="u-switch", league_state_id="state-old", work=work)
    current = _wait_for_status(
        coordinator,
        user_id="u-switch",
        status=IntelligenceJobStatus.INTERRUPTED,
    )
    assert current is not None
    assert current.status == IntelligenceJobStatus.INTERRUPTED
    assert current.phase == IntelligenceJobPhase.INTERRUPTED
    assert current.error == "league_switch"


def test_failure_phase_survives_coordinator_restart() -> None:
    persistence = _LifecyclePersistence()
    first = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]

    def work(progress) -> None:
        progress(IntelligenceJobPhase.RUNNING_SIMULATION, "Running simulation")
        raise RuntimeError("simulation boom")

    first.start(user_id="u-failure-phase", league_state_id="state-1", work=work)
    failed = _wait_for_status(
        first,
        user_id="u-failure-phase",
        status=IntelligenceJobStatus.FAILED,
    )
    assert failed is not None
    assert failed.failure_phase == IntelligenceJobPhase.RUNNING_SIMULATION

    restarted = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    recovered = restarted.current("u-failure-phase")
    assert recovered is not None
    assert recovered.status == IntelligenceJobStatus.FAILED
    assert recovered.phase == IntelligenceJobPhase.FAILED
    assert recovered.failure_phase == IntelligenceJobPhase.RUNNING_SIMULATION


def test_legacy_failed_lifecycle_infers_failure_phase_from_timings() -> None:
    persistence = _LifecyclePersistence()
    from datetime import UTC, datetime
    from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord

    now = datetime.now(UTC)
    persistence.put_artifact(
        ReusableArtifactRecord(
            key=ArtifactKey(
                artifact_kind="intelligence_job_lifecycle",
                scope_kind="user",
                scope_id="u-legacy",
                input_fingerprint="legacy-failed",
                model_version="intelligence-job-lifecycle-v1",
            ),
            payload={
                "job_id": "legacy-failed",
                "user_id": "u-legacy",
                "league_state_id": "state-legacy",
                "status": "failed",
                "phase": "failed",
                "message": "Intelligence refresh failed.",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "error": "LiveForecastSourceHealthFailure: no qualifying sources",
                "phase_timings": [
                    {"phase": "building_forecasts", "elapsed_seconds": 0.5}
                ],
                "total_elapsed_seconds": 0.5,
            },
            computed_at=now,
        )
    )

    coordinator = IntelligenceJobCoordinator(
        max_workers=1,
        persistence_store=persistence,  # type: ignore[arg-type]
    )
    recovered = coordinator.current("u-legacy")

    assert recovered is not None
    assert recovered.status == IntelligenceJobStatus.FAILED
    assert recovered.phase == IntelligenceJobPhase.FAILED
    assert recovered.failure_phase == IntelligenceJobPhase.BUILDING_FORECASTS
