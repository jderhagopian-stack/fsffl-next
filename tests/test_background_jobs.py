from __future__ import annotations

import os
from concurrent.futures import Future

import pytest
from threading import Event, Thread
from unittest.mock import patch
from time import monotonic, sleep

from fsffl.product.background_jobs import (
    IntelligenceJobCoordinator,
    IntelligenceJobBusy,
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


def test_state_sync_checkpoints_new_identity_for_restart_recovery() -> None:
    persistence = _LifecyclePersistence()
    first = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    release = Event()
    started = Event()

    def work(_progress) -> None:
        started.set()
        release.wait(timeout=2)

    first.start(user_id="u-state-checkpoint", league_state_id="state-before-sync", work=work)
    assert started.wait(timeout=2)
    checkpointed = first.update_current_league_state_id(
        user_id="u-state-checkpoint",
        expected_state_id="state-before-sync",
        league_state_id="state-after-sync",
    )
    assert checkpointed is not None
    assert checkpointed.league_state_id == "state-after-sync"

    restarted = IntelligenceJobCoordinator(max_workers=1, persistence_store=persistence)  # type: ignore[arg-type]
    recovered = restarted.current("u-state-checkpoint")
    assert recovered is not None
    assert recovered.status == IntelligenceJobStatus.INTERRUPTED
    assert recovered.league_state_id == "state-after-sync"
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



def test_background_job_uses_work_supplied_truthful_completion_message() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1)

    def work(progress) -> str:
        progress(IntelligenceJobPhase.RUNNING_SIMULATION, "Evaluating simulation authority")
        progress(IntelligenceJobPhase.BUILDING_VALUES, "Building values")
        return (
            "Governed Forecast and current Value evidence are ready. "
            "Simulation remains unavailable under current Forecast authority."
        )

    coordinator.start(user_id="u-partial", league_state_id="state-partial", work=work)
    current = _wait_for_status(
        coordinator,
        user_id="u-partial",
        status=IntelligenceJobStatus.COMPLETED,
    )
    assert current is not None
    assert current.message == (
        "Governed Forecast and current Value evidence are ready. "
        "Simulation remains unavailable under current Forecast authority."
    )



class _BlockingLifecyclePersistence(_LifecyclePersistence):
    def __init__(self, block_user: str):
        super().__init__()
        self.block_user = block_user
        self.entered = Event()
        self.release = Event()
        self._blocked_once = False

    def put_artifact(self, record):
        super().put_artifact(record)
        if (
            not self._blocked_once
            and record.payload.get("user_id") == self.block_user
        ):
            self._blocked_once = True
            self.entered.set()
            if not self.release.wait(timeout=2.0):
                raise RuntimeError("test lifecycle persistence release timed out")


def test_one_users_slow_job_persistence_does_not_block_another_users_start() -> None:
    persistence = _BlockingLifecyclePersistence("user-a")
    coordinator = IntelligenceJobCoordinator(
        max_workers=2,
        persistence_store=persistence,  # type: ignore[arg-type]
    )
    errors = []
    a_done = Event()
    b_done = Event()

    def start_a() -> None:
        try:
            coordinator.start(
                user_id="user-a",
                league_state_id="state-a",
                work=lambda _progress: None,
            )
        except Exception as exc:
            errors.append(exc)
        finally:
            a_done.set()

    def start_b() -> None:
        try:
            coordinator.start(
                user_id="user-b",
                league_state_id="state-b",
                work=lambda _progress: None,
            )
        except Exception as exc:
            errors.append(exc)
        finally:
            b_done.set()

    a_thread = Thread(target=start_a, name="job-start-a")
    a_thread.start()
    assert persistence.entered.wait(timeout=1.0)

    b_thread = Thread(target=start_b, name="job-start-b")
    b_thread.start()
    assert b_done.wait(timeout=0.5)

    persistence.release.set()
    a_thread.join(timeout=2.0)
    b_thread.join(timeout=2.0)
    assert not a_thread.is_alive()
    assert not b_thread.is_alive()
    assert a_done.is_set()
    assert errors == []



def test_superseded_older_job_cannot_replace_newer_durable_current_job() -> None:
    persistence = _LifecyclePersistence()
    coordinator = IntelligenceJobCoordinator(
        max_workers=2,
        persistence_store=persistence,  # type: ignore[arg-type]
    )
    old_started = Event()
    release_old = Event()

    def old_work(_progress) -> None:
        old_started.set()
        assert release_old.wait(timeout=2.0)
        raise IntelligenceJobInterrupted("league_switch")

    old = coordinator.start(
        user_id="u-overlap",
        league_state_id="state-old",
        work=old_work,
    )
    assert old_started.wait(timeout=1.0)

    new = coordinator.start(
        user_id="u-overlap",
        league_state_id="state-new",
        work=lambda _progress: None,
    )
    completed = _wait_for_status(
        coordinator,
        user_id="u-overlap",
        status=IntelligenceJobStatus.COMPLETED,
    )
    assert completed is not None
    assert completed.job_id == new.job_id

    release_old.set()
    deadline = monotonic() + 2.0
    while monotonic() < deadline:
        old_row = coordinator.get(old.job_id)
        if old_row is not None and old_row.status == IntelligenceJobStatus.INTERRUPTED:
            break
        sleep(0.01)
    assert old_row is not None
    assert old_row.status == IntelligenceJobStatus.INTERRUPTED

    restarted = IntelligenceJobCoordinator(
        max_workers=1,
        persistence_store=persistence,  # type: ignore[arg-type]
    )
    recovered = restarted.current("u-overlap")
    assert recovered is not None
    assert recovered.job_id == new.job_id
    assert recovered.status == IntelligenceJobStatus.COMPLETED


