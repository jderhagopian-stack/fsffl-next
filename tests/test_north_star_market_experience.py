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
    assert "data-ns-market-eval" in source
    assert "View every market match" in source


def test_market_preserves_search_and_decision_authority_boundaries() -> None:
    source = _source(MARKET)

    assert "does not create candidate ordering" in source
    assert "recommendation authority" in source
    assert "acceptance probability" in source
    assert "does not calculate an acceptance probability" in source
    assert "runTradeEvaluation" in source


def test_market_has_explicit_consumer_authority_states() -> None:
    source = _source(MARKET)
    css = _source(MARKET_CSS)

    assert "function authorityState(row)" in source
    for label in ("Recommended", "Worth investigating", "Needs full evaluation", "Market match only"):
        assert label in source
    for token in ("authority-recommended", "authority-investigate", "authority-needs-eval", "authority-match-only"):
        assert token in css or token in source
    assert "--authority-accent" in css


def test_market_why_this_surfaced_uses_consumer_language_then_methods() -> None:
    source = _source(MARKET)

    assert "Why this surfaced" in source
    assert "roster pressure point" in source
    assert "close enough in current value to be worth checking" in source
    assert "Methods & evidence" in source
    assert "cleanReason" in source
    assert "diagnostic Search evidence, not an acceptance score" not in source


def test_market_surfaces_identity_package_and_behavioral_context() -> None:
    source = _source(MARKET)

    assert "Acquire" in source
    assert "Give" in source
    assert "Get" in source
    assert "observed trade" in source
    assert "ownerSignal" in source


def test_market_is_mobile_scan_first_without_horizontal_card_carousel() -> None:
    css = _source(MARKET_CSS)

    assert ".ns-market-radar" in css
    assert ".ns-market-authority-orb" in css
    assert ".ns-market-package-line" in css
    assert "scroll-snap-type:none" in css
    assert ".ns-market-cards{display:grid" in css
    assert ".ns-market-exact" in css


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
