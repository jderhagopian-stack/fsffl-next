import json
from dataclasses import dataclass

from fsffl import journey_telemetry as telemetry


def _records(caplog):
    return [
        json.loads(record.message.split("FSFFL_CUSTOMER_JOURNEY ", 1)[1])
        for record in caplog.records
        if "FSFFL_CUSTOMER_JOURNEY " in record.message
    ]


def test_journey_context_emits_only_allowlisted_fields(caplog):
    token, journey_id = telemetry.set_journey_id("12345678-1234-1234-1234-123456789abc")
    try:
        telemetry.emit_journey_event(
            "restore_stage",
            stage="product_context",
            outcome="ready",
            target_state_id="state-opaque",
            raw_user_id="must-not-appear",
        )
    finally:
        telemetry.reset_journey_id(token)

    record = _records(caplog)[0]
    assert record["journey_id"] == journey_id
    assert record["stage"] == "product_context"
    assert record["target_state_id"] == "state-opaque"
    assert "raw_user_id" not in record


def test_persistence_read_trace_reports_application_payload_bytes(caplog):
    @dataclass
    class Artifact:
        payload: dict

    @telemetry.trace_persistence_read("derived_artifact")
    def read_artifact():
        return Artifact(payload={"rooms": [{"position": "QB"}]})

    token, _ = telemetry.set_journey_id(None)
    try:
        read_artifact()
    finally:
        telemetry.reset_journey_id(token)

    record = next(item for item in _records(caplog) if item["event"] == "persistence_read")
    assert record["read_kind"] == "derived_artifact"
    assert record["call_count"] == 1
    assert record["row_count"] == 1
    assert record["payload_json_bytes"] == len(b'{"rooms":[{"position":"QB"}]}')
    assert "payload" not in record


def test_browser_event_batch_is_bounded_and_sanitized(caplog):
    token, _ = telemetry.set_journey_id(None)
    try:
        accepted = telemetry.record_browser_events([
            {"event": "dynasty_generation_mismatch", "outcome": "failure", "attempt": 2,
             "publication_generation_id": "generation-opaque", "player_payload": {"secret": True}}
            for _ in range(100)
        ])
    finally:
        telemetry.reset_journey_id(token)

    records = _records(caplog)
    assert accepted == 80
    assert len(records) == 80
    assert records[0]["event"] == "dynasty_generation_mismatch"
    assert "player_payload" not in records[0]
