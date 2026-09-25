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
    assert "completed:[7,'Intelligence current']" in source


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
    assert "/static/forecast_refresh.js?v=20260924-readiness-control7" in index
    assert "/static/product_shell.js?v=20260924-readiness-control7" in index


def test_visible_readiness_strip_exposes_manual_refresh_when_idle_even_if_complete() -> None:
    source = _shell()
    assert "fsffl-shared-readiness-refresh" in source
    assert "Refresh Intelligence" in source
    assert "window.fsfflManualIntelligenceRefresh?.()" in source
    assert "const refreshAction=(!fsfflSharedReadinessJobActive())?" in source
    assert "!status.complete&&!fsfflSharedReadinessJobActive()" not in source
    assert ".fsffl-shared-readiness-refresh{pointer-events:auto" in source


def test_manual_refresh_bypasses_already_ready_short_circuit() -> None:
    source = _refresh()
    start = source.split("async function maybeStartIntelligenceJob", 1)[1].split(
        "async function maintainFsfflIntelligence", 1
    )[0]
    assert "if(!manual&&intelligencePipelineReady(state.context))" in start
    assert "if(intelligencePipelineReady(state.context))" not in start
    assert "api('/api/intelligence/jobs',{method:'POST'})" in start
