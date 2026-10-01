from __future__ import annotations

import gc
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from time import sleep
import weakref

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product import resource_coordinator as resource_module
from fsffl.product.background_jobs import (
    IntelligenceJob,
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
from fsffl.product.hosted_connect import (
    LeagueConnectCoordinator,
    LeagueConnectStatus,
    install_hosted_connect_routes,
)
from fsffl.product.intrinsic_background import ShapleyIntrinsicBackgroundCoordinator
from fsffl.product.league_value_lens_routes import install_league_value_lens_routes
from fsffl.product.market_economics_cache import make_cached_candidate_economics
from fsffl.product.market_progressive_enrichment import (
    MarketDecisionEnrichmentCoordinator,
    MarketEnrichmentStatus,
)
from fsffl.product.opportunity_search_cache import make_cached_opportunity_search
from fsffl.product.opportunity_workspace_cache import make_cached_opportunity_workspace
from fsffl.product.player_intelligence_routes import (
    PlayerHistoryBackgroundCoordinator,
    PlayerHistoryBuildStatus,
    PlayerHistoryCapacityError,
)
from fsffl.product.resource_coordinator import (
    DEFAULT_MEMORY_LIMIT_BYTES,
    HeavyWorkCoordinator,
    ResourceTransition,
    StateResourceBoundary,
)
from fsffl.product.runtime import (
    PrivateBetaRuntimeStore,
    UserRuntimeContext,
    league_material_fingerprint,
)
from fsffl.product.webapp import create_app
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _state(
    external_id: str,
    *,
    team_suffix: str = "",
    minute: int = 0,
) -> LeagueState:
    league_id = f"sleeper:{external_id}"
    return LeagueState(
        league=League(
            league_id=league_id,
            name=f"League {external_id}",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=datetime(2026, 9, 29, 12, minute, tzinfo=UTC),
        teams=(
            Team(
                team_id=f"{external_id}:a",
                league_id=league_id,
                display_name=f"Alpha{team_suffix}",
            ),
            Team(
                team_id=f"{external_id}:b",
                league_id=league_id,
                display_name="Beta",
            ),
        ),
        team_states=(
            TeamState(team_id=f"{external_id}:a", roster=()),
            TeamState(team_id=f"{external_id}:b", roster=()),
        ),
        players=(),
        player_states=(),
    )


def _runtime(user_id: str, state: LeagueState) -> UserRuntimeContext:
    return UserRuntimeContext(
        user_id=user_id,
        league_state=state,
        selected_team_id=state.teams[0].team_id,
    )


def _wait_connect(
    coordinator: LeagueConnectCoordinator,
    user_id: str = "local-beta-user",
) -> None:
    import time

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        current = coordinator.current(user_id)
        if current is not None and current.status in {
            LeagueConnectStatus.COMPLETED,
            LeagueConnectStatus.FAILED,
        }:
            assert current.status == LeagueConnectStatus.COMPLETED, current.error
            return
        time.sleep(0.01)
    raise AssertionError("background connect did not complete")


def test_heavy_work_telemetry_is_bounded_and_non_identifying(monkeypatch) -> None:
    monkeypatch.setattr(resource_module, "current_rss_bytes", lambda: 100)
    monkeypatch.setattr(resource_module, "process_peak_rss_bytes", lambda: 120)
    coordinator = HeavyWorkCoordinator(
        max_waiters=1,
        memory_limit_bytes=DEFAULT_MEMORY_LIMIT_BYTES,
    )
    raw_key = "jimmy:league:team:request"

    with coordinator.claim(kind="forecast", key=raw_key):
        active = coordinator.snapshot()
        assert active.active_key is not None
        assert active.active_key != raw_key
        assert active.active_key.startswith("sha256:")
        assert raw_key not in str(active.__dict__)

    snapshot = coordinator.snapshot()
    assert len(snapshot.recent_phase_memory) == 1
    assert raw_key not in str(snapshot.__dict__)
    assert snapshot.recent_phase_memory[0]["key"].startswith("sha256:")


def test_resource_boundary_repeated_a_b_a_releases_prior_objects_and_is_bounded(
    monkeypatch,
) -> None:
    class Box:
        def __init__(self, label: str) -> None:
            self.label = label
            self.payload = bytearray(128 * 1024)

    holder: dict[str, Box] = {"user-a": Box("initial-a")}
    fake_rss = lambda: 10_000_000 + len(holder) * 1_000_000
    monkeypatch.setattr(resource_module, "current_rss_bytes", fake_rss)
    monkeypatch.setattr(
        resource_module,
        "release_unused_process_memory",
        lambda *, label: {
            "label": label,
            "before_rss_bytes": fake_rss(),
            "after_rss_bytes": fake_rss(),
            "released_rss_bytes": 0,
            "gc_collected": 0,
            "malloc_trim": True,
            "trim_error": None,
        },
    )

    def clear_user(transition: ResourceTransition) -> int:
        return 1 if holder.pop(transition.user_id, None) is not None else 0

    boundary = StateResourceBoundary(
        clearers=(("execution", clear_user),),
        max_events=16,
    )
    old_refs: list[weakref.ReferenceType[Box]] = []
    previous_league = "sleeper:a"
    previous_state = "a:0"

    for index in range(30):
        old_refs.append(weakref.ref(holder["user-a"]))
        next_league = "sleeper:b" if index % 2 == 0 else "sleeper:a"
        next_state = f"{next_league}:{index + 1}"
        result = boundary.apply(
            ResourceTransition(
                user_id="user-a",
                reason="repeat_switch",
                previous_league_id=previous_league,
                previous_state_id=previous_state,
                previous_team_id="team:a",
                next_league_id=next_league,
                next_state_id=next_state,
                next_team_id="team:b",
            )
        )
        assert result["status"] == "released"
        assert holder == {}
        holder["user-a"] = Box(next_state)
        previous_league = next_league
        previous_state = next_state

    gc.collect()
    assert all(ref() is None for ref in old_refs)
    events = boundary.snapshot()
    assert len(events) == 16
    assert all(item["after_rss_bytes"] <= item["before_rss_bytes"] for item in events)
    assert "user-a" not in str(events)
    assert all(str(item["identity_fingerprint"]).startswith("sha256:") for item in events)


def test_market_execution_caches_clear_only_transitioning_user() -> None:
    state_a = _state("a")
    state_b = _state("b")
    runtime_a = _runtime("user-a", state_a)
    runtime_b = _runtime("user-b", state_b)

    economics_calls = {"user-a": 0, "user-b": 0}

    def evaluator(runtime, row, **_kwargs):
        economics_calls[runtime.user_id] += 1
        return {**row, "economics": {"net": economics_calls[runtime.user_id]}}

    economics = make_cached_candidate_economics(evaluator)
    row = {
        "counterparty_team_id": "other",
        "send": ({"asset_ref": "player:1"},),
        "receive": ({"asset_ref": "player:2"},),
    }
    economics(runtime_a, row)
    economics(runtime_b, row)
    economics(runtime_a, row)
    economics(runtime_b, row)
    assert economics_calls == {"user-a": 1, "user-b": 1}
    assert economics.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    economics(runtime_b, row)
    economics(runtime_a, row)
    assert economics_calls == {"user-a": 2, "user-b": 1}

    search_calls = {"user-a": 0, "user-b": 0}

    def search_builder(runtime, _browser, _cardinal):
        search_calls[runtime.user_id] += 1
        return [{"user": runtime.user_id, "call": search_calls[runtime.user_id]}]

    search = make_cached_opportunity_search(search_builder)
    search(runtime_a, object(), {})
    search(runtime_b, object(), {})
    search(runtime_a, object(), {})
    search(runtime_b, object(), {})
    assert search_calls == {"user-a": 1, "user-b": 1}
    assert search.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    search(runtime_b, object(), {})
    search(runtime_a, object(), {})
    assert search_calls == {"user-a": 2, "user-b": 1}

    workspace_calls = {"user-a": 0, "user-b": 0}

    def workspace_builder(runtime, **_kwargs):
        workspace_calls[runtime.user_id] += 1
        return {"user": runtime.user_id, "call": workspace_calls[runtime.user_id]}

    workspace = make_cached_opportunity_workspace(workspace_builder)
    workspace(runtime_a)
    workspace(runtime_b)
    workspace(runtime_a)
    workspace(runtime_b)
    assert workspace_calls == {"user-a": 1, "user-b": 1}
    assert workspace.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    workspace(runtime_b)
    workspace(runtime_a)
    assert workspace_calls == {"user-a": 2, "user-b": 1}



def test_prior_published_market_activity_cannot_repopulate_released_execution_scope() -> None:
    state_a = _state("a")
    runtime_a = _runtime("user-a", state_a)
    retention_allowed = {"user-a": True}

    def retain(runtime) -> bool:
        return retention_allowed.get(runtime.user_id, True)

    economics_calls = 0

    def evaluator(runtime, row, **_kwargs):
        nonlocal economics_calls
        economics_calls += 1
        return {**row, "economics": {"net": economics_calls}}

    economics = make_cached_candidate_economics(
        evaluator,
        retention_validator=retain,
    )
    row = {
        "counterparty_team_id": "other",
        "send": ({"asset_ref": "player:1"},),
        "receive": ({"asset_ref": "player:2"},),
    }
    economics(runtime_a, row)
    assert economics.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    retention_allowed["user-a"] = False
    economics(runtime_a, row)
    economics(runtime_a, row)
    assert economics_calls == 3
    assert economics.clear_user_cache("user-a") == 0  # type: ignore[attr-defined]

    search_calls = 0

    def search_builder(runtime, _browser, _cardinal):
        nonlocal search_calls
        search_calls += 1
        return [{"call": search_calls}]

    search = make_cached_opportunity_search(
        search_builder,
        retention_validator=retain,
    )
    retention_allowed["user-a"] = True
    search(runtime_a, object(), {})
    assert search.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    retention_allowed["user-a"] = False
    search(runtime_a, object(), {})
    search(runtime_a, object(), {})
    assert search_calls == 3
    assert search.clear_user_cache("user-a") == 0  # type: ignore[attr-defined]

    workspace_calls = 0

    def workspace_builder(runtime, **_kwargs):
        nonlocal workspace_calls
        workspace_calls += 1
        return {"call": workspace_calls}

    workspace = make_cached_opportunity_workspace(
        workspace_builder,
        retention_validator=retain,
    )
    retention_allowed["user-a"] = True
    workspace(runtime_a)
    assert workspace.clear_user_cache("user-a") == 1  # type: ignore[attr-defined]
    retention_allowed["user-a"] = False
    workspace(runtime_a)
    workspace(runtime_a)
    assert workspace_calls == 3
    assert workspace.clear_user_cache("user-a") == 0  # type: ignore[attr-defined]


def test_overlapping_b_then_c_activation_serializes_cleanup_with_state_ownership() -> None:
    state_a = _state("a")
    state_b = _state("b")
    state_c = _state("c")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("user-a", state_a)
    b_boundary_entered = Event()
    release_b_boundary = Event()
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", str(transition.next_league_id)))
        if transition.next_league_id == state_b.league.league_id:
            b_boundary_entered.set()
            assert release_b_boundary.wait(timeout=2.0)
        return {"status": "released"}

    app = create_app(
        runtime_store=store,
        state_loader=lambda external_id: {
            "b": state_b,
            "c": state_c,
        }[external_id],
        state_resource_boundary=boundary,
    )
    errors: list[Exception] = []

    def activate(state: LeagueState, label: str) -> None:
        try:
            result = app.state.activate_state_with_resource_boundary(
                "user-a",
                state,
                reason=label,
            )
            assert result is not None
            events.append(("done", result.league_state.league.league_id))
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    b_thread = Thread(target=lambda: activate(state_b, "b-transition"))
    c_thread = Thread(target=lambda: activate(state_c, "c-transition"))
    b_thread.start()
    assert b_boundary_entered.wait(timeout=1.0)

    c_thread.start()
    sleep(0.05)
    assert c_thread.is_alive()
    assert store.get("user-a").league_state.state_id == state_b.state_id

    release_b_boundary.set()
    b_thread.join(timeout=2.0)
    c_thread.join(timeout=2.0)
    assert not b_thread.is_alive()
    assert not c_thread.is_alive()
    assert errors == []
    assert store.get("user-a").league_state.state_id == state_c.state_id
    assert events == [
        ("boundary", "sleeper:b"),
        ("done", "sleeper:b"),
        ("boundary", "sleeper:c"),
        ("done", "sleeper:c"),
    ]


def test_intrinsic_restore_drops_result_when_boundary_epoch_advances() -> None:
    state_a = _state("a")
    context = _runtime("user-a", state_a)
    restore_entered = Event()
    release_restore = Event()
    contract = SimpleNamespace(estimates=())

    class BlockingLoader:
        forecast_model_version = "fixture-v1"

        def restore_compatible(self, _context):
            restore_entered.set()
            assert release_restore.wait(timeout=2.0)
            return contract

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        BlockingLoader(),
        max_workers=1,
        forecast_coordinate_resolver=lambda _context: "fixture-v1",
        intrinsic_input_fingerprint_resolver=lambda _context: "fixture-input",
    )
    result: dict[str, object] = {}

    def restore() -> None:
        result["record"] = coordinator.restore_compatible(context)

    thread = Thread(target=restore)
    thread.start()
    assert restore_entered.wait(timeout=1.0)
    coordinator.clear_user("user-a")
    release_restore.set()
    thread.join(timeout=2.0)

    assert not thread.is_alive()
    assert result["record"] is None
    assert coordinator.current(context) is None




def test_stale_intrinsic_context_cannot_reacquire_execution_after_boundary() -> None:
    state_a = _state("a")
    context = _runtime("user-a", state_a)
    loader_calls = 0
    owned = {"state_id": "replacement-state"}

    class Loader:
        forecast_model_version = "fixture-v1"

        def intrinsic_input_fingerprint(self, _context):
            nonlocal loader_calls
            loader_calls += 1
            return "fixture-input"

        def __call__(self, _context):
            raise AssertionError("stale Intrinsic loader must not run")

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        Loader(),
        max_workers=1,
        ownership_validator=lambda candidate: (
            candidate.league_state is not None
            and candidate.league_state.state_id == owned["state_id"]
        ),
    )

    from fsffl.product.intrinsic_background import IntrinsicBuildSuperseded

    try:
        coordinator.request(context)
    except IntrinsicBuildSuperseded:
        pass
    else:
        raise AssertionError("stale Intrinsic context must be rejected")

    assert loader_calls == 0
    assert coordinator.current(context) is None


