from pathlib import Path


def test_players_assets_explorer_consumes_existing_authoritative_endpoints() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "'/api/trade-center/browser'" in source
    assert "'/api/values'" in source
    assert "fsffl_cardinal_values" in source
    assert "values.estimates" in source
    assert "cardinalRow?.score" in source
    assert "market?.distribution?.mean" in source
    assert "Search player, pick or team" in source
    assert "All positions" in source
    assert "All teams" in source


def test_players_assets_filter_state_survives_sort_redraw() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "assetFilters:{query:'',type:'',position:'',owner:'',role:''}" in source
    assert "function captureAssetFilters()" in source
    assert "const filters=fsfflExplorerState.assetFilters" in source
    assert "search.value=filters.query" in source
    assert "type.value=filters.type" in source
    assert "position.value=filters.position" in source
    assert "owner.value=filters.owner" in source
    assert "role.value=filters.role" in source
    assert "renderPlayersAssetsExplorer(values)" in source


def test_players_assets_prefers_full_nfl_season_projection() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    regular = "item.horizon==='fantasy_regular_season'"
    season = "item.horizon==='season'"
    assert regular in source
    assert season in source
    assert source.index(season) < source.index(regular)
    assert "NFL season projection" in source


def test_players_assets_adds_read_only_league_and_position_context() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "function explorerLeagueRank" in source
    assert "function explorerPositionRank" in source
    assert "Your highest FSFFL Value asset" in source
    assert "Your highest NFL season projection" in source
    assert "league's top 20 by FSFFL Value" in source
    assert "Your team" in source
    assert "presentation ordering" in source
    assert "not a new FSFFL score" in source
    assert "do not calculate new value, team utility, or action authority" in source


def test_legacy_explorer_metrics_remain_read_only_until_terminal_replaces_them() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    for metric in (
        "expected_wins",
        "playoff_probability",
        "optimized_expected_points",
        "asset_portfolio_mean",
        "draft_pick_count",
    ):
        assert metric in source
    assert "/api/league/chart?metric=" in source
    assert "Compare the league without hunting for answers" in source
    assert "this screen only organizes them" in source


def test_analytics_search_state_survives_sort_redraw() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "teamQuery:''" in source
    assert "fsfflExplorerState.teamQuery=event.target.value" in source
    assert "search.value=fsfflExplorerState.teamQuery" in source


def test_explorer_does_not_derive_fsffl_value_or_action_authority() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    compact = source.replace(" ", "")
    assert "*10000" not in compact
    assert "*10,000" not in compact
    assert "acceptance_probability" not in source
    assert "recommendation" not in source.lower()
    assert "opportunity_score" not in source
    assert "master_score" not in source.lower()
    assert "composite_score" not in source.lower()


def test_explorer_is_loaded_for_players_assets_and_has_mobile_specific_styles() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    css = Path("src/fsffl/product/static/explorer.css").read_text(encoding="utf-8")
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert '/static/explorer.js?v=' in html
    assert '/static/explorer.css?v=' in html
    assert html.index("explorer.js") < html.index("product_shell.js")
    assert "max-width:700px" in css
    assert "renderFsfflExplorer" in shell
    assert "route==='players_assets'&&typeof window.renderFsfflExplorer" in shell
    assert "route==='analytics')ensureAnalyticsTerminalScript" in shell
