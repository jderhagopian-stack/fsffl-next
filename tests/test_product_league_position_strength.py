from pathlib import Path


def test_league_position_strength_is_owned_by_the_structural_surface() -> None:
    shim = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")

    assert "compatibility shim" in shim
    assert "Do not append a second League diagnostic" in shim
    assert "api('/api/league/team-views')" in source
    assert "position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "100 = league-average optimized starter production" in source
    assert "build_league_relative_position_strengths" not in source


def test_legacy_position_strength_script_stays_wired_without_competing_rendering() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    shim = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")

    assert '/static/league_position_strength.js?v=' in html
    assert "league_comparison.js" in shim
    assert "MutationObserver" not in shim
    assert "@media(max-width:560px)" in source