def test_market_enrichment_rejects_released_prior_state_without_retaining_record() -> None:
    valid = {"allowed": False}
    work_calls = 0

    def identity_validator(_user_id: str, _state_id: str, _team_id: str) -> bool:
        return valid["allowed"]

    def work():
        nonlocal work_calls
        work_calls += 1
        return {"heavy": bytearray(64 * 1024)}

    coordinator = MarketDecisionEnrichmentCoordinator(
        heavy_work_coordinator=None,
        identity_validator=identity_validator,
        max_workers=1,
    )
    record = coordinator.start(
        user_id="user-a",
        league_state_id="state-a",
        focal_team_id="team-a",
        request_key="prior-market",
        work=work,
    )

    assert record.status == MarketEnrichmentStatus.INTERRUPTED
    assert record.result is None
    assert work_calls == 0
    assert coordinator.get(user_id="user-a", job_id=record.job_id) is None
    assert coordinator.clear_user("user-a") == 0



def test_cleared_player_history_worker_stops_before_heavy_service_call() -> None:
    state_a = _state("a")
    context = _runtime("user-a", state_a)
    running = Event()
    release = Event()
    service_calls = 0

    class Service:
        def player_history(self, _context, _player_id):
            nonlocal service_calls
            service_calls += 1
            return ()

    class PausedCoordinator(PlayerHistoryBackgroundCoordinator):
        def _update(self, key, *, status, seasons=(), error=None):
            updated = super()._update(
                key,
                status=status,
                seasons=seasons,
                error=error,
            )
            if status == PlayerHistoryBuildStatus.RUNNING and updated:
                running.set()
                assert release.wait(timeout=2.0)
            return updated

    coordinator = PausedCoordinator(
        Service(),
        max_workers=1,
        max_pending=1,
        max_records=2,
        heavy_work_coordinator=None,
    )
    record = coordinator.request(context, "player:1")
    assert running.wait(timeout=1.0)

    assert coordinator.clear_user("user-a") == 1
    release.set()

    deadline = __import__("time").monotonic() + 2.0
    while __import__("time").monotonic() < deadline:
        if coordinator._futures.get(
            (context.user_id, state_a.state_id, "player:1")
        ) is None:
            break
        sleep(0.01)

    assert service_calls == 0
    assert coordinator.clear_user("user-a") == 0
    assert record.user_id == "user-a"



