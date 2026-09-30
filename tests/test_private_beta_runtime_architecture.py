from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic, sleep

import fsffl.product.resource_coordinator as resource_coordinator_module
from fsffl.product.resource_coordinator import HeavyWorkCoordinator
from fsffl.product.runtime import (
    ServedIntelligenceSnapshot,
    _PendingIntelligenceSnapshot,
)


def test_served_and_pending_runtime_state_are_lightweight_identities_only() -> None:
    assert {item.name for item in fields(ServedIntelligenceSnapshot)} == {
        "league_id",
        "league_state_id",
        "as_of",
        "team_ids",
        "publication_generation_id",
    }
    assert {item.name for item in fields(_PendingIntelligenceSnapshot)} == {
        "league_state_id",
    }


def test_process_heavy_work_coordinator_serializes_distinct_builds() -> None:
    coordinator = HeavyWorkCoordinator(
        max_waiters=2,
        memory_limit_bytes=536_870_900,
    )
    first_entered = Event()
    release_first = Event()
    second_entered = Event()
    lock = Lock()
    active = 0
    max_active = 0

    def work(kind: str, key: str, entered: Event, release: Event | None) -> None:
        nonlocal active, max_active
        with coordinator.claim(kind=kind, key=key, timeout_seconds=2):
            with lock:
                active += 1
                max_active = max(max_active, active)
            entered.set()
            if release is not None:
                release.wait(timeout=2)
            with lock:
                active -= 1

    first = Thread(
        target=work,
        args=("forecast", "u:s1:forecast", first_entered, release_first),
    )
    second = Thread(
        target=work,
        args=("player_history", "s1:p1", second_entered, None),
    )
    first.start()
    assert first_entered.wait(timeout=1)
    second.start()

    deadline = monotonic() + 1
    while coordinator.snapshot().waiting_count != 1 and monotonic() < deadline:
        sleep(0.01)
    queued = coordinator.snapshot()
    assert queued.active_kind == "forecast"
    assert queued.waiting_count == 1
    assert second_entered.is_set() is False

    release_first.set()
    first.join(timeout=2)
    second.join(timeout=2)

    final = coordinator.snapshot()
    assert max_active == 1
    assert final.active_kind is None
    assert final.waiting_count == 0
    assert final.max_waiting_observed == 1
    assert final.acquisitions == 2
    assert final.completions == 2
    assert final.memory_budget_bytes == int(536_870_900 * 0.8)


def test_persistent_foreground_get_is_memory_only_and_restore_is_explicit() -> None:
    source = Path("src/fsffl/product/persistent_runtime.py").read_text(
        encoding="utf-8"
    )

    get_body = source.split("    def get(self, user_id: str)", 1)[1].split(
        "    def activate_league_state_for_connect", 1
    )[0]
    restore_body = source.split("    def restore_user(self, user_id: str)", 1)[1].split(
        "    def get(self, user_id: str)", 1
    )[0]

    assert "restore_runtime_snapshot" not in get_body
    assert "_restore_once" not in get_body
    assert "return super().get(user_id)" in get_body
    assert "restore_runtime_snapshot" in restore_body
    assert "captured_generation" in restore_body
    assert "_install_restored_snapshot_if_current" in restore_body


def test_hosted_restored_session_gate_never_blocks_fresh_connect() -> None:
    hosted = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )
    connect = Path("src/fsffl/product/hosted_connect.py").read_text(
        encoding="utf-8"
    )

    gate = hosted.split('@app.middleware("http")', 1)[1].split(
        "def _log_startup_runtime_readiness", 1
    )[0]
    assert '"/api/connect/sleeper"' in hosted
    assert "_RESTORE_GATE_BYPASS_PREFIXES" in gate
    assert "_runtime_store.get(_beta_restore_user).league_state is not None" in gate
    assert "_runtime_store.durable_restore_pending(_beta_restore_user)" in gate
    assert "asyncio.to_thread(_startup_restore_complete.wait" in gate

    background = connect.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[0]
    assert '"prepare_fresh_connect"' in background
    assert "prepare_fresh_connect(user_id)" in background
    assert background.index("prepare_fresh_connect(user_id)") < background.index(
        "league_state = state_loader(league_external_id)"
    )


