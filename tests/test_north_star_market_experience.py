from pathlib import Path


MARKET = Path("src/fsffl/product/static/north_star_market.js")
MARKET_CSS = Path("src/fsffl/product/static/north_star_market.css")
APP = Path("src/fsffl/product/static/north_star_app.js")
INDEX = Path("src/fsffl/product/static/index.html")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_leads_with_visual_opportunity_board_not_table() -> None:
    source = _source(MARKET)

    assert "Your opportunity board" in source
    assert "What is worth your attention?" in source
    assert "ns-market-radar" in source
    assert "ns-market-authority-orb" in source
    assert "ns-market-package-line" in source
    assert "data-ns-market-open" in source
    assert "View every market match" in source


def test_market_preserves_search_and_decision_authority_boundaries() -> None:
    source = _source(MARKET)

    assert "does not create candidate ordering" in source
    assert "recommendation authority" in source
    assert "acceptance probability" in source
    assert "does not calculate an acceptance probability" in source
    assert "runTradeEvaluation" in source
    assert "Presentation filters and sort controls operate" in source


def test_market_has_explicit_consumer_authority_states_and_status_ctas() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "function authorityState(row)" in source
    for label in ("Recommended", "Worth investigating", "Needs full evaluation", "Market match only"):
        assert label in source
    for cta in ("Open recommendation", "Inspect this move", "Run full evaluation", "Inspect market match"):
        assert cta in source
    for token in ("authority-recommended", "authority-investigate", "authority-needs-eval", "authority-match-only"):
        assert token in css or token in source
    assert "--authority-accent" in css
    assert "data-ns-status" in source


def test_market_why_this_surfaced_uses_consumer_language_then_methods() -> None:
    source = _source(MARKET)

    assert "Why this surfaced" in source
    assert "Targets ${target}, currently #" in source
    assert "close enough in current FSFFL Value to be worth checking" in source
    assert "still needs a full bilateral evaluation" in source
    assert "Methods & evidence" in source
    assert "diagnostic Search evidence, not an acceptance score" not in source


def test_market_surfaces_identity_package_and_behavioral_context() -> None:
    source = _source(MARKET)

    assert "Acquire" in source
    assert "You give" in source
    assert "You get" in source
    assert "observed trade" in source
    assert "ownerSignal" in source


def test_market_separates_opportunities_players_and_waivers_modes() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "Opportunities" in source
    assert "Players" in source
    assert "Waivers / Add-Drop" in source
    assert "data-ns-mode" in source
    assert "s.tab='trades'" in source
    assert "s.tab='free_agents'" in source
    assert ".ns-market-mode-nav" in css
    assert ".ns-market-legacy-tabs{display:none" in css


def test_market_is_curated_first_and_has_progressive_browse_actions() -> None:
    source = _source(MARKET)

    assert "s.nsVisibleCount||4" in source
    assert "See more (" in source
    assert "View all unevaluated" in source
    assert "Browse market matches" in source


def test_market_filters_and_sorts_only_on_existing_evidence() -> None:
    source = _source(MARKET)

    for label in ("Position", "Team / owner", "Status", "Deal size", "Assets", "Sort"):
        assert label in source
    for label in ("Best fit / current Search order", "Most actionable", "Closest market match", "Biggest need addressed"):
        assert label in source
    assert "market_gap_ratio" in source
    assert "focal_position_strength_index" in source
    assert "authorityState" in source
    assert "composite" not in source.lower()


def test_market_card_opens_richer_detail_and_workspace_actions() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "Opportunity detail" in source
    assert "Roster fit" in source
    assert "Decision status" in source
    assert "Counterparty context" in source
    assert "Market context" in source
    assert "Save" in source
    assert "Watch target" in source
    assert "Send to Trade Center" in source
    assert "fsfflOpenOpportunityInTradeCenter" in source
    assert "ns-market-detail-result" in source
    assert "Alternative packages / counters" in source
    assert ".ns-market-opportunity-detail" in css


def test_available_players_are_presented_as_market_modes() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "Best available players" in source
    assert "Waiver / add-drop workspace" in source
    assert "Evaluate add/drop" in source
    assert "Open player" in source
    assert ".ns-market-players-mode" in css
    assert ".ns-market-waivers-mode" in css


def test_market_is_mobile_scan_first_without_horizontal_card_carousel() -> None:
    css = _source(MARKET_CSS)

    assert ".ns-market-radar" in css
    assert ".ns-market-authority-orb" in css
    assert ".ns-market-package-line" in css
    assert "scroll-snap-type:none" in css
    assert ".ns-market-cards{display:grid" in css
    assert ".ns-market-exact" in css
    assert "@media(max-width:760px)" in css


def test_app_shell_loads_market_visual_assets_once() -> None:
    source = _source(APP)

    assert "installNorthStarMarketAssets" in source
    assert "north_star_market.css?v=" in source
    assert "north_star_market.js?v=" in source
    assert "link[data-ns-market]" in source
    assert "script[data-ns-market]" in source


def test_hosted_release_eagerly_refreshes_market_assets() -> None:
    source = _source(INDEX)

    assert 'data-ns-market="true"' in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert len(versions) == 1


def test_market_shell_is_route_scoped_and_cleaned_up() -> None:
    source = _source(MARKET)

    assert "function onMarketRoute()" in source
    assert "if(!onMarketRoute()||opportunityState()?.payload?.status!=='ready')" in source
    assert "panel.classList.remove('ns-market-shell')" in source
    assert "if(!onMarketRoute())return" in source


def test_featured_market_spotlight_matches_complete_trade_package() -> None:
    source = _source(MARKET)

    assert "leadSend=assetRefs(lead.send).join('|')" in source
    assert "leadReceive=assetRefs(lead.receive).join('|')" in source
    assert "assetRefs(row.send).join('|')===leadSend" in source
    assert "assetRefs(row.receive).join('|')===leadReceive" in source


def test_waiver_drop_selection_survives_rerenders_and_methods_are_secondary() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "nsWaiverDropSelection" in source
    assert "select.addEventListener('change'" in source
    assert "select.value=String(s.nsWaiverDropSelection||'')" in source
    assert "s.nsWaiverAddKey!==addKey" in source
    assert "simplifyWaiverResult" in source
    assert "ns-waiver-methods" in source
    assert ".ns-waiver-methods" in css