def test_stale_player_history_context_cannot_reacquire_execution_after_boundary() -> None:
    context = _runtime("user-a", _state("a"))
    service_calls = 0

    class Service:
        def player_history(self, _context, _player_id):
            nonlocal service_calls
            service_calls += 1
            return ()

    coordinator = PlayerHistoryBackgroundCoordinator(
        Service(),
        max_workers=1,
        max_pending=1,
        max_records=2,
        ownership_validator=lambda _context: False,
    )

    try:
        coordinator.request(context, "player:1")
    except PlayerHistoryCapacityError as exc:
        assert "context changed" in str(exc)
    else:
        raise AssertionError("stale Player History context must be rejected")

    assert service_calls == 0
    assert coordinator.clear_user("user-a") == 0


def test_synchronous_connect_runs_boundary_before_behavioral_work(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state_a = _state("a")
    state_b = _state("b")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state_a)
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", str(transition.next_league_id)))
        return {"status": "released"}

    behavior = SimpleNamespace(
        start=lambda **kwargs: events.append(
            ("behavior", kwargs["league_state"].league.league_id)
        )
    )
    app = create_app(
        runtime_store=store,
        state_loader=lambda external_id: state_b if external_id == "b" else state_a,
        behavioral_coordinator=behavior,
        state_resource_boundary=boundary,
    )
    response = TestClient(app).post(
        "/api/connect/sleeper",
        json={"league_external_id": "b"},
    )
    assert response.status_code == 200
    assert events[:2] == [
        ("boundary", "sleeper:b"),
        ("behavior", "sleeper:b"),
    ]



