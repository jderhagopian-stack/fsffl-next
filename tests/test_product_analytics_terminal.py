from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_analytics_terminal_consumes_existing_authoritative_outputs() -> None:
    ui = (ROOT / "src/fsffl/product/static/analytics_terminal.js").read_text()
    for path in (
        "/api/league/team-views",
        "/api/values",
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


def test_value_lab_makes_the_ui_model_switch_auditable() -> None:
    ui = (ROOT / "src/fsffl/product/static/analytics_terminal.js").read_text()
    assert "fsffl_cardinal_values" in ui
    assert "provisional_fsffl_values" in ui
    assert "Current authoritative FSFFL Value" in ui
    assert "Earlier beta challenger" in ui
    assert "Decision and Opportunity Search must not consume it" in ui
    assert "different valuation outputs" in ui


def test_product_shell_routes_analytics_to_terminal_not_legacy_team_explorer() -> None:
    shell = (ROOT / "src/fsffl/product/static/product_shell.js").read_text()
    assert "Analytics Terminal" in shell
    assert "analytics_terminal.js" in shell
    assert "renderFsfflAnalyticsTerminal" in shell
    assert "route==='players_assets'&&typeof window.renderFsfflExplorer" in shell
    assert "route==='analytics')ensureAnalyticsTerminalScript" in shell