def test_hosted_startup_is_restore_first_and_does_not_auto_launch_heavy_work() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )

    assert (
        'app.router.add_event_handler("startup", _start_lightweight_startup_restore)'
        in source
    )
    assert "_runtime_store.restore_user(_beta_restore_user)" not in source.split(
        "def _run_lightweight_startup_restore", 1
    )[0]
    assert "default_behavioral_store()" not in source.split(
        "def _run_lightweight_startup_restore", 1
    )[0]
    assert (
        'app.router.add_event_handler("startup", _prewarm_hosted_product_acceptance)'
        not in source
    )
    assert (
        'app.router.add_event_handler("startup", _maybe_start_state_first_production_acceptance)'
        in source
    )
    assert "FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE" in source
    acceptance = source.split(
        "def _maybe_start_state_first_production_acceptance()", 1
    )[1].split(
        '@app.get("/health/product-acceptance")', 1
    )[0]
    assert "if not enabled:" in acceptance
    assert "return" in acceptance.split("if not enabled:", 1)[1].split(
        "if _persistence_store is None:", 1
    )[0]
    assert "FSFFL_RUNTIME_ACCEPTANCE_DELAY_SECONDS" in acceptance
    assert "sleep(delay_seconds)" in acceptance
    assert "_startup_restore_complete.wait" in acceptance
    assert "Acceptance is explicit; startup performs restore-only work." in source
    assert '@app.post("/api/runtime/product-acceptance")' in source
    assert '@app.get("/health/runtime-resources")' in source
    assert '@app.get("/health/runtime-availability-acceptance")' in source


def test_readiness_has_one_server_capability_authority_without_legacy_boolean_fallback() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(
        encoding="utf-8"
    )
    refresh = Path("src/fsffl/product/static/forecast_refresh.js").read_text(
        encoding="utf-8"
    )

    assert "const serverFull=capabilities?.overall_status==='full';" in shell
    assert "!capabilities?.overall_status&&Boolean" not in shell
    assert (
        "context?.capability_readiness?.overall_status==='full'"
        in refresh
    )
    ready_fn = refresh.split("function intelligencePipelineReady", 1)[1].split(
        "function ensureIntelligenceRefreshButton", 1
    )[0]
    assert "forecast_ready" not in ready_fn
    assert "simulation_ready" not in ready_fn
    assert "value_ready" not in ready_fn


def test_hosted_core_intelligence_uses_one_background_worker_and_shared_gate() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    hosted = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )

    assert "IntelligenceJobCoordinator(max_workers=1" in source
    assert 'heavy_claim("forecast"' not in source  # multiline governed claims
    assert '"forecast",' in source
    assert '"simulation",' in source
    assert '"value",' in source
    assert "heavy_work_coordinator=_heavy_work_coordinator" in hosted
    assert "ShapleyIntrinsicBackgroundCoordinator(" in hosted
    assert "BehavioralRuntimeCoordinator(" in hosted
    assert "with store.publication_sequence(user_id):" in source



def test_hosted_acceptance_combines_sync_surfaces_pi_history_and_resource_gate() -> None:
    source = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )
    assert "fsffl_clean_state_before_team_selection" in source
    assert "clean_state_before_team_selection" in source
    assert "fsffl_initial_managed_team_selected" in source
    assert "pi_history_after_initial_publication" in source
    assert "fsffl_restart_restored_session" in source
    assert "restore_only" in source
    assert "restart restore did not recover durable core intelligence" in source
    assert 'probe_surface("restored_session_surfaces")' in source
    assert 'probe_history("restored_session_pi_history")' in source
    assert "_require_full_fsffl(settled_snapshot)" in source
    assert 'probe_surface("restored_session_settled_surfaces")' in source
    assert "product rehydration changed durable publication" in source
    assert "pi_history_during_active_reconciliation" in source
    assert "reload_during_active_reconciliation" in source
    assert "fsffl_automatic_state_sync" in source
    assert "hodor_home_franchise_league" in source
    assert "pi_history_repeat_after_fsffl_return" in source
    assert "fsffl_managed_team_publication_interruption" in source
    assert "managed_team_during_active_reconciliation" not in source
    assert "managed_team_after_reconciliation_interruption" in source
    assert "select_team_if_working_generation_active" in source
    assert "wait_for_managed_team_checkpoint" in source
    assert "with store._lock:" not in source
    assert "team_interleaving" in source
    assert 'team_surface.get("franchise_team_id")' in source
    assert 'same_promoted.get("franchise_team_id")' in source
    assert '"selected_team_id": runtime.selected_team_id' in source
    assert "within_memory_budget" in source
    assert "peak_rss_bytes" in source
    assert "process_identity_start" in source
    assert "process_identity_end" in source





