from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.phase1_latency import install_phase1_latency_routes


def test_phase1_latency_route_accepts_exit_gate_measurements() -> None:
    app = FastAPI()
    install_phase1_latency_routes(app)
    client = TestClient(app)

    response = client.post(
        "/api/performance/latency",
        json={
            "operation": "opportunities_ready",
            "elapsed_ms": 742.5,
            "outcome": "success",
            "detail": "live_beta",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "recorded", "operation": "opportunities_ready"}


def test_phase1_latency_route_rejects_unknown_measurements() -> None:
    app = FastAPI()
    install_phase1_latency_routes(app)
    client = TestClient(app)

    response = client.post(
        "/api/performance/latency",
        json={"operation": "invented_metric", "elapsed_ms": 10.0},
    )

    assert response.status_code == 422


def test_phase1_latency_client_covers_required_user_perceived_paths() -> None:
    mobile = Path("src/fsffl/product/static/mobile_safari_recovery.js").read_text()
    observer = Path("src/fsffl/product/static/phase1_latency.js").read_text()

    assert "first_connect_ready" in mobile
    assert "restore_ready" in mobile
    assert "opportunities_ready" in observer
    assert "explicit_deep_analysis" in observer
    assert "document.querySelector('#screen')" in observer
    assert "observe(document.body" not in observer
