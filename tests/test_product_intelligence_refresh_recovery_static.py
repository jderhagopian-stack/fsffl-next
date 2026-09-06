from pathlib import Path


def _source() -> str:
    return Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")


def test_partial_pipeline_exposes_one_refresh_action() -> None:
    source = _source()
    assert "Refresh Intelligence" in source
    assert "manualIntelligenceRefresh" in source
    assert "intelligencePipelineReady(context)" in source
    assert "3 core stages ready" in source


def test_historical_completed_job_cannot_settle_partial_current_state() -> None:
    source = _source()
    assert "fsfflSessionStartedJobId" in source
    assert "if(fsfflSessionStartedJobId===payload.job_id)" in source
    assert "A completed job discovered after the current state is already partial" in source
    completed_branch = source.split("if(payload.job_id&&payload.status==='completed')", 1)[1]
    assert "await maybeStartIntelligenceJob();" in completed_branch


def test_completed_partial_session_stops_auto_loop_and_offers_retry() -> None:
    source = _source()
    assert "fsfflSettledStateId=context.state_id||null" in source
    assert "Core intelligence is incomplete. Refresh to retry" in source
    assert "button.hidden=ready||running" in source


def test_refresh_client_still_defers_model_authority_to_backend() -> None:
    source = _source()
    assert "simulation_count" not in source
    assert "acceptance_probability" not in source
    assert "provisional_fsffl" not in source
