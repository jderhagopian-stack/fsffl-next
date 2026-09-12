from pathlib import Path

ROOT = Path("src/fsffl/product/static")
SCRIPT = ROOT / "north_star_trade_center.js"
CSS = ROOT / "north_star_trade_center.css"
INDEX = ROOT / "index.html"
HANDOFF = ROOT / "trade_workflow_handoff.js"
RELEASE = "20260911-market-trade4"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def test_trade_center_first_screen_answers_north_star_questions() -> None:
    source = _read(SCRIPT)
    for phrase in ("Trade decision","You give","You get","Main upside","Main risk","What to do next","Advanced details / methods & evidence"):
        assert phrase in source
    assert "ns-trade-answer-grid" in source

def test_trade_center_uses_authoritative_simulation_fields_only() -> None:
    source = _read(SCRIPT)
    for field in ("expected_wins","playoff_probability","first_place_probability"):
        assert field in source
    assert "championship_probability" not in source
    assert "50,000" not in source

def test_exact_market_simulation_is_reused_without_duplicate_run() -> None:
    source = _read(SCRIPT)
    handoff = _read(HANDOFF)
    assert "simulationArtifact" in handoff
    assert "simulation reused" in handoff
    assert "fsfflAdoptHandoffSimulation" in handoff
    assert "artifactMatchesCurrent" in source
    assert "ensureAnalysisHost" in source
    assert "if(lastSimulation)return" in source
    assert "scenario_simulation_count" in source

def test_counter_action_has_working_visible_frontier_path() -> None:
    source = _read(SCRIPT)
    assert "Build a counter" in source
    assert "document.querySelector('#explore-price')?.click()" in source
    assert "revealFrontier" in source
    assert "#trade-frontier-result" in source
    assert "ns-trade-show-methods" in source
    assert "feasibility_shape==='mutual_gain_candidate'" in source

def test_trade_center_does_not_rank_cross_unit_upsides_with_display_weights() -> None:
    source = _read(SCRIPT)
    assert "material_gains" in source
    assert "playoff_probability*10" not in source
    assert "roster_adjusted_market_delta/1000" not in source

def test_trade_center_preserves_authority_boundaries() -> None:
    source = _read(SCRIPT)
    assert "fetch(" not in source
    assert "/api/" not in source
    assert "acceptance_probability" not in source
    assert "roster_adjusted_market_delta" in source
    assert "disposition" in source

def test_trade_center_legacy_depth_is_drill_down_only() -> None:
    css = _read(CSS)
    assert ".ns-trade-legacy{display:none!important}" in css
    assert ".ns-trade-show-methods .ns-trade-legacy{display:block!important}" in css

def test_trade_center_assets_load_after_existing_trade_layers() -> None:
    source = _read(INDEX)
    assert f"north_star_trade_center.css?v={RELEASE}" in source
    assert f"north_star_trade_center.js?v={RELEASE}" in source
    assert source.index("trade_center.js") < source.index("north_star_trade_center.js")
    assert source.index("trade_counter_paths.js") < source.index("north_star_trade_center.js")
