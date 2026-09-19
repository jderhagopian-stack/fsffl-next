from time import monotonic, sleep

from fsffl.behavioral.service import BehavioralSyncResult
from fsffl.product.behavioral_runtime import BehavioralRuntimeCoordinator, BehavioralRuntimeStatus
from tests.test_state_foundation import make_state


def test_behavioral_runtime_runs_off_request_path_and_attaches_result() -> None:
    state = make_state()

    def work(league_state, sleeper_league_external_id):
        assert league_state.state_id == state.state_id
        assert sleeper_league_external_id == "league-123"
        return BehavioralSyncResult(
            league_family_id="sleeper-family:oldest",
            profile_count=0,
            total_event_count=0,
            inserted_event_count=0,
            reused_historical_league_ids=("oldest",),
            scanned_league_ids=("league-123",),
            current_owner_by_roster=((1, "owner-a"),),
            profiles=(),
        )

    coordinator = BehavioralRuntimeCoordinator(work=work, max_workers=1)
    started = coordinator.start(
        user_id="user",
        league_state=state,
        sleeper_league_external_id="league-123",
    )
    assert started.status == BehavioralRuntimeStatus.RUNNING

    deadline = monotonic() + 2.0
    record = coordinator.current("user")
    while record.status == BehavioralRuntimeStatus.RUNNING and monotonic() < deadline:
        sleep(0.01)
        record = coordinator.current("user")

    assert record.status == BehavioralRuntimeStatus.READY
    assert record.result is not None
    assert record.result.league_family_id == "sleeper-family:oldest"


def test_behavioral_runtime_records_failure_without_breaking_league_runtime() -> None:
    state = make_state()

    def fail(_league_state, _league_id):
        raise RuntimeError("provider unavailable")

    coordinator = BehavioralRuntimeCoordinator(work=fail, max_workers=1)
    coordinator.start(user_id="user", league_state=state, sleeper_league_external_id="x")
    deadline = monotonic() + 2.0
    record = coordinator.current("user")
    while record.status == BehavioralRuntimeStatus.RUNNING and monotonic() < deadline:
        sleep(0.01)
        record = coordinator.current("user")

    assert record.status == BehavioralRuntimeStatus.FAILED
    assert record.error == "RuntimeError: provider unavailable"
