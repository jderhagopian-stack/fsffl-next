from __future__ import annotations

from threading import Event

from fsffl.product.background_jobs import (
    IntelligenceJobCoordinator,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)


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
    for _ in range(200):
        current = coordinator.current("u1")
        if current is not None and current.status == IntelligenceJobStatus.COMPLETED:
            break
    current = coordinator.current("u1")
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

    for _ in range(200):
        current = coordinator.current("u1")
        if current is not None and current.status == IntelligenceJobStatus.FAILED:
            break
    current = coordinator.current("u1")
    assert current is not None
    assert current.status == IntelligenceJobStatus.FAILED
    assert current.phase == IntelligenceJobPhase.FAILED
    assert current.error == "ValueError: boom"
