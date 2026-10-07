from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_new_product_navigation_is_loaded_after_product_shell():
    html = (STATIC / "index.html").read_text()
    shell = html.index('/static/product_shell.js?v=')
    architecture = html.index('/static/product_navigation.js?v=')
    assert architecture > shell
    assert '<span>Home</span>' not in html
    for label in ("Franchise", "League", "Explore", "Trade", "More"):
        assert f"<span>{label}</span>" in html


def test_mobile_primary_navigation_is_franchise_league_explore_trade_plus_more():
    source = (STATIC / "product_navigation.js").read_text()
    primary = source.split("const PRIMARY=[", 1)[1].split("];", 1)[0]
    assert "{route:'league',label:'Home'" not in primary
    assert "{route:'my_team',label:'Franchise'" in primary
    assert "{route:'league_comparison',label:'League'" in primary
    assert "{route:'opportunities',label:'Explore'" in primary
    assert "{route:'trade_center',label:'Trade'" in primary
    assert primary.index("route:'my_team'") < primary.index("route:'league_comparison'")
    assert primary.index("route:'league_comparison'") < primary.index("route:'opportunities'")
    assert primary.index("route:'opportunities'") < primary.index("route:'trade_center'")
    assert "<span>More</span>" in source
    assert "grid-template-columns:repeat(5" in (STATIC / "mobile_touch_fix.css").read_text()


def test_more_sheet_preserves_secondary_routes_without_duplication_of_primary_trade():
    source = (STATIC / "product_navigation.js").read_text()
    for route in (
        "behavioral_intelligence",
        "what_if",
        "simulator",
        "reports",
        "analytics",
    ):
        assert f"route:'{route}'" in source
    assert "const SECONDARY=[...LEAGUE_INTELLIGENCE,...SCENARIOS,...ANALYSIS]" in source
    assert "League intelligence" in source
    assert "Scenarios" in source
    assert "Reports & analysis" in source
    # Trade is promoted to primary navigation and must not be duplicated in More.
    secondary = source.split("const LEAGUE_INTELLIGENCE=[", 1)[1].split("const COMPATIBILITY=[", 1)[0]
    assert "route:'trade_center'" not in secondary


def test_desktop_navigation_uses_same_five_part_primary_hierarchy():
    source = (STATIC / "product_navigation.js").read_text()
    render = source.split("function renderDesktop()", 1)[1].split("function moreRow", 1)[0]
    assert "PRIMARY.map(desktopButton).join('')+desktopMoreButton()" in render
    assert "product-nav-group" not in render
    assert "data-product-more" in render


def test_navigation_is_accessible_and_preserves_team_scoping():
    source = (STATIC / "product_navigation.js").read_text()
    assert "aria-current=\"page\"" in source
    assert "aria-label','Primary product navigation'" in source
    assert "aria-modal','true'" in source
    assert "teamScoped:true" in source
    assert "Select a managed franchise first." in source


def test_mobile_navigation_preserves_ios_hardening_and_safe_fallback():
    css = (STATIC / "mobile_touch_fix.css").read_text()
    assert "touch-action:manipulation" in css
    assert "env(safe-area-inset-bottom" in css
    assert "body.fsffl-product-architecture #mobile-menu{display:none!important}" in css
    assert ".sidebar.open" in css
    assert "pointer-events:auto!important" in css


def test_desktop_more_menu_is_reachable_without_exposing_secondary_primary_items():
    css = (STATIC / "mobile_touch_fix.css").read_text()
    assert "@media(min-width:981px)" in css
    assert ".product-more-backdrop{display:block" in css
    assert ".product-more-sheet{display:block" in css
    assert ".product-more-backdrop[hidden],.product-more-sheet[hidden]{display:none!important}" in css


def test_product_navigation_is_presentation_only():
    source = (STATIC / "product_navigation.js").read_text()
    assert "No model truth" in source
    assert "api(" not in source
    assert "fetch(" not in source
    assert "/api/" not in source
    for forbidden in ("expected_wins", "cardinal", "decision_shape", "simulation_count", "acceptance_probability"):
        assert forbidden not in source.lower()
