from pathlib import Path


def test_league_position_strength_surface_consumes_backend_indices_only() -> None:
    source = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")

    assert "api('/api/league/team-views')" in source
    assert "view.position_strengths" in source
    assert "row?.strength_index" in source
    assert "row.league_rank" in source
    assert "row.team_count" in source
    assert "row.expected_points" in source
    assert "100 equals league-average optimized starter production" in source
    assert "Presentation does not calculate the index" in source
    assert "build_league_relative_position_strengths" not in source


def test_league_position_strength_is_wired_with_current_beta_release_token() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")

    assert '/static/league_position_strength.js?v=20260909-beta-feedback1' in html
    assert "MutationObserver" in source
    assert "state?.route==='league_comparison'" in source
    assert "@media(max-width:620px)" in source
