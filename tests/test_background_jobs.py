from __future__ import annotations

from threading import Event
from time import monotonic, sleep

from fsffl.product.background_jobs import (
    IntelligenceJobCoordinator,
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
