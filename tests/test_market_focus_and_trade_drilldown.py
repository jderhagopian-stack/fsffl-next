from pathlib import Path

ROOT = Path("src/fsffl/product")
FOCUSED_SEARCH = ROOT / "focused_opportunity_search.py"
FOCUSED_ROUTES = ROOT / "focused_opportunity_routes.py"
SEARCH_CACHE = ROOT / "opportunity_search_cache.py"
PERSISTENT = ROOT / "persistent_webapp.py"
STATIC = ROOT / "static"
FOCUS_JS = STATIC / "market_focus_server.js"
DRILLDOWN_JS = STATIC / "market_trade_drilldown.js"
INDEX = STATIC / "index.html"
RELEASE = "20260912-market-trade5"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_focus_is_server_owned_before_candidate_limit() -> None:
    search = _read(FOCUSED_SEARCH)
    routes = _read(FOCUSED_ROUTES)
    focus_js = _read(FOCUS_JS)
    assert "build_focused_trade_candidates" in search
    assert "_shop_focused_candidates" in search
    assert "Market Focus rebuilt the package neighborhood around the player you chose to shop" in search
    assert '"/api/opportunities/focused-workspace"' in routes
    assert '"applied_before_candidate_limit": True' in routes
    assert "focused[:limit]" in routes
    assert "/api/opportunities/focused-workspace?" in focus_js
    assert "fsffl:market-focus-applied" in focus_js


def test_focus_reuses_exact_full_search_catalog() -> None:
    cache = _read(SEARCH_CACHE)
    persistent = _read(PERSISTENT)
    assert "make_cached_opportunity_search" in cache
    assert "FSFFL Market search catalog timing" in cache
    assert "_cached_opportunity_search" in persistent
    assert "_opportunity_workspace.build_roster_aware_trade_candidates = _cached_opportunity_search" in persistent
    assert "candidate_builder=_cached_opportunity_search" in persistent


def test_opportunity_detail_adds_useful_preanalysis_context() -> None:
    source = _read(DRILLDOWN_JS)
    for phrase in (
        "Why this is worth investigating",
        "Your need",
        "Package value shape",
        "Other roster fit",
        "Owner context",
        "What still needs Trade Center",
    ):
        assert phrase in source
    assert "acceptance_probability" not in source


def test_trade_result_uses_tappable_progressive_disclosure_panels() -> None:
    source = _read(DRILLDOWN_JS)
    for phrase in (
        "Tap any panel for the evidence underneath",
        "Value & roster space",
        "Starting lineup",
        "Season outlook",
        "Why the decision landed here",
        "Other team",
        "<details class=\"ns3-drill-card\"",
    ):
        assert phrase in source
    assert "scenario_simulation_count" in source
    assert "scenario_cache_hit" in source


def test_new_market_assets_load_after_existing_recomposition() -> None:
    source = _read(INDEX)
    assert f"market_focus_server.js?v={RELEASE}" in source
    assert f"market_trade_drilldown.js?v={RELEASE}" in source
    assert source.index("opportunity_posture_ui.js") < source.index("market_focus_server.js")
    assert source.index("market_trade_recomposition.js") < source.index("market_trade_drilldown.js")
