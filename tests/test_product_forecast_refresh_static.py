from pathlib import Path


def test_intelligence_refresh_is_league_scoped_not_team_scoped() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "!state?.context?.league_id" in source
    assert "!state?.context?.team_id" not in source
    assert "'/api/intelligence/jobs'" in source


def test_mobile_client_polls_server_owned_job_instead_of_holding_long_request() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "pollIntelligenceJob" in source
    assert "'/api/intelligence/jobs/current'" in source
    assert "'/api/intelligence/refresh-forecasts'" not in source
    assert "setInterval(maintainFsfflIntelligence,2500)" in source


def test_job_progress_has_single_stable_presentation_owner() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "phaseMessage(payload)" in source
    assert "payload.status==='queued'||payload.status==='running'" in source
    assert "refreshVisibleEvidenceIfAdvanced" in source
    assert "intelligencePipelineReady" in source
    assert "#runtime-status-title" in source
    assert "#runtime-status-summary" not in source


def test_completed_or_failed_job_does_not_poll_forever_when_value_has_no_estimates() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "fsfflSettledStateId" in source
    assert "settleCompletedJob" in source
    assert "settleFailedJob" in source
    assert "Value finished without an authoritative estimate set." in source


def test_server_started_current_state_job_surfaces_terminal_failure() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    maintain = source.split("async function maintainFsfflIntelligence()", 1)[1]

    assert "fsfflSessionStartedJobId=payload.job_id" in maintain
    assert "failureTargetsVisibleState" in maintain
    assert "payload.league_state_id===state.context.state_id" in maintain
    assert "settleFailedJob(payload)" in maintain
    assert maintain.index("failureTargetsVisibleState") < maintain.index("settleFailedJob(payload)")


def test_foreground_context_uses_cached_replay_diagnostics_only() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    payload = source.split("def _runtime_context_payload", 1)[1].split("def _job_payload", 1)[0]
    status = source.split('@application.get("/api/intelligence/status")', 1)[1].split(
        '@application.post("/api/connect/sleeper")', 1
    )[0]

    assert "_cached_forecast_replay_decision(" in payload
    assert "_cached_forecast_replay_decision(" in status
    assert 'getattr(store, "forecast_replay_decision")' not in payload
    assert 'getattr(store, "forecast_replay_decision")' not in status


def test_first_team_handoff_resets_stale_settlement_and_starts_current_enrichment() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    handoff = source.split("window.fsfflEnsureIntelligenceAfterTeamSelection=()=>{", 1)[1].split(
        "window.addEventListener('load'", 1
    )[0]
    assert "fsfflSettledStateId=null" in handoff
    assert "maybeStartIntelligenceJob({manual:false})" in handoff
