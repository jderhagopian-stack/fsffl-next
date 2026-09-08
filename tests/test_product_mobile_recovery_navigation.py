from pathlib import Path


def test_product_shell_emits_context_update_and_builds_direct_mobile_recovery_controls() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "fsffl:product-context-updated" in shell
    assert "renderMobileRecoveryControls" in shell
    assert "mobile-direct-nav" in shell
    assert "mobile-team-chooser" in shell
    assert "await selectTeam(team.team_id)" in shell


def test_mobile_recovery_controls_are_visible_without_off_canvas_navigation() -> None:
    css = Path("src/fsffl/product/static/mobile_touch_fix.css").read_text(encoding="utf-8")
    assert ".mobile-direct-nav" in css
    assert "display:flex" in css
    assert ".mobile-team-chooser" in css
    assert "display:block" in css
    assert "pointer-events:none!important" in css
    assert ".sidebar.open" in css
    assert "pointer-events:auto!important" in css


def test_mobile_recovery_layer_contains_no_model_or_decision_authority() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    css = Path("src/fsffl/product/static/mobile_touch_fix.css").read_text(encoding="utf-8")
    source = shell + css
    for forbidden in (
        "acceptance_probability",
        "expected_wins=",
        "playoff_probability=",
        "fsffl_cardinal_values.reduce",
    ):
        assert forbidden not in source
