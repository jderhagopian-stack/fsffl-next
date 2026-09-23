from pathlib import Path


def test_league_comparison_consumes_authoritative_atlas_analytics_and_value_contracts() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for evidence in (
        "calculated_competitive_state",
        "expected_wins",
        "position_strengths",
        "strength_index",
        "league_rank",
        "playoff_probability",
        "preseason_expectation",
        "pick_map",
    ):
        assert evidence in source
    assert "api('/api/league/atlas')" in source
    assert "api('/api/league/team-views')" in source
    assert "api('/api/league/value-lenses')" in source
    assert "api('/api/values')" not in source
    assert "team_cardinal_portfolios" not in source
    assert "No team Market total, team Intrinsic total" in source


def test_value_api_exposes_server_owned_team_value_portfolios_without_atlas_consuming_them() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    atlas = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert '"team_market_value_portfolios"' in source
    assert '"team_cardinal_portfolios"' in source
    assert "team_cardinal_portfolios" not in atlas


def test_league_comparison_is_wired_as_a_real_product_surface() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "league_comparison.js" in shell
    assert "renderFsfflLeagueComparison" in shell
    assert "route==='league_comparison'" in shell


def test_league_comparison_has_mobile_first_hierarchy() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    css = Path("src/fsffl/product/static/league_atlas.css").read_text(encoding="utf-8")
    assert ".league-edge-row" in source
    assert "@media(max-width:720px)" in css
    assert ".league-atlas-tabs" in css
    assert ".atlas-race-list{overflow-x:auto}" in css
    assert ".atlas-pick-table{overflow-x:auto}" in css
    assert ".atlas-outlook-list{overflow-x:auto}" in css