def test_bounded_admission_rejects_burst_without_recording_unbounded_jobs() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1, max_pending_jobs=1)
    started = Event()
    release = Event()
    executed = []

    def blocked(_progress) -> None:
        started.set()
        assert release.wait(timeout=3.0)

    first = coordinator.start(user_id="burst-1", league_state_id="state-1", work=blocked)
    assert started.wait(timeout=2.0)
    second = coordinator.start(
        user_id="burst-2",
        league_state_id="state-2",
        work=lambda _progress: executed.append("second"),
    )
    assert second.status == IntelligenceJobStatus.QUEUED

    # Coalescing works even at capacity and does not consume another slot.
    joined = coordinator.start(
        user_id="burst-1",
        league_state_id="state-1",
        work=lambda _progress: executed.append("duplicate"),
    )
    assert joined.job_id == first.job_id

    for i in range(20):
        with pytest.raises(IntelligenceJobBusy):
            coordinator.start(
                user_id=f"overflow-{i}",
                league_state_id=f"state-{i}",
                work=lambda _progress: executed.append("overflow"),
            )
    assert len(coordinator._jobs) == 2
    assert executed == []

    release.set()
    assert _wait_for_status(
        coordinator, user_id="burst-2", status=IntelligenceJobStatus.COMPLETED,
        timeout=3.0,
    ).status == IntelligenceJobStatus.COMPLETED
    assert executed == ["second"]

    # A completed Future releases admission so a new user can retry.
    retried = coordinator.start(
        user_id="overflow-0",
        league_state_id="state-0",
        work=lambda _progress: None,
    )
    assert _wait_for_status(
        coordinator, user_id="overflow-0", status=IntelligenceJobStatus.COMPLETED,
    ).job_id == retried.job_id


def test_bounded_admission_releases_slot_after_failed_and_interrupted_work() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1, max_pending_jobs=0)
    for user_id, exception, status in [
        ("failure", ValueError("failure"), IntelligenceJobStatus.FAILED),
        ("interrupted", IntelligenceJobInterrupted("switch"), IntelligenceJobStatus.INTERRUPTED),
    ]:
        def work(_progress, exc=exception) -> None:
            raise exc

        coordinator.start(user_id=user_id, league_state_id="state", work=work)
        assert _wait_for_status(
            coordinator, user_id=user_id, status=status,
        ).status == status

    retry = coordinator.start(
        user_id="after-failure", league_state_id="state", work=lambda _progress: None,
    )
    assert _wait_for_status(
        coordinator, user_id="after-failure", status=IntelligenceJobStatus.COMPLETED,
    ).job_id == retry.job_id


def test_cancelled_pending_future_releases_capacity_and_marks_interrupted() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1, max_pending_jobs=0)
    pending: Future[None] = Future()
    with patch.object(coordinator._executor, "submit", return_value=pending):
        job = coordinator.start(
            user_id="cancelled", league_state_id="state", work=lambda _progress: None,
        )
        with pytest.raises(IntelligenceJobBusy):
            coordinator.start(
                user_id="overflow", league_state_id="state", work=lambda _progress: None,
            )
        assert pending.cancel()
    interrupted = coordinator.get(job.job_id)
    assert interrupted is not None
    assert interrupted.status == IntelligenceJobStatus.INTERRUPTED
    assert interrupted.error == "job_cancelled"
    retry = coordinator.start(
        user_id="after-cancel", league_state_id="state", work=lambda _progress: None,
    )
    assert _wait_for_status(
        coordinator, user_id="after-cancel", status=IntelligenceJobStatus.COMPLETED,
    ).job_id == retry.job_id


def test_executor_submit_failure_releases_admission_and_preserves_failure_status() -> None:
    coordinator = IntelligenceJobCoordinator(max_workers=1, max_pending_jobs=0)
    with patch.object(
        coordinator._executor, "submit", side_effect=RuntimeError("executor shutdown"),
    ):
        with pytest.raises(RuntimeError, match="executor shutdown"):
            coordinator.start(
                user_id="submit-failed", league_state_id="state", work=lambda _progress: None,
            )
    failed = coordinator.current("submit-failed")
    assert failed is not None
    assert failed.status == IntelligenceJobStatus.FAILED
    assert failed.error == "executor_submit_failed"
    retry = coordinator.start(
        user_id="after-submit-failure",
        league_state_id="state",
        work=lambda _progress: None,
    )
    assert _wait_for_status(
        coordinator, user_id="after-submit-failure", status=IntelligenceJobStatus.COMPLETED,
    ).job_id == retry.job_id
