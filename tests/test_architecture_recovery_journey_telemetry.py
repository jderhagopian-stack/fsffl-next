import hashlib
import json
import logging
from pathlib import Path

import pytest
from dataclasses import dataclass

from fsffl import journey_telemetry as telemetry


@pytest.fixture(autouse=True)
def _capture_journey_logs(caplog):
    caplog.set_level(logging.INFO, logger="uvicorn.error")


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
    assert record["artifact_kind"] == "derived_artifact"
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


def test_restore_stage_has_opaque_run_identity_without_browser_context(caplog):
    @telemetry.trace_restore_stage("state_activation")
    def activate_state():
        return "ready"

    activate_state()

    record = next(item for item in _records(caplog) if item["event"] == "restore_stage")
    assert record["stage"] == "state_activation"
    assert record["outcome"] == "ready"
    assert len(record["restore_id"]) == 36
    assert "journey_id" not in record


def test_dynasty_failure_remains_a_failure_and_success_requires_exact_visible_generation():
    atlas = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    browser = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    assert "payload?.publication_generation_id!==requestedGeneration" in atlas
    assert "dynasty_generation_mismatch" in atlas
    assert "dynasty_request_failed" in atlas
    assert "fsfflFlushJourney?.()" in atlas
    assert "rooms.publication_generation_id!==atlas.publication_generation_id" in atlas
    assert "document.visibilityState!=='visible'" in atlas
    assert "panel?.querySelector('[data-position-view=\"dynasty\"].active')" in atlas
    assert "memory_supported" in atlas
    assert "X-FSFFL-Journey-ID" in browser
    assert "X-FSFFL-Restore-ID" in browser



def test_api_paths_with_identifiers_are_redacted(caplog):
    token, _ = telemetry.set_journey_id(None)
    try:
        telemetry.emit_journey_event(
            "request_complete",
            api_path="/api/player-intelligence/private-user-id",
            outcome="success",
        )
    finally:
        telemetry.reset_journey_id(token)

    record = _records(caplog)[0]
    assert record["api_path"] == "/api/other"
    assert "private-user-id" not in record["api_path"]


def test_saved_session_app_asset_and_event_merge_keep_generations_distinct():
    app = Path("src/fsffl/product/static/app.js").read_bytes()
    app_blob_hash = hashlib.sha1(
        b"blob " + str(len(app)).encode() + bytes([0]) + app
    ).hexdigest()[:12]
    index = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    source = app.decode("utf-8")

    assert f"/static/app.js?v=20261004-safari-restore380&c=git-{app_blob_hash}" in index
    assert "item.target_state_id===fields.target_state_id" in source
    assert "item.publication_generation_id===fields.publication_generation_id" in source


def test_startup_does_not_probe_unused_legacy_presentation_payloads():
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")
    startup = source.split("def _run_lightweight_startup_restore", 1)[1].split(
        "def _start_lightweight_startup_restore", 1
    )[0]

    assert "legacy_snapshot_available" not in startup
    assert "_prepare_presentation_for_user(_beta_restore_user, context)" in startup
    assert "_promote_presentation_for_user" in startup