def test_overlapping_synchronous_connects_cannot_restart_older_behavior_after_newer_state(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state_a = _state("a")
    state_b = _state("b")
    state_c = _state("c")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state_a)
    b_boundary_entered = Event()
    release_b_boundary = Event()
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", str(transition.next_league_id)))
        if transition.next_league_id == state_b.league.league_id:
            b_boundary_entered.set()
            assert release_b_boundary.wait(timeout=2.0)
        return {"status": "released"}

    behavior = SimpleNamespace(
        start=lambda **kwargs: events.append(
            ("behavior", kwargs["league_state"].league.league_id)
        )
    )
    app = create_app(
        runtime_store=store,
        state_loader=lambda external_id: {
            "b": state_b,
            "c": state_c,
        }[external_id],
        behavioral_coordinator=behavior,
        state_resource_boundary=boundary,
    )
    client = TestClient(app)
    responses: dict[str, object] = {}

    def connect(external_id: str) -> None:
        responses[external_id] = client.post(
            "/api/connect/sleeper",
            json={"league_external_id": external_id},
        )

    b_thread = Thread(target=lambda: connect("b"))
    c_thread = Thread(target=lambda: connect("c"))
    b_thread.start()
    assert b_boundary_entered.wait(timeout=1.0)

    c_thread.start()
    sleep(0.05)
    assert c_thread.is_alive()

    release_b_boundary.set()
    b_thread.join(timeout=2.0)
    c_thread.join(timeout=2.0)
    assert not b_thread.is_alive()
    assert not c_thread.is_alive()
    assert responses["b"].status_code == 200
    assert responses["c"].status_code == 200
    assert store.get("local-beta-user").league_state.state_id == state_c.state_id
    assert events == [
        ("boundary", "sleeper:b"),
        ("behavior", "sleeper:b"),
        ("boundary", "sleeper:c"),
        ("behavior", "sleeper:c"),
    ]


def test_background_connect_runs_same_boundary_before_behavioral_work(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state_a = _state("a")
    state_b = _state("b")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state_a)
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", str(transition.next_league_id)))
        return {"status": "released"}

    behavior = SimpleNamespace(
        start=lambda **kwargs: events.append(
            ("behavior", kwargs["league_state"].league.league_id)
        )
    )
    app = create_app(
        runtime_store=store,
        state_loader=lambda external_id: state_b if external_id == "b" else state_a,
        behavioral_coordinator=behavior,
        state_resource_boundary=boundary,
    )
    coordinator = install_hosted_connect_routes(
        app,
        runtime_store=store,
        state_loader=lambda external_id: state_b if external_id == "b" else state_a,
        behavioral_coordinator=behavior,
        intelligence_reconciler=None,
        state_activator=app.state.activate_state_with_resource_boundary,
    )
    response = TestClient(app).post(
        "/api/connect/sleeper/background",
        json={"league_external_id": "b"},
    )
    assert response.status_code == 200
    _wait_connect(coordinator)
    assert events[:2] == [
        ("boundary", "sleeper:b"),
        ("behavior", "sleeper:b"),
    ]


