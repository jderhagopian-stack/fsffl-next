from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_new_product_navigation_is_loaded_after_product_shell():
    html = (STATIC / "index.html").read_text()
    shell = html.index('/static/product_shell.js?v=')
    architecture = html.index('/static/product_navigation.js?v=')
    assert architecture > shell
    assert '<span>Home</span>' in html
    assert '<span>Franchise</span>' in html
    assert '<span>League</span>' in html
    assert '<span>Market</span>' in html


def test_mobile_primary_navigation_has_exactly_four_objects_plus_more():
    source = (STATIC / "product_navigation.js").read_text()
    assert "{route:'league',label:'Home'" in source
    assert "{route:'my_team',label:'Franchise'" in source
    assert "{route:'league_comparison',label:'League'" in source
    assert "{route:'opportunities',label:'Market'" in source
    assert "<span>More</span>" in source
    assert "grid-template-columns:repeat(5" in (STATIC / "mobile_touch_fix.css").read_text()


def test_more_sheet_preserves_every_existing_secondary_route():
    source = (STATIC / "product_navigation.js").read_text()
    for route in (
        "trade_center",
        "players_assets",
        "behavioral_intelligence",
        "what_if",
        "simulator",
        "reports",
        "analytics",
    ):
        assert f"route:'{route}'" in source
    assert "Decision tools" in source
    assert "Scenarios" in source
    assert "Explore" in source


def test_desktop_navigation_is_grouped_by_product_job():
    source = (STATIC / "product_navigation.js").read_text()
    assert '>Current<' in source
    assert '>Decide<' in source
    assert '>Explore<' in source
    assert "product-nav-group" in source


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


def test_product_navigation_is_presentation_only():
    source = (STATIC / "product_navigation.js").read_text()
    assert "No model truth" in source
    assert "api(" not in source
    assert "fetch(" not in source
    assert "/api/" not in source
    for forbidden in ("expected_wins", "cardinal", "decision_shape", "simulation_count", "acceptance_probability"):
        assert forbidden not in source.lower()
