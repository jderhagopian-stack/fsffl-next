"""Render Workflows entrypoint for FSFFL nonproduction real-artifact storage proof.

Registration executes no database/storage work. Tasks accept ZERO user inputs:
the Dashboard "Start Task" dialog must contain [] and NEVER a credential.
Service environment belongs to this isolated workflow, not production web.
"""
from __future__ import annotations

from render import Retry, TaskContext, Workflows

app = Workflows(default_plan="flex", default_timeout=180)


@app.task(name="preflight", retry=Retry(max_retries=0), timeout_seconds=60, plan="flex")
def preflight(ctx: TaskContext) -> dict[str, object]:
    """Offline smoke of frozen PR #439 adapter; no credentials, DB or cloud."""
    import tempfile
    from pathlib import Path
    from hybrid_adapter import ArtifactIdentity, HybridPrototype, LocalObjectStore, Metadata

    with tempfile.TemporaryDirectory(prefix="fsffl-p2-preflight-") as tmp:
        i = ArtifactIdentity(
            "synthetic-test-only", "current_forecast_evidence", "league_state",
            "fixture-state", "fixture-fingerprint", "fixture-model", "2026-10-09T00:00:00Z"
        )
        prototype = HybridPrototype(
            LocalObjectStore(Path(tmp) / "objects"),
            Metadata(Path(tmp) / "local.db"),
        )
        original = {"fixture": True, "trial_count": 50000, "values": [1.0, 2.0]}
        saved = prototype.put(i, original)
        loaded = prototype.get(i)
        assert loaded is not None and loaded["payload"] == original
        prototype.metadata.close()
        assert saved["raw_bytes"] > 0 and saved["stored_bytes"] > 0
    # No secret or user data is serialized into Render's 30-day task state.
    return {"status": "PASS", "scope": "synthetic_preflight_no_production_access"}


@app.task(
    name="validate_real_artifacts", retry=Retry(max_retries=0),
    timeout_seconds=180, plan="flex"
)
def validate_real_artifacts(ctx: TaskContext) -> dict[str, object]:
    """Two read-only PostgreSQL artifacts, temporary PRIVATE S3 writes only."""
    import os
    required = (
        "FSFFL_DATABASE_URL",
        "FSFFL_TEST_S3_ACCESS_KEY_ID",
        "FSFFL_TEST_S3_SECRET_ACCESS_KEY",
    )
    if any(not os.environ.get(name) for name in required):
        # Never name or print environment variable values.
        raise RuntimeError("BLOCKED: workflow-only private credentials not configured")
    from render_s3_real_artifact_gate import run
    try:
        return run(workflow=True)
    except Exception as exc:
        # Protect task logs/state from backend error text, payloads or secrets.
        # Do not use "from exc": suppress sensitive chained trace messages.
        raise RuntimeError("NO-GO: private validation failed; review sanitized gate") from None


if __name__ == "__main__":
    app.start()
