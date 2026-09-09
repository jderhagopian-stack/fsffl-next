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
