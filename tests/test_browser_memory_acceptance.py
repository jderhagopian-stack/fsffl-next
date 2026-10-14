from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from threading import Event
from time import sleep

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.background_jobs import IntelligenceJob, IntelligenceJobPhase, IntelligenceJobStatus
from fsffl.product.hosted_connect import LeagueConnectCoordinator, install_hosted_connect_routes
from fsffl.product.league_value_lens_routes import install_league_value_lens_routes
from fsffl.product.resource_coordinator import DEFAULT_MEMORY_LIMIT_BYTES, HeavyWorkCoordinator
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.webapp import create_app
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _state(external_id: str, *, team_suffix: str = "", minute: int = 0) -> LeagueState:
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
            Team(team_id=f"{external_id}:a", league_id=league_id, display_name=f"Alpha{team_suffix}"),
            Team(team_id=f"{external_id}:b", league_id=league_id, display_name="Beta"),
        ),
        team_states=(TeamState(team_id=f"{external_id}:a", roster=()), TeamState(team_id=f"{external_id}:b", roster=())),
        players=(),
        player_states=(),
    )


def test_browser_manual_refresh_joins_auto_refresh_and_reaches_usable_core_layers(
    monkeypatch,
) -> None:
    """Measure the browser workload in a fresh process, with the actual hard cap.

    The full suite's unrelated model fixtures and allocator high-water mark are
    not part of this browser workload. Keep every original runtime assertion.
    """
    import os
    import subprocess
    import sys

    if os.getenv("FSFFL_BROWSER_MEMORY_ACCEPTANCE_CHILD") != "1":
        child = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-s",
             f"{Path(__file__).resolve()}::test_browser_manual_refresh_joins_auto_refresh_and_reaches_usable_core_layers"],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "FSFFL_BROWSER_MEMORY_ACCEPTANCE_CHILD": "1"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=120, check=False,
        )
        assert child.returncode == 0, child.stdout
        print(child.stdout)
        return

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
    manually_synced = _state("a", team_suffix=" manual-change", minute=3)
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
    print(f"browser_refresh_peak_rss_bytes={max(resource.current_rss_bytes, resource.peak_rss_bytes)}")
