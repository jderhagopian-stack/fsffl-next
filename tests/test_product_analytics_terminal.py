from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_analytics_terminal_consumes_existing_authoritative_outputs() -> None:
    ui = (ROOT / "src/fsffl/product/static/analytics_terminal.js").read_text()
    for path in (
        "/api/league/team-views",
        "/api/league/value-lenses",
        "/api/intelligence/status",
        "/api/league/chart?metric=",
    ):
        assert path in ui
    for metric in (
        "expected_wins",
        "playoff_probability",
        "optimized_expected_points",
        "asset_portfolio_mean",
        "draft_pick_count",
    ):
        assert metric in ui


def test_owner_facing_analytics_uses_shared_market_intrinsic_value_language() -> None:
    ui = (ROOT / "src/fsffl/product/static/analytics_terminal.js").read_text()
    assert "Broad Market Index" in ui
    assert "FSFFL Intrinsic Index" in ui
    assert "value_presentation" in ui
    assert "fsffl_cardinal_values" not in ui
    assert "provisional_fsffl_values" not in ui
    assert "Value Lab" not in ui


def test_product_shell_routes_analytics_to_terminal_not_legacy_team_explorer() -> None:
    shell = (ROOT / "src/fsffl/product/static/product_shell.js").read_text()
    assert "Analytics Terminal" in shell
    assert "analytics_terminal.js" in shell
    assert "renderFsfflAnalyticsTerminal" in shell
    assert "route==='players_assets'&&typeof window.renderFsfflExplorer" in shell
    assert "route==='analytics')ensureAnalyticsTerminalScript" in shell
