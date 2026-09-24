from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.foreground_pressure import (
    ForegroundPressure,
    foreground_pressure,
    install_foreground_pressure,
)


def test_pressure_tracks_active_request_and_clears_after_success() -> None:
    pressure = ForegroundPressure(
        slow_request_seconds=10.0,
        recovery_seconds=0.0,
        yield_seconds=0.0,
    )
    assert pressure.snapshot().active_requests == 0
    pressure.begin_request()
    assert pressure.should_yield()
    assert pressure.snapshot().active_requests == 1
    pressure.end_request(elapsed_seconds=0.01)
    assert pressure.snapshot().active_requests == 0
    assert not pressure.should_yield()


def test_recent_slow_request_temporarily_preserves_pressure() -> None:
    pressure = ForegroundPressure(
        slow_request_seconds=0.1,
        recovery_seconds=1.0,
        yield_seconds=0.0,
    )
    pressure.begin_request()
    pressure.end_request(elapsed_seconds=0.2)
    assert pressure.should_yield()


def test_cooperative_yield_is_inactive_without_foreground_pressure() -> None:
    pressure = ForegroundPressure(
        slow_request_seconds=10.0,
        recovery_seconds=0.0,
        yield_seconds=0.0,
    )
    with patch("fsffl.product.foreground_pressure.sleep") as sleeper:
        assert not pressure.cooperative_yield()
        sleeper.assert_not_called()


def test_hosted_middleware_balances_success_and_failure_requests() -> None:
    app = FastAPI()
    install_foreground_pressure(app)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/fail")
    def fail():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    baseline = foreground_pressure.snapshot().active_requests

    assert client.get("/ok").status_code == 200
    assert foreground_pressure.snapshot().active_requests == baseline

    assert client.get("/fail").status_code == 500
    assert foreground_pressure.snapshot().active_requests == baseline


def test_hosted_entrypoint_installs_foreground_pressure() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text()
    assert "from .foreground_pressure import install_foreground_pressure" in source
    assert "install_foreground_pressure(app)" in source
