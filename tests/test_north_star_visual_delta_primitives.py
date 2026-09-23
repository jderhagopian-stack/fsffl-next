from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "fsffl" / "product" / "static"


def _source(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_shared_delta_primitive_is_global_presentation_grammar() -> None:
    index = _source("index.html")
    css = _source("visual_primitives.css")
    assert "/static/visual_primitives.css?v=20260913-phase3-latency1" in index
    assert "transitional PR #159 delta styling" in css
    assert ".ns-visual-delta{" in css
    assert ".ns-visual-delta__track" in css
    assert 'data-direction="positive"' in css
    assert 'data-direction="negative"' in css
    assert "not the canonical visual benchmark" in css


def test_trade_center_visualizes_both_teams_from_returned_simulation_deltas() -> None:
    source = _source("north_star_trade_center.js")
    assert "seasonImpactComparison" in source
    assert "shiftVisual" in source
    assert "result.focal_team_id" in source
    assert "result.counterparty_team_id" in source
    assert "simRow(result,focalId)?.competitive" in source
    assert "simRow(result,counterpartyId)?.competitive" in source
    for field in ("expected_wins", "playoff_probability", "first_place_probability"):
        assert field in source
    assert "Who moves where after the trade?" in source
    assert "Exact deltas come from Simulation and Team Utility." in source


def test_delta_band_normalizes_only_within_same_returned_metric() -> None:
    source = _source("north_star_trade_center.js")
    assert "magnitudes=[a,b].filter(finite).map(value=>Math.abs(value))" in source
    assert "Math.max(...magnitudes)" in source
    assert "Visual length is normalized only within each same-unit outcome across these two franchises" in source
    assert "adds no model score or materiality threshold" in source
    assert "playoff_probability*10" not in source
    assert "composite_score" not in source
    assert "master_score" not in source


def test_trade_delta_visual_keeps_exact_numbers_visible() -> None:
    source = _source("north_star_trade_center.js")
    assert "shiftVisual(a,maxAbs,metric.format(a),metric.unit,focalLabel,'left')" in source
    assert "shiftVisual(b,maxAbs,metric.format(b),metric.unit,counterLabel,'right')" in source
    assert "nx-shift__number" in source
    assert "signed(value,2)" in source
    assert "pp(value)" in source


def test_trade_delta_visual_is_intentionally_mobile_composed() -> None:
    design = _source("north_star_design_system.css")
    trade = _source("north_star_trade_center.css")
    assert "@media(max-width:640px)" in design
    assert ".nx-impact__teams{display:none}" in design
    assert ".nx-impact__row" in design
    assert "grid-template-columns:1fr" in design
    assert ".nx-shift--left:before" in design
    assert ".ns-trade-room--reference" in trade


def test_trade_center_visual_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "north_star_trade_center.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
