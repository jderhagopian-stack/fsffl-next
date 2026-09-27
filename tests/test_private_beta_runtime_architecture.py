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
        'app.router.add_event_handler("startup", _log_startup_runtime_readiness)'
        in source
    )
    assert (
        'app.router.add_event_handler("startup", _prewarm_hosted_product_acceptance)'
        not in source
    )
    assert (
        'app.router.add_event_handler("startup", _maybe_start_state_first_production_acceptance)'
        not in source
    )
    assert "Acceptance is explicit; startup performs restore-only work." in source
    assert '@app.post("/api/runtime/product-acceptance")' in source
    assert '@app.get("/health/runtime-resources")' in source


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
