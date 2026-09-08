from pathlib import Path


def test_mobile_shell_closed_sidebar_cannot_intercept_taps() -> None:
    source = Path("src/fsffl/product/static/explorer.css").read_text(encoding="utf-8")
    assert ".sidebar{pointer-events:none}" in source
    assert ".sidebar.open{pointer-events:auto}" in source
    assert ".mobile-menu{position:relative;z-index:31;pointer-events:auto}" in source


def test_mobile_native_selects_are_not_wrapped_in_horizontal_overflow() -> None:
    source = Path("src/fsffl/product/static/explorer.css").read_text(encoding="utf-8")
    assert ".context-controls{overflow:visible;max-width:none}" in source
    assert ".context-controls select{pointer-events:auto;touch-action:auto}" in source
