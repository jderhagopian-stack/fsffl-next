from pathlib import Path


EXPECTED_ROUTES = (
    "league",
    "my_team",
    "players_assets",
    "league_comparison",
    "trade_center",
    "opportunities",
    "what_if",
    "simulator",
    "analytics",
    "reports",
)


def test_full_product_navigation_shell_is_exposed() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    for route in EXPECTED_ROUTES:
        assert f"route:'{route}'" in source

    for label in (
        "Home",
        "My Team",
        "Players & Assets",
        "League Comparison",
        "Trade Center",
        "Opportunities",
        "What-If",
        "Simulator",
        "Analytics Explorer",
        "Reports",
    ):
        assert f"label:'{label}'" in source


def test_future_surfaces_explain_authoritative_reuse_not_frontend_model_logic() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "reuse Forecast, Value, Decision and Simulation authority" in source
    assert "authoritative Analytics outputs" in source
    assert "no parallel calculation path" in source
    assert "second valuation path" in source


def test_shell_script_is_loaded_after_existing_product_scripts() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert '/static/product_shell.js?v=' in html
    assert html.index("product_polish.js") < html.index("product_shell.js")
