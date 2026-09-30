from __future__ import annotations

import gc
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from time import sleep
import weakref

from fastapi.testclient import TestClient

from fsffl.product import resource_coordinator as resource_module
from fsffl.product.hosted_connect import (
    LeagueConnectCoordinator,
    LeagueConnectStatus,
    install_hosted_connect_routes,
)
from fsffl.product.intrinsic_background import ShapleyIntrinsicBackgroundCoordinator
from fsffl.product.market_economics_cache import make_cached_candidate_economics
from fsffl.product.market_progressive_enrichment import (
    MarketDecisionEnrichmentCoordinator,
    MarketEnrichmentStatus,
)
from fsffl.product.opportunity_search_cache import make_cached_opportunity_search
from fsffl.product.opportunity_workspace_cache import make_cached_opportunity_workspace
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


def test_timestamp_only_same_league_refresh_restarts_behavior_after_boundary(
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

    assert events == [
        ("boundary", state_a_timestamp_only.state_id),
        ("behavior", state_a_timestamp_only.state_id),
    ]
    assert store.get("local-beta-user").league_state.state_id == state_a_timestamp_only.state_id


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