def test_material_same_league_refresh_runs_boundary_before_new_behavioral_work(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state_a = _state("a")
    state_a2 = _state("a", team_suffix=" changed", minute=1)
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state_a)
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", transition.reason))
        return {"status": "released"}

    behavior = SimpleNamespace(
        start=lambda **kwargs: events.append(
            ("behavior", kwargs["league_state"].state_id)
        )
    )
    app = create_app(
        runtime_store=store,
        state_loader=lambda _external_id: state_a2,
        behavioral_coordinator=behavior,
        state_resource_boundary=boundary,
    )
    coordinator = install_hosted_connect_routes(
        app,
        runtime_store=store,
        state_loader=lambda _external_id: state_a2,
        behavioral_coordinator=behavior,
        intelligence_reconciler=None,
        state_activator=app.state.activate_state_with_resource_boundary,
    )
    response = TestClient(app).post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "a"},
    )
    assert response.status_code == 200
    _wait_connect(coordinator)
    assert events[0] == ("boundary", "background_material_refresh")
    assert events[1][0] == "behavior"
    assert store.get("local-beta-user").league_state.state_id == state_a2.state_id


def test_timestamp_only_same_league_refresh_retains_resource_boundary(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state_a = _state("a", minute=0)
    state_a_timestamp_only = _state("a", minute=1)
    assert state_a.state_id != state_a_timestamp_only.state_id
    assert (
        league_material_fingerprint(state_a)
        == league_material_fingerprint(state_a_timestamp_only)
    )

    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state_a)
    events: list[tuple[str, str]] = []

    def boundary(transition: ResourceTransition):
        events.append(("boundary", str(transition.next_state_id)))
        return {"status": "released"}

    behavior = SimpleNamespace(
        start=lambda **kwargs: events.append(
            ("behavior", kwargs["league_state"].state_id)
        )
    )
    app = create_app(
        runtime_store=store,
        state_loader=lambda _external_id: state_a_timestamp_only,
        behavioral_coordinator=behavior,
        state_resource_boundary=boundary,
    )
    coordinator = install_hosted_connect_routes(
        app,
        runtime_store=store,
        state_loader=lambda _external_id: state_a_timestamp_only,
        behavioral_coordinator=behavior,
        intelligence_reconciler=None,
        state_activator=app.state.activate_state_with_resource_boundary,
    )
    response = TestClient(app).post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "a"},
    )
    assert response.status_code == 200
    _wait_connect(coordinator)

    assert events == []
    assert store.get("local-beta-user").league_state.state_id == state_a.state_id


def test_hosted_composition_registers_complete_user_execution_boundary() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )
    for name in (
        "market_wrappers",
        "market_enrichment",
        "behavioral",
        "intrinsic",
        "player_future",
        "player_history",
        "presentation_validation",
    ):
        assert f'("{name}",' in source
    assert "StateResourceBoundary(" in source
    assert "state_resource_boundary=_apply_runtime_resource_boundary" in source
    assert "state_activator=app.state.activate_state_with_resource_boundary" in source
    assert "retention_validator=_market_execution_retention_valid" in source
    assert "and _market_execution_retention_valid(context)" in source


def test_all_supported_transition_paths_use_shared_resource_boundary() -> None:
    webapp = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    hosted = Path("src/fsffl/product/hosted_connect.py").read_text(encoding="utf-8")
    acceptance = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )

    sync_connect = webapp.split('@application.post("/api/connect/sleeper")', 1)[1].split(
        '@application.get("/api/behavioral/status")', 1
    )[0]
    assert "activate_state_with_resource_boundary(" in sync_connect

    sync_reconcile = webapp.split("def reconcile(progress)", 1)[1].split(
        "def work(progress)", 1
    )[0]
    assert "apply_state_resource_boundary(" in sync_reconcile

    assert 'reason="background_connect"' in hosted
    assert 'reason="background_material_refresh"' in hosted
    assert "state_activator(" in hosted
    assert "state_activator(" in acceptance


def test_hard_memory_gate_is_unchanged() -> None:
    assert DEFAULT_MEMORY_LIMIT_BYTES == 536_870_900
    acceptance = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )
    assert "if limit > 0 and observed >= limit:" in acceptance
    assert "hard memory limit reached" in acceptance


def test_intrinsic_compatible_restore_waits_for_existing_heavy_phase() -> None:
    state = _state("a")
    context = _runtime("user-a", state)
    gate = HeavyWorkCoordinator(max_waiters=2)
    forecast_entered = Event()
    release_forecast = Event()
    restore_called = Event()
    restore_finished = Event()
    contract = SimpleNamespace(estimates=())

    class Loader:
        forecast_model_version = "fixture-v1"

        def restore_compatible(self, _context):
            restore_called.set()
            return contract

        def intrinsic_input_fingerprint(self, _context):
            return "fixture-input"

        def __call__(self, _context):
            raise AssertionError("staged compatible restore should avoid rebuild")

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        Loader(),
        max_workers=1,
        heavy_work_coordinator=gate,
    )

    def hold_forecast() -> None:
        with gate.claim(kind="forecast", key="forecast:first-load"):
            forecast_entered.set()
            assert release_forecast.wait(timeout=2.0)

    def restore_intrinsic() -> None:
        coordinator.restore_compatible_staged(context)
        restore_finished.set()

    forecast_thread = Thread(target=hold_forecast)
    restore_thread = Thread(target=restore_intrinsic)
    forecast_thread.start()
    assert forecast_entered.wait(timeout=1.0)
    restore_thread.start()
    sleep(0.05)

    assert restore_called.is_set() is False
    assert restore_finished.is_set() is False
    assert gate.snapshot().waiting_count == 1

    release_forecast.set()
    forecast_thread.join(timeout=2.0)
    restore_thread.join(timeout=2.0)
    assert not forecast_thread.is_alive()
    assert not restore_thread.is_alive()
    assert restore_called.is_set()
    restored = coordinator.current(context)
    assert restored is not None
    assert restored.contract is contract


