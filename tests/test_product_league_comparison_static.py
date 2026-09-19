from pathlib import Path


def test_league_comparison_consumes_authoritative_analytics_and_optional_value_evidence() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for evidence in (
        "calculated_competitive_state",
        "expected_wins",
        "position_strengths",
        "strength_index",
        "league_rank",
        "draft_picks",
        "team_cardinal_portfolios",
    ):
        assert evidence in source
    assert "api('/api/league/team-views')" in source
    assert "api('/api/values')" in source
    assert "Promise.allSettled" in source
    assert "valueResult.status==='fulfilled'?valueResult.value:null" in source
    assert "FSFFL Cardinal pick value" in source
    assert "one power score" in source


def test_value_api_exposes_server_owned_team_value_portfolios() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '"team_market_value_portfolios"' in source
    assert "for portfolio in evidence.team_market_value_portfolios" in source
    assert '"team_cardinal_portfolios"' in source
    assert "for portfolio in evidence.team_cardinal_portfolios" in source
    assert '"team_name": team_names.get(portfolio.team_id, portfolio.team_id)' in source


def test_league_comparison_is_wired_as_a_real_product_surface() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "league_comparison.js" in shell
    assert "renderFsfflLeagueComparison" in shell
    assert "route==='league_comparison'" in shell


def test_league_comparison_has_mobile_first_hierarchy() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    north_star = Path("src/fsffl/product/static/north_star.css").read_text(encoding="utf-8")
    assert "@media(max-width:560px)" in source
    assert ".league-edge-row" in source
    assert "@media(max-width:900px)" in north_star
    assert ".league-takeaway{order:-1" in north_star
    assert ".league-position-section" in north_star
