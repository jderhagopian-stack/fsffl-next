from pathlib import Path

ROOT = Path("src/fsffl/product/static")
DETAIL = ROOT / "north_star_opportunity_detail.js"
HANDOFF = ROOT / "north_star_opportunity_handoff.js"
CSS = ROOT / "north_star_opportunity_detail.css"
INDEX = ROOT / "index.html"
RELEASE = "20260912-market-trade5"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def test_opportunity_detail_uses_consumer_first_hierarchy() -> None:
    source = _read(DETAIL)
    for phrase in ("Why this fits","What changes for your team","What is stopping this?","Next step","Methods & evidence","Expected wins","Playoff odds","Title odds","Run full evaluation","Send to Trade Center"):
        assert phrase in source

def test_opportunity_detail_preserves_authority_boundaries() -> None:
    source = _read(DETAIL)
    for phrase in ("action_authority","disposition","market_test_only","acceptance odds","does not calculate acceptance odds or upgrade recommendation authority"):
        assert phrase in source
    assert "acceptance_probability" not in source

def test_opportunity_detail_visualizes_existing_simulation_deltas() -> None:
    source = _read(DETAIL)
    for phrase in ("team_deltas","competitive_outcome","expected_wins","playoff_probability","championship_probability","largest_single_player_lineup_drop","nsod-bars"):
        assert phrase in source

def test_detail_replaces_legacy_report_blocks_in_default_hierarchy() -> None:
    css = _read(CSS)
    assert ".ns-market-opportunity-detail.nsod .opp-trade-result" in css
    assert ".ns-market-opportunity-detail.nsod #opp-evaluation-brief" in css
    assert "display:none!important" in css

def test_trade_center_handoff_carries_market_context_without_replacing_canonical_recheck() -> None:
    source = _read(HANDOFF)
    for phrase in ("Market context carried forward","actionAuthority","disposition","fsfflOpenOpportunityInTradeCenter","Trade Center still revalidates canonical assets"):
        assert phrase in source

def test_opportunity_detail_assets_load_after_market_layer() -> None:
    source = _read(INDEX)
    for asset in ("north_star_opportunity_detail.css","north_star_opportunity_handoff.js","north_star_opportunity_detail.js"):
        assert f"{asset}?v={RELEASE}" in source
    assert source.index("north_star_market.js") < source.index("north_star_opportunity_detail.js")
