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
    assert "building_intrinsic:[6,'Building FSFFL Intrinsic…']" in source
    assert "attaching_results:[6,'Attaching current intelligence…']" in source
    assert "completed:[7,'Build lifecycle complete']" in source
    assert "capability_readiness" in source
    assert "fsfflCapabilityChip('Intrinsic','intrinsic')" in source
    assert "fsfflReadinessAsOf" in source


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


def test_readiness_recovery_busts_refresh_asset_without_churning_unchanged_shell() -> None:
    index = _index()
    shell = _shell()
    assert "/static/forecast_refresh.js?v=20260928-first-load-recovery1" in index
    assert "/static/product_shell.js?v=20260927-market-nonblocking1" in index
    assert "/static/home_dashboard.js?v=20260927-market-nonblocking1" in index
    assert "Build lifecycle complete" in shell
    assert "Core intelligence current · FSFFL Intrinsic unavailable" in shell
    assert "As of " in shell
    assert "const fsfflStaticVersion='20260927-dualstate1';" in shell
    assert "const leagueAtlasStaticVersion='20260927-dualstate1';" in shell


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


def test_full_capability_context_wins_over_terminal_failed_job() -> None:
    source = _shell()
    snapshot = source.split("function fsfflSharedReadinessSnapshot()", 1)[1].split(
        "function fsfflSharedReadinessMarkup", 1
    )[0]
    capability_index = snapshot.index("const capabilityFull=")
    terminal_complete_index = snapshot.index("&&capabilityFull")
    terminal_failure_index = snapshot.index("const prior=Number.isFinite")
    assert capability_index < terminal_complete_index < terminal_failure_index
    assert "label:'Last-good intelligence identity retained; current capability truth shown'" in snapshot
    assert "step:FSFFL_SHARED_READINESS_STEPS" in snapshot


def test_mobile_terminal_readiness_uses_two_column_compact_layout() -> None:
    source = _shell()
    assert "grid-template-columns:14px auto minmax(0,1fr) auto" in source
    assert 'grid-template-columns:minmax(0,1fr) auto;grid-template-areas:"status refresh" "detail detail"' in source
    assert ".fsffl-shared-readiness-mark{display:none}" in source
    assert "overflow-wrap:normal;word-break:normal" in source
    assert "overflow-wrap:anywhere" not in source
    assert "min-height:0!important" in source


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



def test_mobile_full_readiness_collapses_to_one_current_state_and_hides_redundant_chips() -> None:
    source = _shell()
    assert "✓ Intelligence current" in source
    assert "fsffl-readiness-mobile-step" in source
    assert ".fsffl-capability-summary{display:none!important}" in source
    assert ".fsffl-shared-readiness-mark{display:none}" in source
    assert "fsffl-shared-readiness-refresh" in source


def test_mobile_readiness_never_renders_capability_pill_swarm_in_terminal_card() -> None:
    source = _shell()
    assert ".fsffl-capability-summary{display:none!important}" in source
    assert (
        ".fsffl-shared-readiness-strip.complete .fsffl-shared-readiness-copy,"
        ".fsffl-shared-readiness-strip.partial .fsffl-shared-readiness-copy,"
        ".fsffl-shared-readiness-strip.failed .fsffl-shared-readiness-copy{display:none}"
    ) in source
    assert "fsfflMobileCapabilityException(status)" in source
    assert "'◐ Intelligence partial · '+fsfflMobileCapabilityException(status)" in source
    assert "status.step+' / '+status.total" in source
    assert "Refreshing…" in source



def test_product_readiness_never_false_greens_when_intrinsic_or_league_surface_is_unavailable() -> None:
    source = _shell()
    snapshot = source.split("function fsfflSharedReadinessSnapshot()", 1)[1].split(
        "function fsfflCapabilityChip", 1
    )[0]
    assert "capabilities?.overall_status==='full'" in snapshot
    assert "const surfaceIssue=fsfflSurfaceReadinessIssue()" in snapshot
    assert "const capabilityFull=serverFull&&!surfaceIssue" in snapshot
    assert "Core intelligence current · FSFFL Intrinsic unavailable" in snapshot
    assert "Core intelligence current · '+surfaceIssue" in snapshot
    assert "league_comparison==='failed'" in source
    assert "fsfflSetSurfaceHealth('league_comparison','failed')" in source


def test_readiness_as_of_is_derived_from_governed_payload_not_browser_now() -> None:
    source = _shell()
    helper = source.split("function fsfflReadinessAsOf()", 1)[1].split(
        "function fsfflSurfaceReadinessIssue", 1
    )[0]
    assert "const readiness=fsfflCapabilityReadiness()" in helper
    assert "readiness?.as_of" in helper
    assert "readiness.served_last_good.as_of" in helper
    assert "served_state?.as_of" in helper
    assert "context?.evidence_as_of" in helper
    assert "new Date()" not in helper
    assert "Date.now()" not in helper



def test_mobile_readiness_scopes_current_capabilities_and_preserves_build_phase_detail() -> None:
    source = _shell()
    assert "fsfflCapabilityChip('Current Forecast','forecast')" in source
    assert "fsfflCapabilityChip('Current Value','current_value')" in source
    assert "['Intrinsic','intrinsic']" in source
    assert "['Simulation','simulation']" in source
    assert "grid-area:detail" in source
    assert "white-space:nowrap" in source
    # The working in-progress lifecycle remains a two-row compact treatment:
    # numeric phase in the status row and the server phase message in detail.
    assert "phaseLabel+(lastGoodAvailable?' · Last-good available':'')" in source



def test_dual_state_rebuild_never_renders_false_green_current_status() -> None:
    source = _shell()
    snapshot = source.split("function fsfflSharedReadinessSnapshot()", 1)[1].split(
        "function fsfflCapabilityChip", 1
    )[0]
    assert "capabilities?.overall_status==='rebuilding'" in snapshot
    assert "State current · intelligence rebuilding · last-good identity remains durable" in snapshot
    assert "rebuilding" in snapshot
    assert "capabilityFull" in snapshot

    markup = source.split("function fsfflSharedReadinessMarkup", 1)[1].split(
        "function fsfflSharedReadinessHost", 1
    )[0]
    assert "status.rebuilding?'◐ State current · intelligence rebuilding'" in markup
    assert "✓ Intelligence current" in markup


def test_first_load_release_busts_only_changed_session_flow_assets() -> None:
    index = _index()
    for script in ("app.js", "mobile_safari_recovery.js", "forecast_refresh.js"):
        assert f"/static/{script}?v=20260928-first-load-recovery1" in index
    for script in ("session_recovery.js", "home_dashboard.js", "product_shell.js"):
        assert f"/static/{script}?v=20260927-market-nonblocking1" in index
