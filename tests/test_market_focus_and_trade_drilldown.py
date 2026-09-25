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
RELEASE = "20260925-market-discovery1"


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


def test_market_north_star_has_exactly_four_primary_tabs_and_neutral_language() -> None:
    source = _read(STATIC / "north_star_market.js")
    assert '["for_you","For You","What might I care about?"]' in source
    assert '["trade_finder","Trade Finder","Find realistic paths"]' in source
    assert '["player_board","Player Board","Discover for yourself"]' in source
    assert '["free_agents","Free Agents","Add without a trade"]' in source
    tabs = source.split("const TABS=[", 1)[1].split("];", 1)[0]
    assert tabs.count('["') == 4
    for phrase in (
        "Value disagreement",
        "Worth attention",
        "Prelim plausible",
        "Bilateral friction",
        "Market match only",
    ):
        assert phrase in source
    for forbidden in ("Buy low", "Sell high", "realistic %", "A grade", "B grade", "C grade"):
        assert forbidden not in source


def test_market_north_star_for_you_never_auto_runs_full_trade_evaluation() -> None:
    source = _read(STATIC / "north_star_market.js")
    assert "forYouOpportunities" in source
    assert "Your best paths right now." in source
    assert "Open opportunity" in source
    assert "Evaluate in Trade Center" in source
    assert "runTradeEvaluation" not in source
    assert "/api/opportunities/trade" not in source
    assert "/api/trade-center/simulate" not in source
    assert "acceptance_probability" not in source


def test_trade_finder_owner_focus_is_server_owned_before_candidate_limit() -> None:
    search = _read(FOCUSED_SEARCH)
    source = _read(STATIC / "north_star_market.js")
    assert '"owner"' in search.split("_VALID_INTENTS", 1)[1].split("\n", 1)[0]
    assert 'normalized_intent == "owner"' in search
    assert 'counterparty_team_id' in search
    assert "Explore an owner / team" in source
    assert "window.fsfflMarketIntent?.set" in source
    assert "window.fsfflMarketFocus?.refresh" in source


def test_player_board_is_read_only_discovery_with_separate_value_lenses() -> None:
    source = _read(STATIC / "north_star_market.js")
    css = _read(STATIC / "north_star_market.css")
    assert 'api("/api/league/value-lenses?universe=all")' in source
    assert 'api("/api/league/team-views")' in source
    assert "Broad Market and FSFFL Intrinsic are shown side by side and never blended." in source
    assert "Intrinsic is preparing; Broad Market remains live." in source
    assert "League Market Value: unavailable" in source
    assert "Team Utility: not part of this board." in source
    for token in (
        "market_index",
        "intrinsic_index",
        "age",
        "ppg",
        "projection",
        "overall_rank",
        "position_rank",
        "data-player-intelligence-id",
        "data-board-filter='position'",
        "data-board-filter='owner'",
        "data-board-filter='nfl'",
        "data-board-filter='roster'",
        "data-board-filter='role'",
    ):
        assert token in source
    assert ".market-ns-player-table{overflow-x:auto" in css
    assert ".market-ns-player-sticky{position:sticky;left:0" in css


def test_free_agents_only_run_governed_add_drop_on_explicit_action() -> None:
    source = _read(STATIC / "north_star_market.js")
    assert "Evaluate add/drop" in source
    assert 'body.querySelector("[data-waiver-run]")?.addEventListener("click",runWaiver)' in source
    run_waiver = source.split("async function runWaiver(){", 1)[1].split("function openOwner", 1)[0]
    assert 'api("/api/opportunities/waiver"' in run_waiver
    assert "/api/opportunities/waiver" not in source.split("async function runWaiver(){", 1)[0]


def test_market_mobile_contract_preserves_four_tabs_and_player_identity() -> None:
    css = _read(STATIC / "north_star_market.css")
    assert ".market-ns-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))" in css
    assert "@media(max-width:760px)" in css
    assert ".market-ns-v2{width:100%;max-width:100%;overflow:hidden}" in css
    assert ".market-ns-player-table{width:100%;max-width:100%}" in css
    assert ".market-ns-player-sticky" in css


def test_player_intelligence_market_actions_route_by_current_ownership_context() -> None:
    source = _read(STATIC / "player_intelligence.js")
    for phrase in (
        "Market actions",
        "Evaluate add/drop",
        "Shop in Trade Finder",
        "Target in Trade Finder",
        "Open current owner",
        "openFreeAgent",
        'openTradeFinder?.("shop"',
        'openTradeFinder?.("target"',
        "openOwner",
    ):
        assert phrase in source


def test_legacy_players_route_delegates_to_market_player_board() -> None:
    shell = _read(STATIC / "product_shell.js")
    navigation = _read(STATIC / "product_navigation.js")
    assert "marketTab:'player_board'" in shell
    assert "{route:'players_assets',label:'Players & Assets',legacy:true}" in shell
    assert "fsfflProductRoutes.filter(item=>!item.legacy)" in shell
    decision_block = navigation.split("const DECISIONS=[", 1)[1].split("];", 1)[0]
    assert "players_assets" not in decision_block