def test_hosted_clean_first_run_history_is_state_only_until_terminal_publication() -> None:
    hosted = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )
    history = hosted.split("def _acceptance_history_probe", 1)[1].split(
        "def _runtime_acceptance_resource_reader", 1
    )[0]
    surfaces = hosted.split("def _acceptance_surface_probe", 1)[1].split(
        "def _acceptance_history_probe", 1
    )[0]
    orchestration = hosted.split(
        "def _maybe_start_state_first_production_acceptance()", 1
    )[1].split('@app.get("/health/product-acceptance")', 1)[0]

    assert 'label == "cold_pi_history_during_initial_reconciliation"' in history
    cold_branch = history.split("if cold_state_only:", 1)[1].split("else:", 1)[0]
    assert "entry.player_id for entry in selected_state.roster" in history
    assert "list(selected_state.roster)" not in history
    assert "canonical_player_ids" in cold_branch
    assert "canonical_roster_ids" in cold_branch
    assert "build_player_intelligence_overview" not in cold_branch
    assert "Player Intelligence lacks Y2/Y3" in history
    assert '"state_only_during_enrichment": cold_state_only' in history
    assert "state_only = context.selected_team_id is None" in surfaces
    assert '("context", "/api/product-context", {})' in surfaces
    assert '("league", "/api/league/atlas", {})' in surfaces
    state_only_branch = surfaces.split("if state_only", 1)[0]
    assert '("home", "/api/home", {})' not in state_only_branch
    assert "FSFFL_RUNTIME_AVAILABILITY_ACCEPTANCE_MODE" in orchestration
    assert 'acceptance_mode not in {"full", "journey", "restore"}' in orchestration
    assert 'restore_only=acceptance_mode == "restore"' in orchestration
    assert 'journey_only=acceptance_mode == "journey"' in orchestration


def test_realistic_hosted_journey_skips_synthetic_overlap_stress() -> None:
    source = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )
    journey = source.split("if journey_only:", 1)[1].split(
        "# Reproduce the availability incident shape", 1
    )[0]

    assert 'activate(HODOR_ACCEPTANCE_LEAGUE, label="hodor_switch")' in journey
    assert 'activate(FSFFL_ACCEPTANCE_LEAGUE, label="fsffl_return")' in journey
    assert 'sample_resources("hodor_switch")' in journey
    assert 'sample_resources("fsffl_return")' in journey
    assert 'report["mode"] = "journey"' in journey
    assert "start_sync_reconciliation" not in journey
    assert "select_team_if_working_generation_active" not in journey
    assert "same_state_during_active_reconciliation" not in journey
    assert "pi_history_during_active_reconciliation" not in journey
    assert "realistic hosted acceptance peak RSS" in journey


def test_live_pi_route_and_acceptance_share_one_history_coordinator() -> None:
    source = Path("src/fsffl/product/player_intelligence_routes.py").read_text(
        encoding="utf-8"
    )
    assert "app.state.player_history_coordinator = history" in source
    assert source.count("PlayerHistoryBackgroundCoordinator(") == 1



