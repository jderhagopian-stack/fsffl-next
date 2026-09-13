from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_value_lens_preserves_four_value_coordinates_and_unavailability():
    script = _text("intrinsic_value_experience.js")
    assert "Broad Market Value" in script
    assert "FSFFL Intrinsic Value" in script
    assert "League Market Value" in script
    assert "Team Utility" in script
    assert "Not production-ready" in script
    assert "No substitute number is shown" in script
    assert "will not silently use one in place of Intrinsic" in script


def test_value_lens_uses_governed_intrinsic_api_and_does_not_rebrand_legacy_value():
    script = _text("intrinsic_value_experience.js")
    assert "api('/api/value/intrinsic-v1')" in script
    assert "provisional_fsffl_values" not in script
    assert "fsffl_cardinal_values" not in script
    assert "older generic “FSFFL Value”" in script
    assert "is not this Intrinsic value" in script
    assert "FSFFL Cardinal Value" in script
    assert "replaceTextWithin(document.querySelector('.franchise-shell'),'FSFFL Value','FSFFL Cardinal Value')" in script
    assert "replaceTextWithin(document.querySelector('.league-structure-panel'),'Total FSFFL value','Total FSFFL Cardinal Value')" in script


def test_value_lens_comparison_is_rank_only_and_not_a_fake_common_scale():
    script = _text("intrinsic_value_experience.js")
    assert "percentile rank only as a presentation aid" in script
    assert "Broad Market and Intrinsic use different units" in script
    assert "does <strong>not</strong> subtract the raw numbers" in script
    assert "not an automatic buy signal" in script
    assert "not an automatic sell signal" in script


def test_value_lens_is_lazy_and_does_not_add_an_intrinsic_request_to_first_paint():
    script = _text("intrinsic_value_experience.js")
    bootstrap = _text("league_position_strength.js")
    assert "button.addEventListener('click',()=>activate(shell))" in script
    assert "function activate(panel)" in script
    assert "load()" in script
    assert "api('/api/value/intrinsic-v1')" in script
    # Eager bootstrap only attaches static assets; it performs no API request.
    assert "/api/value/intrinsic-v1" not in bootstrap
    assert "the lens itself performs no API work until the customer opens its tab" in bootstrap


def test_value_lens_surfaces_confidence_and_provenance_secondarily():
    script = _text("intrinsic_value_experience.js")
    assert "Confidence" in script
    assert "Evidence & provenance" in script
    assert "forecast_policy_version" in script
    assert "base_forecast_model_version" in script
    assert "replacement_context_version" in script
    assert "What exactly is FSFFL Intrinsic Value?" in script


def test_value_lens_has_intentional_mobile_layout():
    css = _text("intrinsic_value_experience.css")
    assert "@media(max-width:680px)" in css
    assert ".value-lens-coordinates{grid-template-columns:1fr}" in css
    assert ".value-lens-player summary{grid-template-columns:1fr 1fr" in css
    assert ".franchise-tabs{overflow-x:auto" in css
