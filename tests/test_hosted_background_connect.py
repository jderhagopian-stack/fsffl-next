from __future__ import annotations

from threading import Event
from time import monotonic, sleep

from fsffl.product.hosted_connect import LeagueConnectCoordinator, LeagueConnectStatus
from fsffl.product.persistent_webapp import app


def test_background_connect_returns_without_waiting_for_provider_work() -> None:
    coordinator = LeagueConnectCoordinator(max_workers=1)
    release = Event()
    started = Event()

    def work() -> None:
        started.set()
        release.wait(timeout=2)

    before = monotonic()
    job = coordinator.start(user_id="u", league_external_id="123", work=work)
    elapsed = monotonic() - before

    assert elapsed < 0.25
    assert job.status == LeagueConnectStatus.QUEUED
    assert started.wait(timeout=1)
    current = coordinator.current("u")
    assert current is not None
    assert current.status == LeagueConnectStatus.RUNNING

    duplicate = coordinator.start(user_id="u", league_external_id="123", work=work)
    assert duplicate.job_id == current.job_id

    release.set()
    deadline = monotonic() + 2
    while monotonic() < deadline:
        current = coordinator.current("u")
        if current is not None and current.status == LeagueConnectStatus.COMPLETED:
            break
        sleep(0.01)
    assert current is not None
    assert current.status == LeagueConnectStatus.COMPLETED


def test_hosted_app_exposes_short_start_and_poll_connect_routes() -> None:
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/api/connect/sleeper/background" in paths
    assert "/api/connect/sleeper/background/current" in paths


def test_mobile_connect_uses_background_import_and_transport_recovery() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "fsfflMobileSafariRecoveryDisabled=true" in source
    assert "/api/connect/sleeper/background'" in source
    assert "/api/connect/sleeper/background/current" in source
    assert "Load failed|Failed to fetch|Network request failed|network error" in source
    assert "document.addEventListener('click'" in source
    assert "event.stopImmediatePropagation()" in source
    assert "window.fsfflRestoreSession=restoreSavedSession" in source
    assert "Loading league…" in source
    assert "visibilitychange" not in source
    assert "pageshow" not in source


def test_mobile_connect_is_single_flight_and_recovers_existing_job_before_starting() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "let activeConnectPromise=null" in source
    assert "let activeLeagueId=null" in source
    assert "activeConnectPromise&&activeLeagueId===leagueId" in source
    assert "const existing=await recoverCurrentJob(leagueId)" in source
    assert "['queued','running'].includes(existing.status)" in source


def test_hosted_connect_persists_partial_state_off_request_path() -> None:
    source = open(
        "src/fsffl/product/persistent_runtime.py",
        encoding="utf-8",
    ).read()

    # League State must become durable without putting Postgres serialization back
    # on the Connect League request. One worker preserves checkpoint ordering so an
    # earlier partial snapshot cannot overwrite a later complete bundle.
    set_state = source.split("def set_league_state", 1)[1].split("def set_forecast_evidence", 1)[0]
    assert "self._checkpoint_async(user_id, context)" in set_state
    assert "ThreadPoolExecutor" in source
    assert "max_workers=1" in source
    assert "self._checkpoint_executor.submit" in source
    assert "context.forecast_evidence is not None" not in source
    assert "context.simulation_analytics is not None" not in source
    assert "context.value_evidence is not None" not in source


def test_hosted_connect_reuses_restored_matching_league_before_provider_reload() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()

    assert "already_loaded = _matches_sleeper_league" in source
    assert "if already_loaded:" in source
    assert "return" in source.split("if already_loaded:", 1)[1].split("league_state = state_loader", 1)[0]
