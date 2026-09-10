from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.phase1_latency import install_phase1_latency_routes
from fsffl.product.webapp import require_beta_user


class CollectingLatencyStore:
    def __init__(self) -> None:
        self.records = []

    def append_user_perceived_latency(self, record) -> None:
        self.records.append(record)


class FailingLatencyStore:
    def append_user_perceived_latency(self, record) -> None:
        raise RuntimeError("database unavailable")


def _client(store) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_beta_user] = lambda: "jimmy"
    install_phase1_latency_routes(app, persistence_store=store)
    return TestClient(app)


def test_user_perceived_latency_is_durably_recorded() -> None:
    store = CollectingLatencyStore()
    response = _client(store).post(
        "/api/performance/latency",
        json={
            "operation": "restore_ready",
            "elapsed_ms": 142.5,
            "outcome": "success",
            "detail": "durable_restore",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "recorded", "operation": "restore_ready"}
    assert len(store.records) == 1
    record = store.records[0]
    assert record.user_id == "jimmy"
    assert record.operation == "restore_ready"
    assert record.elapsed_ms == 142.5
    assert record.outcome == "success"
    assert record.detail == "durable_restore"
    assert record.observed_at.tzinfo is not None


def test_latency_persistence_failure_never_breaks_product_request() -> None:
    response = _client(FailingLatencyStore()).post(
        "/api/performance/latency",
        json={
            "operation": "first_connect_ready",
            "elapsed_ms": 4800.0,
            "outcome": "success",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "recorded",
        "operation": "first_connect_ready",
    }