def test_hosted_surface_acceptance_releases_sequential_payloads_and_bounds_market_caches() -> None:
    hosted = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )
    probe = hosted.split("def _acceptance_surface_probe", 1)[1].split(
        "def _acceptance_history_probe", 1
    )[0]
    workspace_cache = Path(
        "src/fsffl/product/opportunity_workspace_cache.py"
    ).read_text(encoding="utf-8")
    search_cache = Path(
        "src/fsffl/product/opportunity_search_cache.py"
    ).read_text(encoding="utf-8")
    economics_cache = Path(
        "src/fsffl/product/market_economics_cache.py"
    ).read_text(encoding="utf-8")

    assert "payloads = {" not in probe
    assert "del payload" in probe
    assert "gc.collect()" in probe
    assert "surface_latency_seconds" in probe
    assert "max_surface_latency_seconds" in probe
    assert "total_surface_latency_seconds" in probe
    assert "_MAX_ENTRIES_PER_USER = 1" in workspace_cache
    assert "_MAX_ENTRIES_PER_USER = 1" in search_cache
    assert "def clear_user_cache(user_id: str)" in workspace_cache
    assert "def clear_user_cache(user_id: str)" in search_cache
    assert "active_scope_by_user" in economics_cache
    assert "def clear_user_cache(user_id: str)" in economics_cache



def test_heavy_work_snapshot_records_bounded_phase_memory_evidence(monkeypatch) -> None:
    rss_values = iter((100, 120, 130, 125))
    peak_values = iter((150, 220, 220))
    monkeypatch.setattr(
        resource_coordinator_module,
        "current_rss_bytes",
        lambda: next(rss_values),
    )
    monkeypatch.setattr(
        resource_coordinator_module,
        "process_peak_rss_bytes",
        lambda: next(peak_values),
    )

    coordinator = HeavyWorkCoordinator(
        max_waiters=1,
        memory_limit_bytes=1_000,
        headroom_ratio=0.20,
    )
    with coordinator.claim(kind="forecast", key="u:s1:forecast"):
        pass

    snapshot = coordinator.snapshot()
    assert snapshot.peak_rss_bytes == 220
    assert len(snapshot.recent_phase_memory) == 1
    event = snapshot.recent_phase_memory[0]
    assert event["kind"] == "forecast"
    assert str(event["key"]).startswith("sha256:")
    assert event["key"] != "u:s1:forecast"
    assert "u:s1:forecast" not in str(snapshot.__dict__)
    assert event["before_rss_bytes"] == 120
    assert event["after_rss_bytes"] == 130
    assert event["resident_delta_bytes"] == 10
    assert event["peak_before_rss_bytes"] == 150
    assert event["peak_after_rss_bytes"] == 220
    assert event["new_peak_increment_bytes"] == 70


def test_cross_league_hosted_switch_reclaims_execution_caches_before_intelligence() -> None:
    connect_source = Path("src/fsffl/product/hosted_connect.py").read_text(
        encoding="utf-8"
    )
    hosted_source = Path("src/fsffl/product/persistent_webapp.py").read_text(
        encoding="utf-8"
    )
    acceptance_source = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )

    connect = connect_source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[0]
    activate_index = connect.index("state_activator(")
    behavior_index = connect.index("behavioral_coordinator.start(", activate_index)
    reconcile_index = connect.index("intelligence_reconciler(user_id)", behavior_index)
    assert activate_index < behavior_index < reconcile_index
    assert 'reason="background_connect"' in connect

    refresh = connect_source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split(
        '@application.get("/api/connect/sleeper/background/current")', 1
    )[0]
    activate_refresh_index = refresh.index("state_activator(")
    behavior_refresh_index = refresh.index(
        "behavioral_coordinator.start(",
        activate_refresh_index,
    )
    reconcile_refresh_index = refresh.index(
        "intelligence_reconciler(user_id)",
        behavior_refresh_index,
    )
    assert activate_refresh_index < behavior_refresh_index < reconcile_refresh_index
    assert 'reason="background_material_refresh"' in refresh

    assert (
        "state_resource_boundary=_apply_runtime_resource_boundary"
        in hosted_source
    )
    assert (
        "state_activator=app.state.activate_state_with_resource_boundary"
        in hosted_source
    )
    assert '"state_transition_reclaims": []' in acceptance_source
    assert 'sample_resources(f"{label}_pre_state_activation")' in acceptance_source
    assert 'sample_resources(f"{label}_post_resource_boundary")' in acceptance_source

