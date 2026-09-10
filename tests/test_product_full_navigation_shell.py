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
        "Franchise",
        "Players & Assets",
        "League Comparison",
        "Trade Center",
        "Opportunities",
        "What-If",
        "Simulator",
        "Analytics Terminal",
        "Reports",
    ):
        assert f"label:'{label}'" in source


def test_product_surfaces_explain_authoritative_reuse_not_frontend_model_logic() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "rerun authoritative Simulation" in source
    assert "without inventing a second forecast or Value path" in source
    assert "authoritative Analytics/API outputs" in source
    assert "no parallel calculation path" in source
    assert "second valuation path" in source


def test_trade_center_route_loads_browser_after_dynamic_navigation() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "route==='trade_center'" in source
    assert "setTimeout(loadTradeCenter,0)" in source


def test_shell_script_is_loaded_after_existing_product_scripts() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert '/static/product_shell.js?v=' in html
    assert html.index("product_polish.js") < html.index("product_shell.js")
