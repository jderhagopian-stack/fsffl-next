from pathlib import Path


APP_JS = Path("src/fsffl/product/static/app.js")
POSTURE_JS = Path("src/fsffl/product/static/opportunity_posture_ui.js")
INDEX_HTML = Path("src/fsffl/product/static/index.html")
LATENCY_PY = Path("src/fsffl/product/latency_observability.py")
WORKSPACE_CACHE_PY = Path("src/fsffl/product/opportunity_workspace_cache.py")


def test_identical_inflight_gets_are_coalesced_but_mutations_are_not() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "const fsfflInFlightGets=new Map()" in source
    assert "if(method!=='GET')return run()" in source
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


def test_build_counter_invokes_frontier_even_if_legacy_button_was_disabled() -> None:
    source = POSTURE_JS.read_text(encoding="utf-8")

    assert "function runCounterDirectly" in source
    assert "action.disabled=false" in source
    assert "window.exploreTradeFrontier" in source
    assert "void runner()" in source


def test_render_captured_logger_receives_endpoint_and_market_cache_timings() -> None:
    latency = LATENCY_PY.read_text(encoding="utf-8")
    workspace = WORKSPACE_CACHE_PY.read_text(encoding="utf-8")

    assert 'logging.getLogger("uvicorn.error")' in latency
    assert 'logging.getLogger("uvicorn.error")' in workspace
    assert "FSFFL hosted request timing" in latency
    assert "FSFFL Market workspace timing" in workspace


def test_static_release_token_advanced_for_repairs() -> None:
    source = INDEX_HTML.read_text(encoding="utf-8")

    assert "20260911-market-latency3" in source
    assert "20260911-market-trade2" not in source
