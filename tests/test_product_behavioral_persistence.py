from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.service import BehavioralSyncResult
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.product.behavioral_runtime import BehavioralRuntimeCoordinator, BehavioralRuntimeStatus
from tests.test_state_foundation import make_state


def _profile() -> OwnerBehaviorProfile:
    return OwnerBehaviorProfile(
        league_family_id="sleeper-family:oldest",
        owner_id="owner-a",
        as_of=datetime(2026, 9, 9, tzinfo=UTC),
        event_count=2,
        trade_count=1,
        waiver_count=1,
        consolidation_trade_count=1,
        acquired_positions={"WR": 1},
    )


def _seed_durable_context(store: BehavioralIntelligenceStore) -> None:
    store.put_profiles((_profile(),))
    store.put_runtime_context(
        user_id="user",
        league_state_id="stored-state",
        sleeper_league_external_id="league-123",
        league_family_id="sleeper-family:oldest",
        current_owner_by_roster=((1, "owner-a"),),
    )


def _wait(coordinator: BehavioralRuntimeCoordinator) -> None:
    deadline = monotonic() + 2.0
    record = coordinator.current("user")
    while record.status == BehavioralRuntimeStatus.RUNNING and monotonic() < deadline:
        sleep(0.01)
        record = coordinator.current("user")


def test_restart_hydrates_durable_observed_profiles_without_in_memory_job(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    _seed_durable_context(store)

    restarted = BehavioralRuntimeCoordinator(store_factory=lambda: store, max_workers=1)
    record = restarted.current("user")

    assert record.status == BehavioralRuntimeStatus.READY
    assert record.result is not None
    assert record.result.league_family_id == "sleeper-family:oldest"
    assert record.result.profile_count == 1
    assert record.result.profiles[0].owner_id == "owner-a"
    assert record.result.current_owner_by_roster == ((1, "owner-a"),)
    assert record.result.inserted_event_count == 0


def test_active_rebuild_keeps_durable_observed_profiles_readable(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    _seed_durable_context(store)
    state = make_state()

    def slow_work(_league_state, _league_id):
        sleep(0.15)
        return BehavioralSyncResult(
            league_family_id="sleeper-family:oldest",
            profile_count=1,
            total_event_count=2,
            inserted_event_count=0,
            reused_historical_league_ids=(),
            scanned_league_ids=("league-123",),
            current_owner_by_roster=((1, "owner-a"),),
            profiles=(_profile(),),
        )

    coordinator = BehavioralRuntimeCoordinator(
        work=slow_work,
        store_factory=lambda: store,
        max_workers=1,
    )
    started = coordinator.start(
        user_id="user",
        league_state=state,
        sleeper_league_external_id="league-123",
    )

    assert started.status == BehavioralRuntimeStatus.RUNNING
    assert started.result is not None
    assert started.result.profiles[0].owner_id == "owner-a"
    _wait(coordinator)
    assert coordinator.current("user").status == BehavioralRuntimeStatus.READY


def test_active_rebuild_without_durable_history_does_not_fabricate_profiles(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    state = make_state()

    def slow_work(_league_state, _league_id):
        sleep(0.15)
        return BehavioralSyncResult(
            league_family_id="sleeper-family:oldest",
            profile_count=0,
            total_event_count=0,
            inserted_event_count=0,
            reused_historical_league_ids=(),
            scanned_league_ids=("league-123",),
            current_owner_by_roster=(),
            profiles=(),
        )

    coordinator = BehavioralRuntimeCoordinator(
        work=slow_work,
        store_factory=lambda: store,
        max_workers=1,
    )
    started = coordinator.start(
        user_id="user",
        league_state=state,
        sleeper_league_external_id="league-123",
    )

    assert started.status == BehavioralRuntimeStatus.RUNNING
    assert started.result is None
    _wait(coordinator)


def test_failed_rebuild_without_durable_history_is_unavailable(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    state = make_state()

    def fail(_league_state, _league_id):
        raise RuntimeError("provider unavailable")

    coordinator = BehavioralRuntimeCoordinator(
        work=fail,
        store_factory=lambda: store,
        max_workers=1,
    )
    coordinator.start(
        user_id="user",
        league_state=state,
        sleeper_league_external_id="league-123",
    )
    _wait(coordinator)

    record = coordinator.current("user")
    assert record.status == BehavioralRuntimeStatus.FAILED
    assert record.result is None
    assert record.error == "RuntimeError: provider unavailable"


def test_failed_refresh_preserves_durable_observed_history_but_not_decision_use(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    _seed_durable_context(store)
    state = make_state()

    def fail(_league_state, _league_id):
        raise RuntimeError("provider unavailable")

    coordinator = BehavioralRuntimeCoordinator(
        work=fail,
        store_factory=lambda: store,
        max_workers=1,
    )
    coordinator.start(
        user_id="user",
        league_state=state,
        sleeper_league_external_id="league-123",
    )
    _wait(coordinator)

    record = coordinator.current("user")
    assert record.status == BehavioralRuntimeStatus.READY
    assert record.result is not None
    assert record.error == "RuntimeError: provider unavailable"
    assert coordinator.profile_for_team("user", state, state.teams[0].team_id) is None


def test_runtime_context_round_trips_without_inference_fields(tmp_path: Path) -> None:
    store = BehavioralIntelligenceStore(tmp_path / "behavior.sqlite3")
    _seed_durable_context(store)

    context = store.load_runtime_context("user")

    assert context == {
        "league_state_id": "stored-state",
        "sleeper_league_external_id": "league-123",
        "league_family_id": "sleeper-family:oldest",
        "current_owner_by_roster": ((1, "owner-a"),),
    }
    assert "acceptance_probability" not in context
    assert "team_owner_adjusted_value" not in context
    assert "preference" not in context
