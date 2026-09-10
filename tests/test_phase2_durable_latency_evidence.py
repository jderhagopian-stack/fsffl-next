from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.persistence.base import UserPerceivedLatencyRecord
from fsffl.product.phase1_latency import install_phase1_latency_routes


class CollectingLatencyStore:
    def __init__(self) -> None:
        self.records: list[UserPerceivedLatencyRecord] = []

    def append_user_perceived_latency(self, record: UserPerceivedLatencyRecord) -> None:
        self.records.append(record)


def _client(store: CollectingLatencyStore) -> TestClient:
    application = FastAPI()
    install_phase1_latency_routes(application, persistence_store=store)  # type: ignore[arg-type]
    return TestClient(application)


def test_latency_event_is_persisted_as_additive_observability_evidence() -> None:
    store = CollectingLatencyStore()
    response = _client(store).post(
        "/api/performance/latency",
        json={
            "operation": "restore_ready",
            "elapsed_ms": 321.5,
            "outcome": "success",
            "detail": "stored state restored",
        },
    )

    assert response.status_code == 200
    assert len(store.records) == 1
    record = store.records[0]
    assert record.operation == "restore_ready"
    assert record.elapsed_ms == 321.5
    assert record.outcome == "success"
    assert record.detail == "stored state restored"


def test_non_finite_latency_is_rejected_before_persistence() -> None:
    store = CollectingLatencyStore()
    response = _client(store).post(
        "/api/performance/latency",
        json={
            "operation": "restore_ready",
            "elapsed_ms": "NaN",
            "outcome": "success",
        },
    )

    assert response.status_code == 422
    assert store.records == []
