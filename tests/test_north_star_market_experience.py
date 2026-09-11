from pathlib import Path


MARKET = Path("src/fsffl/product/static/north_star_market.js")
MARKET_CSS = Path("src/fsffl/product/static/north_star_market.css")
APP = Path("src/fsffl/product/static/north_star_app.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_leads_with_personalized_opportunity_cards_not_table() -> None:
    source = _source(MARKET)

    assert "Personalized market" in source
    assert "Moves worth your attention." in source
    assert "ns-market-card" in source
    assert "data-ns-market-eval" in source
    assert "See every candidate and exact Search evidence" in source


def test_market_preserves_search_and_decision_authority_boundaries() -> None:
    source = _source(MARKET)

    assert "does not create candidate ordering" in source
    assert "recommendation authority" in source
    assert "acceptance probability" in source
    assert "diagnostic Search evidence, not an acceptance score" in source
    assert "runTradeEvaluation" in source


def test_market_surfaces_identity_package_and_behavioral_context() -> None:
    source = _source(MARKET)

    assert "Acquire" in source
    assert "You send" in source
    assert "You receive" in source
    assert "observed trade" in source
    assert "ownerSignal" in source


def test_market_is_mobile_scan_first() -> None:
    css = _source(MARKET_CSS)

    assert "overflow-x:auto" in css
    assert "scroll-snap-type:x mandatory" in css
    assert ".ns-market-card.featured" in css
    assert ".ns-market-exact" in css


def test_app_shell_loads_market_visual_assets_once() -> None:
    source = _source(APP)

    assert "installNorthStarMarketAssets" in source
    assert "north_star_market.css?v=" in source
    assert "north_star_market.js?v=" in source
    assert "link[data-ns-market]" in source
    assert "script[data-ns-market]" in source


def test_market_shell_is_route_scoped_and_cleaned_up() -> None:
    source = _source(MARKET)

    assert "function onMarketRoute()" in source
    assert "if(!onMarketRoute()||opportunityState()?.payload?.status!=='ready')" in source
    assert "panel.classList.remove('ns-market-shell')" in source
    assert "if(!onMarketRoute())return" in source


def test_market_descendant_enhancements_reapply_after_workspace_rerenders() -> None:
    source = _source(MARKET)

    assert "if(panel.classList.contains('ns-market-shell'))return" not in source
    assert "summary&&!summary.classList.contains('ns-market-summary')" in source
    assert "note&&!note.classList.contains('ns-market-supporting')" in source


def test_featured_market_spotlight_matches_complete_trade_package() -> None:
    source = _source(MARKET)

    assert "leadSend=assetRefs(lead.send).join('|')" in source
    assert "leadReceive=assetRefs(lead.receive).join('|')" in source
    assert "assetRefs(row.send).join('|')===leadSend" in source
    assert "assetRefs(row.receive).join('|')===leadReceive" in source
