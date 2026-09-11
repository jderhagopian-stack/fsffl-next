from pathlib import Path


def test_legacy_position_map_is_only_a_compatibility_shim() -> None:
    source = Path("src/fsffl/product/static/league_position_map.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    league = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")

    assert "league_position_map.js" in html
    assert "compatibility shim" in source
    assert "Do not append duplicate League content" in source
    assert "position_strengths" in league
    assert "strength_index" in league
    assert "league_rank" in league
    assert "hidden power rating" in league
    assert "acceptance_probability" not in league


def test_phase3_position_map_is_owned_by_single_mobile_friendly_league_surface() -> None:
    source = Path("src/fsffl/product/static/league_position_map.js").read_text(encoding="utf-8")
    league = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    north_star = Path("src/fsffl/product/static/north_star.css").read_text(encoding="utf-8")

    assert "league_comparison.js" in source
    assert "lcPositionMatrix" in league
    assert "@media(max-width:560px)" in league
    assert ".league-takeaway{order:-1" in north_star
