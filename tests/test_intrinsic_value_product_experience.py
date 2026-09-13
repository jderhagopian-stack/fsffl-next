from pathlib import Path
import shutil
import subprocess

import pytest


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_value_lens_preserves_four_value_coordinates_and_unavailability():
    script = _text("intrinsic_value_experience.js")
    assert "Broad Market Value" in script
    assert "FSFFL Intrinsic Value" in script
    assert "League Market Value" in script
    assert "Team Utility" in script
    assert "No substitute number is shown" in script


def test_value_lens_uses_fundamental_intrinsic_api_and_market_cardinal_magnitude():
    script = _text("intrinsic_value_experience.js")
    assert "api('/api/value/intrinsic-v2')" in script
    assert "api('/api/value/intrinsic-v1')" not in script
    assert "fsffl-market-cardinal" in script
    assert "fsffl_cardinal_values" in script
    assert "estimate.display_value" in script
    assert "fundamental_value" in script
    assert "raw_fundamental_career_value" in script


def test_value_lens_states_comparable_presentation_but_independent_derivation():
    script = _text("intrinsic_value_experience.js")
    assert "Both use a familiar 0–10,000 presentation language" in script
    assert "neither is derived from the other" in script
    assert "disagreement is a reason to investigate, not a BUY/SELL command" in script
    assert "Replacement surplus" in script
    assert "Team Utility" in script


def test_value_lens_is_lazy_and_does_not_add_intrinsic_request_to_first_paint():
    script = _text("intrinsic_value_experience.js")
    bootstrap = _text("league_position_strength.js")
    assert "button.addEventListener('click',()=>activate(shell))" in script
    assert "function activate(panel)" in script
    assert "api('/api/value/intrinsic-v2')" in script
    assert "/api/value/intrinsic-v2" not in bootstrap
    assert "the lens itself performs no API work until the customer opens its tab" in bootstrap


def test_value_lens_surfaces_long_horizon_provenance_without_replacement_context():
    script = _text("intrinsic_value_experience.js")
    assert "Confidence" in script
    assert "Evidence & provenance" in script
    assert "forecast_policy_version" in script
    assert "base_forecast_model_version" in script
    assert "terminal.model_version" in script
    assert "post-Year-3 continuation" in script
    assert "replacement_context_version" not in script


def test_value_lens_has_intentional_mobile_layout():
    css = _text("intrinsic_value_experience.css")
    assert "@media(max-width:680px)" in css
    assert ".value-lens-coordinates{grid-template-columns:1fr}" in css
    assert ".value-lens-player summary{grid-template-columns:1fr 1fr" in css
    assert ".franchise-tabs{overflow-x:auto" in css


def test_value_lens_browser_script_parses():
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "intrinsic_value_experience.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_value_lens_request_generation_guard_is_authoritative():
    script = _text("intrinsic_value_experience.js")
    assert "requestGeneration=0" in script
    assert "requestIsCurrent(generation,sid)" in script
    assert "if(!requestIsCurrent(generation,sid))return" in script
    assert "requestGeneration+=1" in script
    assert "if(inFlight?.generation===generation&&inFlight?.stateId===sid)inFlight=null" in script


def test_value_lens_bootstrap_cache_key_is_bumped_consistently():
    html = _text("index.html")
    bootstrap = _text("league_position_strength.js")
    experience = _text("intrinsic_value_experience.js")
    shell_version = "20260913-phase3-latency1"
    experience_version = "20260913-fundamental-intrinsic-v3"
    assert f'/static/league_position_strength.js?v={shell_version}' in html
    assert f"const version='{experience_version}'" in bootstrap
    assert f"const VERSION='{experience_version}'" in experience
    assert f'/static/intrinsic_value_experience.css?v=${{version}}' in bootstrap
    assert f'/static/intrinsic_value_experience.js?v=${{version}}' in bootstrap