def test_first_load_value_lenses_do_not_start_intrinsic_or_materialize_player_rows() -> None:
    state = _state("a")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("user-a", state)
    store.select_team("user-a", state.teams[0].team_id)
    store.begin_working_generation("user-a", league_state=state)

    class Coordinator:
        def __init__(self) -> None:
            self.request_calls = 0

        def current(self, _runtime):
            return None

        def request(self, _runtime):
            self.request_calls += 1
            raise AssertionError("first-load foreground read must not start Intrinsic")

    coordinator = Coordinator()
    app = FastAPI()
    install_league_value_lens_routes(
        app,
        runtime_store=store,
        contract_loader=lambda _runtime: (_ for _ in ()).throw(
            AssertionError("first-load foreground read must not load Intrinsic")
        ),
        require_user=lambda: "user-a",
        background_coordinator=coordinator,  # type: ignore[arg-type]
    )
    client = TestClient(app)

    response = client.get("/api/league/value-lenses?universe=all")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "loading"
    assert payload["league_state_id"] == state.state_id
    assert payload["players"] == []
    assert payload["intrinsic_execution"]["status"] == "staged"
    assert payload["surface_readiness"]["status"] == "building_optional"
    assert coordinator.request_calls == 0


def test_browser_manual_refresh_joins_auto_refresh_and_reaches_usable_core_layers(
    monkeypatch,
) -> None:
    """Reproduce Safari auto-refresh + manual tap + foreground/value-lens reads."""

    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    original = _state("a", minute=0)
    refreshed = _state("a", team_suffix=" changed", minute=1)
    state_to_load = [refreshed]
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", original)
    store.select_team("local-beta-user", original.teams[0].team_id)

    state_loads = 0
    release_state_sync = Event()
    state_sync_entered = Event()
    forecast_entered = Event()
    release_forecast = Event()

    def state_loader(_external_id: str) -> LeagueState:
        nonlocal state_loads
        state_loads += 1
        state_sync_entered.set()
        assert release_state_sync.wait(timeout=3.0)
        return state_to_load[0]

    observation = SimpleNamespace(as_of=refreshed.as_of, player_id="fixture-player")
    forecast_evidence = SimpleNamespace(
        raw_forecasts=(observation,),
        league_scored_forecasts=(observation,),
        successful_source_ids=("fixture-source",),
        failed_sources=(),
        uncertainty_ready=True,
        evidence_basis="fixture-governed",
        runtime_result=SimpleNamespace(
            simulation_authority_blockers=(),
            partial_fantasy_point_forecasts=(),
            simulation_material_partial_player_ids=(),
            fumbles_lost_non_material_partial_player_ids=(),
            fumbles_lost_material_partial_player_ids=(),
            family_coverage=(),
            evaluation_as_of=refreshed.as_of,
        ),
    )

    def forecast_loader(_state: LeagueState):
        forecast_entered.set()
        assert release_forecast.wait(timeout=3.0)
        return forecast_evidence

    def simulation_for(state: LeagueState):
        return SimpleNamespace(
            league_view=SimpleNamespace(
                context=SimpleNamespace(league_state_id=state.state_id)
            ),
            simulation_result=SimpleNamespace(simulation_count=50_000),
        )

    def value_for(state: LeagueState):
        return SimpleNamespace(
            league_state_id=state.state_id,
            estimates=(SimpleNamespace(as_of=state.as_of),),
            fsffl_cardinal_values=(),
            pick_variant_market_values=(),
            successful_source_ids=("fixture-value-source",),
            coverage=1.0,
            cardinal_player_coverage=1.0,
        )

    intrinsic_reconciled_state_ids: list[str] = []

    def reconcile_intrinsic(runtime):
        intrinsic_reconciled_state_ids.append(runtime.league_state.state_id)
        return {"status": "full"}

    app = create_app(
        runtime_store=store,
        state_loader=state_loader,
        forecast_loader=forecast_loader,
        simulation_loader=lambda state, _evidence: simulation_for(state),
        value_loader=value_for,
        product_capability_reconciler=reconcile_intrinsic,
        heavy_work_coordinator=HeavyWorkCoordinator(memory_limit_bytes=DEFAULT_MEMORY_LIMIT_BYTES),
    )
    connect_jobs = LeagueConnectCoordinator(max_workers=1)
    install_hosted_connect_routes(
        app,
        runtime_store=store,
        state_loader=state_loader,
        behavioral_coordinator=SimpleNamespace(start=lambda **_kwargs: None),
        coordinator=connect_jobs,
        intelligence_reconciler=app.state.start_intelligence_reconciliation,
        state_activator=app.state.activate_state_with_resource_boundary,
        full_refresh_seconds=3600,
    )

    class IntrinsicCoordinator:
        def current(self, _runtime):
            return None

        def request(self, _runtime):
            raise AssertionError("first-load Market polling must stay staged")

    install_league_value_lens_routes(
        app,
        runtime_store=store,
        contract_loader=lambda _runtime: None,
        require_user=lambda: "local-beta-user",
        background_coordinator=IntrinsicCoordinator(),  # type: ignore[arg-type]
    )

    client = TestClient(app)
    auto_refresh = client.post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "a"},
    )
    assert auto_refresh.status_code == 200
    assert state_sync_entered.wait(timeout=1.0)

    manual = client.post("/api/intelligence/jobs")
    assert manual.status_code == 200
    joined = manual.json()
    assert joined["state_sync_owner"] == "hosted_connect_refresh"
    assert joined["job_id"] == auto_refresh.json()["job_id"]
    assert state_loads == 1
    assert client.get("/api/intelligence/jobs/current").json()["job_id"] == joined["job_id"]

    release_state_sync.set()
    assert forecast_entered.wait(timeout=2.0)

    # Concurrent browser reads and automatic Market/value-lens polls must stay
    # lightweight and must not start Intrinsic or duplicate core builders.
    with ThreadPoolExecutor(max_workers=5) as readers:
        reads = [
            readers.submit(client.get, "/api/product-context"),
            readers.submit(client.get, "/api/intelligence/status"),
            *[
                readers.submit(client.get, "/api/league/value-lenses")
                for _ in range(3)
            ],
        ]
        responses = [future.result(timeout=2.0) for future in reads]
    assert all(response.status_code == 200 for response in responses)
    for response in responses[2:]:
        staged = response.json()
        assert staged["status"] == "loading"
        assert staged["players"] == []
    assert state_loads == 1

    release_forecast.set()
    deadline = __import__("time").monotonic() + 3.0
    while __import__("time").monotonic() < deadline:
        job = app.state.intelligence_jobs.current("local-beta-user")
        if job is not None and job.status.value in {"completed", "failed", "interrupted"}:
            break
        sleep(0.01)
    assert job is not None and job.status.value == "completed", job
    current = store.get("local-beta-user")
    assert current.league_state is not None
    assert current.league_state.state_id == refreshed.state_id
    assert current.forecast_evidence is forecast_evidence
    assert current.simulation_analytics is not None
    assert current.value_evidence is not None
    readiness = app.state.capability_readiness_reader(current)
    assert readiness["overall_status"] == "full"
    assert readiness["forecast"]["consumer_usable"] is True
    assert readiness["forecast"]["status"] == "full"
    assert readiness["simulation"]["status"] == "full"
    assert readiness["current_value"]["status"] == "full"
    assert intrinsic_reconciled_state_ids == [refreshed.state_id]

    # Model a process restart after canonical State has been durably retained but
    # its in-memory working generation was lost. A browser status poll must resume
    # the missing exact-State layers without another provider State sync.
    after_restart = _state("a", minute=2)
    store.set_league_state("local-beta-user", after_restart)
    interrupted = IntelligenceJob(
        job_id="interrupted-after-restart",
        user_id="local-beta-user",
        league_state_id=after_restart.state_id,
        status=IntelligenceJobStatus.INTERRUPTED,
        phase=IntelligenceJobPhase.INTERRUPTED,
        message="server restarted",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        error="server_restart",
    )
    app.state.intelligence_jobs._jobs[interrupted.job_id] = interrupted
    app.state.intelligence_jobs._current_by_user[interrupted.user_id] = interrupted.job_id
    resume = client.get("/api/intelligence/jobs/current").json()
    assert resume["resumed_after_restart"] is True
    assert resume["status"] in {"queued", "running", "completed"}
    deadline = __import__("time").monotonic() + 3.0
    while __import__("time").monotonic() < deadline:
        recovered_job = app.state.intelligence_jobs.current("local-beta-user")
        if recovered_job is not None and recovered_job.status == IntelligenceJobStatus.COMPLETED:
            break
        sleep(0.01)
    recovered = store.get("local-beta-user")
    assert recovered_job is not None and recovered_job.status == IntelligenceJobStatus.COMPLETED
    assert recovered.forecast_evidence is forecast_evidence
    assert recovered.simulation_analytics is not None
    assert recovered.value_evidence is not None
    recovered_readiness = app.state.capability_readiness_reader(recovered)
    assert recovered_readiness["overall_status"] == "full"
    assert recovered_readiness["forecast"]["consumer_usable"] is True
    assert intrinsic_reconciled_state_ids == [refreshed.state_id, after_restart.state_id]
    assert state_loads == 1

    # A direct refresh owns its own State sync. Once that sync reaches a different
    # State, persist the new job identity before downstream phases so a restart can
    # match the durable job to the State it was building.
    manually_synced = _state("a", minute=3)
    state_to_load[0] = manually_synced
    manual_refresh = client.post("/api/intelligence/jobs")
    assert manual_refresh.status_code == 200
    deadline = __import__("time").monotonic() + 3.0
    while __import__("time").monotonic() < deadline:
        manual_job = app.state.intelligence_jobs.current("local-beta-user")
        if manual_job is not None and manual_job.status == IntelligenceJobStatus.COMPLETED:
            break
        sleep(0.01)
    assert manual_job is not None
    assert manual_job.status == IntelligenceJobStatus.COMPLETED, manual_job
    assert manual_job.league_state_id == manually_synced.state_id
    assert state_loads == 2
    resource = app.state.heavy_work_coordinator.snapshot()
    assert resource.memory_limit_bytes == DEFAULT_MEMORY_LIMIT_BYTES
    assert max(resource.current_rss_bytes, resource.peak_rss_bytes) < DEFAULT_MEMORY_LIMIT_BYTES


