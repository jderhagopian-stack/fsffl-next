from pathlib import Path


ROOT = Path("src/fsffl/product/static")
SCRIPT = ROOT / "north_star_trade_center.js"
CSS = ROOT / "north_star_trade_center.css"
INDEX = ROOT / "index.html"
RELEASE = "20260911-trade-center1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_trade_center_is_scan_first_decision_room() -> None:
    source = _read(SCRIPT)
    for phrase in (
        "Trade decision",
        "You give",
        "You get",
        "Your roster",
        "Their roster",
        "Season impact",
        "Lineup movement",
        "Main blocker / risk",
        "What to do next",
        "Methods & evidence",
    ):
        assert phrase in source


def test_trade_center_uses_authoritative_simulation_fields() -> None:
    source = _read(SCRIPT)
    assert "expected_wins" in source
    assert "playoff_probability" in source
    assert "first_place_probability" in source
    assert "First-place odds" in source
    assert "championship_probability" not in source
    assert "50,000" not in source


def test_trade_center_waits_for_simulation_before_final_action() -> None:
    source = _read(SCRIPT)
    assert "Simulation needed" in source
    assert "Finish the changed-roster season comparison before treating this as a completed recommendation." in source
    assert "lastSimulation||result" in source
    assert "simulated&&Boolean(disposition(lastSimulation))" in source


def test_trade_center_preserves_authority_boundaries() -> None:
    source = _read(SCRIPT)
    assert "fetch(" not in source
    assert "/api/" not in source
    assert "acceptance_probability" not in source
    assert "acceptance probability" in source
    assert "roster_adjusted_market_delta" in source
    assert "position_strength" in source
    assert "disposition" in source
    assert "feasibility_shape==='mutual_gain_candidate'" in source


def test_trade_center_remains_asset_generic_for_players_and_picks() -> None:
    source = _read(SCRIPT)
    assert "asset_ref" in source
    assert ".assets" in source
    assert "player_id" not in source


def test_trade_center_legacy_depth_is_drill_down_only() -> None:
    css = _read(CSS)
    source = _read(SCRIPT)
    assert ".ns-trade-legacy{display:none!important}" in css
    assert ".ns-trade-show-methods .ns-trade-legacy{display:block!important}" in css
    assert "ns-trade-methods-toggle" in source


def test_trade_center_assets_load_after_existing_trade_layers() -> None:
    source = _read(INDEX)
    assert f"north_star_trade_center.css?v={RELEASE}" in source
    assert f"north_star_trade_center.js?v={RELEASE}" in source
    assert source.index("trade_center.js") < source.index("north_star_trade_center.js")
    assert source.index("trade_primary_narrative.js") < source.index("north_star_trade_center.js")
