from __future__ import annotations

import gc
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import weakref

from fastapi.testclient import TestClient

from fsffl.product import resource_coordinator as resource_module
from fsffl.product.hosted_connect import (
    LeagueConnectCoordinator,
    LeagueConnectStatus,
    install_hosted_connect_routes,
)
from fsffl.product.market_economics_cache import make_cached_candidate_economics
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
