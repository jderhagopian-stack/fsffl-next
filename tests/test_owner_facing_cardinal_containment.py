from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


OWNER_FACING = (
    "analytics_terminal.js",
    "explorer.js",
    "home_dashboard.js",
    "intrinsic_market_discovery.js",
    "intrinsic_value_experience.js",
    "market_trade_drilldown.js",
    "market_trade_recomposition.js",
    "my_team_dashboard.js",
    "north_star_market.js",
    "opportunities.js",
    "player_intelligence.js",
    "player_stat_lines.js",
    "trade_center.js",
)


def test_owner_facing_primary_surfaces_do_not_foreground_cardinal() -> None:
    for filename in OWNER_FACING:
        source = (STATIC / filename).read_text(encoding="utf-8")
        assert "FSFFL Cardinal Value" not in source, filename
        assert "Current authoritative FSFFL Cardinal Market Value" not in source, filename


def test_more_player_and_analytics_tables_do_not_consume_cardinal_as_primary_value() -> None:
    analytics = (STATIC / "analytics_terminal.js").read_text(encoding="utf-8")
    explorer = (STATIC / "explorer.js").read_text(encoding="utf-8")
    for source in (analytics, explorer):
        assert "fsffl_cardinal_values" not in source
        assert "provisional_fsffl_values" not in source
        assert "Broad Market" in source
        assert "FSFFL Intrinsic" in source


def test_compatibility_cardinal_cleanup_shim_is_not_a_visible_value_surface() -> None:
    source = (STATIC / "beta_product_corrections.js").read_text(encoding="utf-8")
    # The legacy metric identifier is allowed only in the cleanup shim that
    # removes it from the UI. It is not an owner-facing label.
    assert "total_cardinal_value" in source
    assert "FSFFL Cardinal Value" not in source
