from pathlib import Path


def test_accessibility_layer_supports_keyboard_and_navigation_context() -> None:
    source = Path("src/fsffl/product/static/accessibility.js").read_text(encoding="utf-8")
    assert "Skip to main content" in source
    assert "aria-current" in source
    assert "aria-disabled" in source
    assert "aria-expanded" in source
    assert "event.key==='Escape'" in source
    assert ":focus-visible" in source


def test_accessibility_layer_respects_touch_and_reduced_motion() -> None:
    source = Path("src/fsffl/product/static/accessibility.js").read_text(encoding="utf-8")
    assert "@media(pointer:coarse)" in source
    assert "min-height:44px" in source
    assert "@media(prefers-reduced-motion:reduce)" in source
    assert "Swipe horizontally for more" in source


def test_product_shell_loads_accessibility_without_business_logic() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/accessibility.js").read_text(encoding="utf-8")
    assert "ensureAccessibilityScript" in shell
    assert "installFsfflAccessibility" in shell
    for forbidden in ("expected_wins", "playoff_probability", "fsffl_cardinal_values", "acceptance_probability"):
        assert forbidden not in source
