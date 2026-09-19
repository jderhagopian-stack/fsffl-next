from pathlib import Path


def test_player_stat_lines_use_only_authoritative_full_season_forecast_observations() -> None:
    source = Path("src/fsffl/product/static/player_stat_lines.js").read_text(encoding="utf-8")
    assert "item.metric===metric&&item.horizon==='season'" in source
    for metric in (
        "fantasy_points",
        "pass_yards",
        "pass_td",
        "interceptions",
        "rush_yards",
        "rush_td",
        "receptions",
        "rec_yards",
        "rec_td",
    ):
        assert metric in source
    assert "does not calculate fantasy points" in source
    assert "rest_of_season" not in source
    assert "fantasy_regular_season" not in source


def test_player_stat_lines_are_sortable_and_loaded_after_explorer() -> None:
    source = Path("src/fsffl/product/static/player_stat_lines.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert "player-stat-sort" in source
    assert "fsfflPlayerStatLineState.sort" in source
    assert "window.renderFsfflExplorer=async function(route)" in source
    assert "renderFsfflPlayerStatLines" in source
    assert html.index("explorer.js") < html.index("player_stat_lines.js") < html.index("product_shell.js")
