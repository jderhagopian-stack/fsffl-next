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


def test_full_product_navigation_shell_preserves_routes_under_new_labels() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    for route in EXPECTED_ROUTES:
        assert f"route:'{route}'" in source

    assert "{route:'league',label:'Franchise',navigation:false}" in source
    assert "{route:'my_team',label:'Franchise',teamScoped:true,primary:true}" in source
    assert "{route:'league_comparison',label:'League',primary:true}" in source
    assert "{route:'opportunities',label:'Explore',primary:true}" in source
    assert "{route:'trade_center',label:'Trade',teamScoped:true,primary:true}" in source
    assert "label:'Home'" not in source
    assert "label:'Market'" not in source


def test_legacy_players_route_is_compatibility_only_and_delegates_to_market() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "{route:'players_assets',label:'Players & Assets',legacy:true,navigation:false}" in source
    assert "marketTab:'player_board'" in source
    assert "fsfflProductRoutes.filter(item=>item.primary)" in source


def test_shell_fallback_more_preserves_secondary_destinations() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "function fsfflFallbackSecondaryRoutes()" in source
    assert "!item.primary&&!item.legacy&&item.route!=='league'" in source
    assert "function fsfflAppendFallbackMore(nav,hasTeam,direct=false)" in source
    assert "more.textContent='More'" in source
    assert "fsfflAppendFallbackMore(nav,hasTeam,false)" in source
    assert "fsfflAppendFallbackMore(nav,hasTeam,true)" in source
    for route in ("behavioral_intelligence", "what_if", "simulator", "reports", "analytics"):
        assert f"route:'{route}'" in source


def test_product_surfaces_explain_authoritative_reuse_not_frontend_model_logic() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "rerun authoritative Simulation" in source
    assert "without inventing a second forecast or Value path" in source
    assert "authoritative Analytics/API outputs" in source
    assert "no parallel calculation path" in source
    assert "second valuation path" in source


def test_trade_center_route_loads_browser_after_dynamic_navigation() -> None:
    source = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "targetRoute==='trade_center'" in source
    assert "setTimeout(loadTradeCenter,0)" in source


def test_shell_script_is_loaded_after_existing_product_scripts() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert '/static/product_shell.js?v=' in html
    assert html.index("product_polish.js") < html.index("product_shell.js")