def test_published_full_readiness_stays_full_during_working_reconciliation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state = _state("served-ready")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state)
    store.select_team("local-beta-user", state.teams[0].team_id)

    app = create_app(
        runtime_store=store,
        capability_readiness_reader=lambda _runtime: {
            "overall_status": "full",
            "served_last_good": {"available": False},
            "forecast": {"status": "full"},
            "simulation": {"status": "full"},
            "current_value": {"status": "full"},
            "intrinsic": {"status": "full"},
        },
    )

    store.begin_working_generation("local-beta-user", league_state=state)
    published = store.get("local-beta-user")
    readiness = app.state.capability_readiness_reader(published)

    assert readiness["overall_status"] == "full"
    assert readiness["publication"]["working_generation_active"] is True
    assert readiness["publication"]["status"] == "serving_published_during_update"
    assert readiness["reconciliation"]["status"] == "running"
    assert readiness["reconciliation"]["published_state_id"] == state.state_id
    assert readiness["reconciliation"]["target_state_id"] == state.state_id
    assert readiness["served_last_good"].get("stale") is not True


def test_same_state_full_refresh_verifies_without_rebuilding_current_layers(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state = _state("same-state-noop")
    synced_state = _state("same-state-noop", minute=1)
    assert synced_state.state_id != state.state_id
    assert league_material_fingerprint(synced_state) == league_material_fingerprint(state)
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state)
    store.select_team("local-beta-user", state.teams[0].team_id)

    observation = SimpleNamespace(as_of=state.as_of, player_id="fixture-player")
    forecast = SimpleNamespace(
        raw_forecasts=(observation,),
        league_scored_forecasts=(observation,),
        successful_source_ids=("fixture-source",),
        failed_sources=(),
        uncertainty_ready=True,
        evidence_basis="fixture-governed",
        runtime_result=SimpleNamespace(
            simulation_authority_blockers=(),
            partial_fantasy_point_forecasts=(),
            simulation_material_partial_player_ids=(),
            fumbles_lost_non_material_partial_player_ids=(),
            fumbles_lost_material_partial_player_ids=(),
            family_coverage=(),
            evaluation_as_of=state.as_of,
        ),
    )
    simulation = SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state.state_id)
        ),
        simulation_result=SimpleNamespace(simulation_count=50_000),
    )
    values = SimpleNamespace(
        league_state_id=state.state_id,
        estimates=(SimpleNamespace(as_of=state.as_of),),
        fsffl_cardinal_values=(),
        pick_variant_market_values=(),
        successful_source_ids=("fixture-value-source",),
        coverage=1.0,
        cardinal_player_coverage=1.0,
    )
    store.set_forecast_evidence("local-beta-user", forecast)
    store.set_simulation_analytics("local-beta-user", simulation)
    store.set_value_evidence("local-beta-user", values)
    store.bind_publication_generation_id("local-beta-user", "published-generation-1")

    calls = {"state": 0, "forecast": 0, "simulation": 0, "value": 0, "intrinsic": 0}

    def state_loader(_external_id: str) -> LeagueState:
        calls["state"] += 1
        return synced_state

    def should_not_forecast(_state: LeagueState):
        calls["forecast"] += 1
        raise AssertionError("current Forecast must not rebuild for unchanged full State")

    def should_not_simulate(_state: LeagueState, _forecast):
        calls["simulation"] += 1
        raise AssertionError("current Simulation must not rebuild for unchanged full State")

    def should_not_value(_state: LeagueState):
        calls["value"] += 1
        raise AssertionError("current Value must not rebuild for unchanged full State")

    def should_not_intrinsic(_runtime):
        calls["intrinsic"] += 1
        raise AssertionError("current Intrinsic must not reconcile for unchanged full State")

    app = create_app(
        runtime_store=store,
        state_loader=state_loader,
        forecast_loader=should_not_forecast,
        simulation_loader=should_not_simulate,
        value_loader=should_not_value,
        product_capability_reconciler=should_not_intrinsic,
        capability_readiness_reader=lambda _runtime: {
            "overall_status": "full",
            "served_last_good": {"available": False},
            "forecast": {"status": "full"},
            "simulation": {"status": "full"},
            "current_value": {"status": "full"},
            "intrinsic": {"status": "full"},
        },
    )
    client = TestClient(app)

    response = client.post("/api/intelligence/jobs")
    assert response.status_code == 200

    deadline = __import__("time").monotonic() + 3.0
    job = None
    while __import__("time").monotonic() < deadline:
        job = app.state.intelligence_jobs.current("local-beta-user")
        if job is not None and job.status in {
            IntelligenceJobStatus.COMPLETED,
            IntelligenceJobStatus.FAILED,
            IntelligenceJobStatus.INTERRUPTED,
        }:
            break
        sleep(0.01)

    assert job is not None
    assert job.status == IntelligenceJobStatus.COMPLETED
    assert "no rebuild was required" in job.message.lower()
    assert calls == {
        "state": 1,
        "forecast": 0,
        "simulation": 0,
        "value": 0,
        "intrinsic": 0,
    }
    assert store.working_generation_active("local-beta-user") is False
    published = store.get("local-beta-user")
    assert published.publication_generation_id == "published-generation-1"
    assert published.league_state is state
    assert published.forecast_evidence is forecast
    assert published.simulation_analytics is simulation
    assert published.value_evidence is values
