from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic, sleep

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



def test_hosted_acceptance_combines_sync_surfaces_pi_history_and_resource_gate() -> None:
    source = Path("src/fsffl/product/state_first_acceptance.py").read_text(
        encoding="utf-8"
    )
    assert "pi_history_during_active_reconciliation" in source
    assert "reload_during_active_reconciliation" in source
    assert "fsffl_automatic_state_sync" in source
    assert "hodor_home_franchise_league" in source
    assert "pi_history_repeat_after_fsffl_return" in source
    assert "fsffl_managed_team_publication_interruption" in source
    assert "managed_team_during_active_reconciliation" in source
    assert "managed_team_after_reconciliation_interruption" in source
    assert "managed-team switch was not interleaved with active reconciliation" in source
    assert 'team_surface.get("franchise_team_id") != alternate_team_id' in source
    assert '"selected_team_id": runtime.selected_team_id' in source
    assert "within_memory_budget" in source
    assert "peak_rss_bytes" in source
    assert "process_identity_start" in source
    assert "process_identity_end" in source


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
    assert "_MAX_ENTRIES = 1" in workspace_cache
    assert "_MAX_ENTRIES = 1" in search_cache
    assert "cache.clear()" in workspace_cache
    assert "cache.clear()" in search_cache
    assert "active_scope" in economics_cache
    assert "cache.clear()" in economics_cache
