from pathlib import Path

ROOT = Path("src/fsffl/product/static")
SCRIPT = ROOT / "market_trade_recomposition.js"
CSS = ROOT / "market_trade_recomposition.css"
INDEX = ROOT / "index.html"
RELEASE = "20260911-market-trade4"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_recomposition_loads_last_with_current_release() -> None:
    source = _read(INDEX)
    assert f"market_trade_recomposition.css?v={RELEASE}" in source
    assert f"market_trade_recomposition.js?v={RELEASE}" in source
    assert source.index("north_star_trade_center.js") < source.index("market_trade_recomposition.js")


def test_market_removes_redundant_players_mode_and_keeps_waiver_workflow() -> None:
    source = _read(SCRIPT)
    assert 'nav.querySelector(\'[data-ns-mode="players"]\')?.remove()' in source
    assert "s.nsMode='waivers'" in source
    assert "s.tab='free_agents'" in source
    assert "Waiver / Add-Drop" in source


def test_market_focus_uses_touch_friendly_controls_without_new_scoring() -> None:
    source = _read(SCRIPT)
    css = _read(CSS)
    assert "ns-focus-choice" in source
    assert "select.dispatchEvent(new Event('change',{bubbles:true}))" in source
    assert "touch-action:manipulation" in css
    assert "applyServerPostureView" not in source
    assert "acceptance_probability" not in source


def test_market_discovery_does_not_auto_run_expensive_full_trade_evaluation() -> None:
    source = _read(SCRIPT)
    assert "installMarketEvaluationBoundary" in source
    assert "const suppressed=function(){return Promise.resolve(null)}" in source
    assert "Evaluate in Trade Center" in source
    assert "What Search already knows" in source


def test_analyze_trade_is_one_visible_flow_through_analysis_then_simulation() -> None:
    source = _read(SCRIPT)
    assert "async function runFullTradeEvaluation" in source
    assert "await analyze()" in source
    assert "await simulate()" in source
    assert "Running season impact" in source
    assert "Finishing the trade evaluation" in source


def test_single_trade_room_surfaces_useful_evidence_before_methods() -> None:
    source = _read(SCRIPT)
    css = _read(CSS)
    for phrase in (
        "FSFFL Value after cuts",
        "Expected wins",
        "Playoff odds",
        "First-place odds",
        "Projected starter points by position",
        "Main upside",
        "Main risk",
        "What to do next",
        "Methods & evidence",
    ):
        assert phrase in source
    assert "#trade-center-screen.ns2-trade-center .ns-trade-legacy" in css
    assert "#trade-center-screen.ns2-trade-center .trade-preliminary-read" in css
    assert "#trade-center-screen.ns2-trade-center .authoritative-trade-decision" in css


def test_counter_result_stays_at_launch_point_and_recomposition_does_not_call_apis_directly() -> None:
    source = _read(SCRIPT)
    assert "id=\"ns2-counter-zone\"" in source
    assert "Searching nearby counter packages" in source
    assert "Best returned counter paths" in source
    assert "await runner()" in source
    assert "fetch(" not in source
    assert "/api/" not in source
