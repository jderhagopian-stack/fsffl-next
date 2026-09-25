from pathlib import Path


APP_JS = Path("src/fsffl/product/static/app.js")
POSTURE_JS = Path("src/fsffl/product/static/opportunity_posture_ui.js")
INDEX_HTML = Path("src/fsffl/product/static/index.html")
LATENCY_PY = Path("src/fsffl/product/latency_observability.py")
WORKSPACE_CACHE_PY = Path("src/fsffl/product/opportunity_workspace_cache.py")


def test_identical_inflight_gets_are_coalesced_and_invalidated_by_mutations() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "const fsfflInFlightGets=new Map()" in source
    assert "let fsfflReadGeneration=0" in source
    assert "fsfflReadGeneration+=1" in source
    assert "`${fsfflReadGeneration}|${path}|${JSON.stringify(headers)}`" in source
    assert "const pending=run().finally" in source
    assert "fsfflInFlightGets.delete(key)" in source


def test_market_focus_is_opportunities_only_and_anchored_to_mode_nav() -> None:
    source = POSTURE_JS.read_text(encoding="utf-8")

    assert "currentMarketMode()!=='opportunities'" in source
    assert "control?.remove()" in source
    assert "panel.querySelector('.ns-market-mode-nav')" in source
    assert "nav.insertAdjacentElement('afterend',control)" in source


def test_player_browse_hands_off_to_distinct_waiver_workspace() -> None:
    source = POSTURE_JS.read_text(encoding="utf-8")

    assert ".ns-market-players-mode .opp-waiver-evaluator{display:none!important}" in source
    assert "function openPlayerInWaivers" in source
    assert "s.nsMode='waivers'" in source
    assert "s.waiverAdd=player" in source
    assert "event.stopImmediatePropagation()" in source


def test_build_counter_runs_once_then_reveals_completed_frontier() -> None:
    source = POSTURE_JS.read_text(encoding="utf-8")

    assert "function runCounterDirectly" in source
    assert "frontier?.textContent?.trim()" in source
    assert "action.disabled=false" in source
    assert "window.exploreTradeFrontier" in source
    assert "Promise.resolve(runner()).then" in source
    assert "root.classList.add('ns-trade-show-methods')" in source
    assert "#trade-frontier-result" in source


def test_render_captured_logger_receives_endpoint_and_market_cache_timings() -> None:
    latency = LATENCY_PY.read_text(encoding="utf-8")
    workspace = WORKSPACE_CACHE_PY.read_text(encoding="utf-8")

    assert 'logging.getLogger("uvicorn.error")' in latency
    assert 'logging.getLogger("uvicorn.error")' in workspace
    assert "FSFFL hosted request timing" in latency
    assert "FSFFL Market workspace timing" in workspace


def test_static_release_token_advanced_for_repairs() -> None:
    source = INDEX_HTML.read_text(encoding="utf-8")

    assert "20260925-hodor-lifecycle1" in source
    assert "20260913-phase3-intrinsic2" not in source


def test_performance_corrective_reuses_work_without_changing_market_authority() -> None:
    focused = (PRODUCT / "focused_opportunity_routes.py").read_text(encoding="utf-8")
    discovery = (PRODUCT / "market_discovery_runtime.py").read_text(encoding="utf-8")
    hosted = (PRODUCT / "persistent_webapp.py").read_text(encoding="utf-8")

    assert "candidate_limit=0" in focused
    assert "evaluation_limit=DEFAULT_PRELIMINARY_DECISION_BUDGET" in focused
    assert "asset_index=owned_asset_index(browser)" in focused
    assert "def focused_evaluator" not in focused

    assert "DEFAULT_PRELIMINARY_DECISION_BUDGET = 8" in discovery
    assert "select_preliminary_screen_indices(seeds, limit=evaluation_limit)" in discovery
    assert '"changed_state_simulation_calls_during_discovery": 0' in discovery
    assert '"acceptance_probability": None' in discovery
    assert "_prune_package_neighborhood" in discovery
    assert "select_for_you(opportunities, by_id)" in discovery

    assert "make_cached_candidate_economics" in hosted
    assert "_market_discovery_runtime.evaluate_candidate_economics" in hosted
