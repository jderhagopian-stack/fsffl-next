from pathlib import Path
import shutil
import subprocess

import pytest


STATIC = Path("src/fsffl/product/static")
MARKET = STATIC / "north_star_market.js"
MARKET_CSS = STATIC / "north_star_market.css"
INDEX = STATIC / "index.html"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return node


def test_market_has_exactly_four_primary_jobs_to_be_done_tabs() -> None:
    source = _source(MARKET)
    tabs = source.split("const TABS=[", 1)[1].split("];", 1)[0]
    assert tabs.count('["') == 4
    for label in ("For You", "Trade Finder", "Player Board", "Free Agents"):
        assert label in tabs
    for old in ("Waivers / Add-Drop", "data-ns-mode"):
        assert old not in tabs


def test_for_you_is_small_governed_discovery_not_a_frontend_score() -> None:
    source = _source(MARKET)
    assert "spotlightRows" in source
    assert ".slice(0,5)" in source
    assert "current governed Search and Decision evidence" in source
    assert "Open opportunity" in source
    assert "presentation score" not in source.lower()
    assert "acceptance_probability" not in source
    assert "realistic %" not in source
    assert "Buy low" not in source
    assert "Sell high" not in source


def test_market_consumer_statuses_are_authority_bounded() -> None:
    source = _source(MARKET)
    for label in (
        "Recommended",
        "Worth investigating",
        "Needs full evaluation",
        "Market match only",
    ):
        assert label in source
    assert 'if(action==="actionable"||action==="recommended")' in source
    assert "Existing Decision authority supports action." in source
    assert "Search found a plausible structure; Decision has not evaluated this package." in source


def test_opportunity_detail_is_predecision_and_hands_exact_package_to_trade_center() -> None:
    source = _source(MARKET)
    for label in ("Opportunity Detail", "Overview", "Acquisition Paths", "Fit & Impact"):
        assert label in source
    assert "Search-discovered acquisition path · not an acceptance prediction" in source
    assert "Exact season impact" in source
    assert "Not run merely to preview this opportunity." in source
    assert "Evaluate this package in Trade Center" in source
    assert "fsfflOpenOpportunityInTradeCenter" in source
    assert "runTradeEvaluation" not in source
    assert "/api/trade-center/simulate" not in source


def test_trade_finder_preserves_owner_controlled_search_modes_and_postures() -> None:
    source = _source(MARKET)
    for label in (
        "Improve my team",
        "Target a player",
        "Shop a player",
        "Target a position",
        "Explore an owner / team",
        "Calculated",
        "Contend / Win now",
        "Balanced",
        "Retool",
        "Rebuild",
    ):
        assert label in source
    assert "window.fsfflMarketIntent?.set" in source
    assert "window.fsfflOpportunityPosture?.setPosture" in source
    assert "window.fsfflMarketFocus?.refresh" in source


def test_trade_finder_filters_and_sorts_only_governed_returned_rows() -> None:
    source = _source(MARKET)
    for label in (
        "Package shape",
        "Players only",
        "Includes picks",
        "Current Search order",
        "Closest market match",
        "Biggest roster need addressed",
        "Most action-authoritative",
    ):
        assert label in source
    assert "market_gap_ratio" in source
    assert "focal_position_strength_index" in source
    assert "hidden composite" not in source.lower()


def test_player_board_is_read_only_and_keeps_value_lenses_separate() -> None:
    source = _source(MARKET)
    assert 'api("/api/league/value-lenses?universe=all")' in source
    assert 'api("/api/league/team-views")' in source
    assert "Reading current State, Forecast team views and governed Value lenses. No Search or Decision work is launched." in source
    assert "Broad Market and FSFFL Intrinsic are shown side by side and never blended." in source
    assert "League Market Value: unavailable" in source
    assert "Team Utility: not part of this board." in source
    assert "data-player-intelligence-id" in source
    assert "/api/opportunities/workspace" not in source


def test_player_board_exposes_requested_filter_and_sort_dimensions() -> None:
    source = _source(MARKET)
    for token in (
        "data-board-filter='query'",
        "data-board-filter='position'",
        "data-board-filter='age'",
        "data-board-filter='owner'",
        "data-board-filter='nfl'",
        "data-board-filter='roster'",
        "data-board-filter='role'",
        "market_index",
        "intrinsic_index",
        "ppg",
        "projection",
        "overall_rank",
        "position_rank",
    ):
        assert token in source
    assert "presentation ordering only" in source


def test_player_board_preserves_governed_value_disagreement_discovery() -> None:
    source = _source(MARKET)
    discovery = _source(STATIC / "intrinsic_market_discovery.js")
    assert "Explore Value disagreement" in source
    assert "data-market-disagreement" in source
    assert "data-market-disagreement" in discovery
    assert "raw Market and raw Shapley quantities are never subtracted" in discovery


def test_free_agents_browse_immediately_and_evaluate_only_on_explicit_click() -> None:
    source = _source(MARKET)
    assert "Available-player discovery is immediate; add/drop evaluation is explicit." in source
    assert "Evaluate add/drop" in source
    assert 'body.querySelector("[data-waiver-run]")?.addEventListener("click",runWaiver)' in source
    before, after = source.split("async function runWaiver(){", 1)
    assert "/api/opportunities/waiver" not in before
    assert 'api("/api/opportunities/waiver"' in after


def test_market_context_links_to_existing_player_owner_and_trade_workflows() -> None:
    source = _source(MARKET)
    assert "openTradeFinder" in source
    assert "openFreeAgent" in source
    assert "openOwner" in source
    assert "behavioral_intelligence" in source
    assert "data-player-intelligence-id" in source
    handoff = _source(STATIC / "north_star_opportunity_handoff.js")
    assert "Market context carried forward" in handoff
    assert "whySurfaced" in handoff


def test_market_mobile_layout_keeps_tabs_tappable_and_identity_sticky() -> None:
    css = _source(MARKET_CSS)
    assert ".market-ns-tabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))" in css
    assert "@media(max-width:760px)" in css
    assert ".market-ns-tabs button{min-height:46px" in css
    assert ".market-ns-v2{width:100%;max-width:100%;overflow:hidden}" in css
    assert ".market-ns-player-table{width:100%;max-width:100%}" in css
    assert ".market-ns-player-sticky{position:sticky;left:0" in css


def test_market_release_is_eager_and_single_generation() -> None:
    source = _source(INDEX)
    assert 'north_star_market.css?v=20260924-live-usability-hotfix1' in source
    assert 'north_star_market.js?v=20260924-live-usability-hotfix1' in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert versions == {"20260924-live-usability-hotfix1"}


def test_market_browser_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(MARKET)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
