from pathlib import Path


def test_league_comparison_consumes_authoritative_analytics_and_value_metrics() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for metric in (
        "expected_wins",
        "playoff_probability",
        "optimized_expected_points",
        "total_cardinal_value",
        "draft_pick_count",
    ):
        assert metric in source
    assert "/api/league/chart?metric=" in source
    assert "api('/api/values')" in source
    assert "team_cardinal_portfolios" in source
    assert "browser does not sum asset prices" in source
    assert "does not calculate new scores or rankings" in source


def test_value_api_exposes_server_owned_team_cardinal_portfolios() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '"team_cardinal_portfolios"' in source
    assert "for portfolio in evidence.team_cardinal_portfolios" in source
    assert '"team_name": team_names.get(portfolio.team_id, portfolio.team_id)' in source


def test_league_comparison_is_wired_as_a_real_product_surface() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "league_comparison.js" in shell
    assert "renderFsfflLeagueComparison" in shell
    assert "route==='league_comparison'" in shell


def test_league_comparison_has_mobile_first_layout() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "@media(max-width:620px)" in source
    assert ".league-comparison-tiles{grid-template-columns:1fr}" in source
