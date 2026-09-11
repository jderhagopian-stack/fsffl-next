from pathlib import Path


INDEX = Path("src/fsffl/product/static/index.html")
APP_JS = Path("src/fsffl/product/static/north_star_app.js")
APP_CSS = Path("src/fsffl/product/static/north_star_app.css")
DIRECTIVE = Path("docs/NORTH_STAR_PRODUCT_DIRECTIVE.md")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_north_star_app_layer_loads_after_recomposition() -> None:
    source = _source(INDEX)
    assert "/static/north_star_recomposition.css?v=" in source
    assert "/static/north_star_app.css?v=" in source
    assert source.index("north_star_recomposition.css") < source.index("north_star_app.css")
    assert "/static/north_star_app.js?v=" in source
    assert source.index("product_navigation.js") < source.index("north_star_app.js")


def test_app_layer_visualizes_authoritative_evidence_without_new_model_truth() -> None:
    source = _source(APP_JS)
    assert "competitive_outcome" in source
    assert "position_strengths" in source
    assert "roster_resilience" in source
    assert "fsfflLeagueStructureState.views" in source
    assert "fsfflMyTeamState.view" in source
    assert "acceptance_probability" not in source
    assert "master_score" not in source
    assert "recommendation_score" not in source


def test_league_atlas_is_scan_first_and_exact_values_are_drill_down() -> None:
    source = _source(APP_JS)
    assert "See positional control at a glance." in source
    assert "strengthBand" in source
    assert "data-ns-team" in source
    assert "ns-atlas-detail" in source
    assert "strength index" in source
    assert "league-relative numbers" in source


def test_home_and_franchise_surface_graphical_current_state() -> None:
    source = _source(APP_JS)
    assert "ns-home-scan" in source
    assert "Playoffs" in source
    assert "Best room" in source
    assert "Pressure point" in source
    assert "ns-franchise-visual" in source
    assert "ns-franchise-mini-bars" in source


def test_mobile_experience_is_composed_like_an_app() -> None:
    source = _source(APP_CSS)
    assert "Mobile is composed like an app" in source
    assert ".product-mobile-nav" in source
    assert "env(safe-area-inset-bottom)" in source
    assert ".ns-horizontal-band" in source
    assert ".ns-league-atlas" in source


def test_product_directive_preserves_depth_and_authority_boundaries() -> None:
    source = _source(DIRECTIVE)
    assert "scan" in source.lower()
    assert "drill-down" in source.lower()
    assert "Data → State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation" in source
    assert "fake acceptance probability" in source
    assert "Presentation may organize, compress, visualize and explain governed truth" in source
