from pathlib import Path


def _shell() -> str:
    return Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")


def _refresh() -> str:
    return Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")


def _index() -> str:
    return Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")


def test_shared_readiness_maps_authoritative_lifecycle_phases() -> None:
    source = _shell()
    assert "state.intelligence=await api('/api/intelligence/status')" in source
    assert "queued:[1,'Preparing current intelligence…']" in source
    assert "building_forecasts:[2,'Building projections…']" in source
    assert "refreshing_state:[3,'Refreshing league state…']" in source
    assert "running_simulation:[4,'Running season outlook…']" in source
    assert "building_values:[5,'Building market values…']" in source
    assert "attaching_results:[6,'Attaching current intelligence…']" in source
    assert "completed:[7,'Core intelligence current']" in source


def test_manual_refresh_restarts_readiness_polling() -> None:
    source = _refresh()
    start = source.split("async function maybeStartIntelligenceJob", 1)[1]
    assert "window.fsfflSharedReadiness?.refresh()" in start


def test_interrupted_refresh_is_terminal_and_truthful() -> None:
    shell = _shell()
    refresh = _refresh()
    assert "Refresh interrupted — last-good intelligence retained" in shell
    assert "if(payload.status==='interrupted')" in refresh
    assert "if(payload.job_id&&payload.status==='interrupted')" in refresh
    assert "fsfflCurrentJobId=null" in refresh


def test_readiness_repair_busts_only_repaired_mobile_assets() -> None:
    index = _index()
    shell = _shell()
    assert "/static/forecast_refresh.js?v=20260925-market-beta-corrective2" in index
    assert "/static/product_shell.js?v=20260925-hodor-lifecycle1" in index
    assert "Core intelligence current" in shell


def test_visible_readiness_strip_exposes_manual_refresh_when_idle_even_if_complete() -> None:
    source = _shell()
    assert "fsffl-shared-readiness-refresh" in source
    assert "Refresh Intelligence" in source
    assert "window.fsfflManualIntelligenceRefresh?.()" in source
    assert "const active=fsfflSharedReadinessJobActive()" in source
    assert "Refresh Intelligence" in source
    assert "Refreshing…" in source
    assert "disabled aria-disabled=\"true\"" in source
    assert "!status.complete&&!fsfflSharedReadinessJobActive()" not in source
    assert ".fsffl-shared-readiness-refresh{pointer-events:auto" in source
    assert "display:block!important;pointer-events:auto;overflow:hidden" in source


def test_manual_refresh_bypasses_already_ready_short_circuit() -> None:
    source = _refresh()
    start = source.split("async function maybeStartIntelligenceJob", 1)[1].split(
        "async function maintainFsfflIntelligence", 1
    )[0]
    assert "if(!manual&&intelligencePipelineReady(state.context))" in start
    assert "if(intelligencePipelineReady(state.context))" not in start
    assert "api('/api/intelligence/jobs',{method:'POST'})" in start


def test_manual_refresh_single_flight_survives_server_acceptance() -> None:
    source = _refresh()
    manual = source.split("async function manualIntelligenceRefresh()", 1)[1].split(
        "async function pollIntelligenceJob", 1
    )[0]
    assert "fsfflJobStartInFlight||fsfflCurrentJobId" in manual
    assert "fsfflCurrentJobId=null" not in manual


def test_shared_refresh_acknowledges_tap_before_network_roundtrip() -> None:
    source = _shell()
    render = source.split("function fsfflRenderSharedReadiness()", 1)[1].split(
        "function fsfflStopSharedReadinessPolling", 1
    )[0]
    disabled_index = render.index("refresh.disabled=true")
    label_index = render.index("refresh.textContent='Refreshing…'")
    start_index = render.index("window.fsfflManualIntelligenceRefresh?.()")
    assert disabled_index < start_index
    assert label_index < start_index


def test_restored_complete_context_wins_over_terminal_failed_job() -> None:
    source = _shell()
    snapshot = source.split("function fsfflSharedReadinessSnapshot()", 1)[1].split(
        "function fsfflSharedReadinessMarkup", 1
    )[0]
    complete_index = snapshot.index("const contextComplete=Boolean")
    terminal_complete_index = snapshot.index("&&contextComplete")
    terminal_failure_index = snapshot.index("const prior=Number.isFinite")
    assert complete_index < terminal_complete_index < terminal_failure_index
    assert "label:'Last-good intelligence retained'" in snapshot
    assert "step:FSFFL_SHARED_READINESS_STEPS" in snapshot


def test_mobile_refresh_control_owns_explicit_fourth_grid_column() -> None:
    source = _shell()
    assert "grid-template-columns:14px auto minmax(0,1fr) auto" in source
    assert "grid-template-columns:12px auto minmax(0,1fr) auto" in source
    assert "white-space:nowrap" in source
    assert "min-width:max-content" in source


def test_failed_forecast_readiness_names_blocker_and_usable_roster() -> None:
    source = _shell()
    snapshot = source.split("function fsfflSharedReadinessSnapshot()", 1)[1].split(
        "function fsfflSharedReadinessMarkup", 1
    )[0]
    assert "job?.failure_phase" in snapshot
    assert "state?.intelligence?.served_state?.roster_usable" in snapshot
    assert "state?.intelligence?.blocked_stage" in snapshot
    assert "Forecast blocked — roster State remains usable" in snapshot
    assert "fsfflSharedReadinessPhases[failedPhase][0]" in snapshot
