from pathlib import Path


def test_league_position_map_uses_existing_position_strength_without_new_master_score() -> None:
    source = Path("src/fsffl/product/static/league_position_map.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert "league_position_map.js" in html
    for label in ("Where are the league-wide lineup edges?", "Strongest", "Weakest", "Your team"):
        assert label in source
    assert "position_strengths" in source
    assert "strength_index" in source
    assert "not a new power ranking" in source
    assert "acceptance_probability" not in source
    assert "trade grade" not in source.lower()


def test_league_position_map_suppresses_stale_context_results_and_stays_mobile_friendly() -> None:
    source = Path("src/fsffl/product/static/league_position_map.js").read_text(encoding="utf-8")
    assert "leaguePositionMapContextKey" in source
    assert "captured!==leaguePositionMapContextKey()" in source
    assert "state?.route!=='league_comparison'" in source
    assert "@media(max-width:520px)" in source
