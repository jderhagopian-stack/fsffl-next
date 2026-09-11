from pathlib import Path


ROOT = Path("src/fsffl/product/static")
DETAIL = ROOT / "north_star_opportunity_detail.js"
HANDOFF = ROOT / "north_star_opportunity_handoff.js"
CSS = ROOT / "north_star_opportunity_detail.css"
INDEX = ROOT / "index.html"
RELEASE = "20260911-trade-center1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_opportunity_detail_uses_consumer_first_hierarchy() -> None:
    source = _read(DETAIL)
    for phrase in (
        "Why this fits",
        "What changes for your team",
        "What is stopping this?",
        "Next step",
        "Methods & evidence",
    ):
        assert phrase in source
    assert "Expected wins" in source
    assert "Playoff odds" in source
    assert "Title odds" in source
    assert "Run full evaluation" in source
    assert "Send to Trade Center" in source


def test_opportunity_detail_preserves_authority_boundaries() -> None:
    source = _read(DETAIL)
    assert "action_authority" in source
    assert "disposition" in source
    assert "market_test_only" in source
    assert "acceptance odds" in source
    assert "does not calculate acceptance odds or upgrade recommendation authority" in source
    assert "acceptance_probability" not in source


def test_opportunity_detail_visualizes_existing_simulation_deltas() -> None:
    source = _read(DETAIL)
    assert "team_deltas" in source
    assert "competitive_outcome" in source
    assert "expected_wins" in source
    assert "playoff_probability" in source
    assert "championship_probability" in source
    assert "largest_single_player_lineup_drop" in source
    assert "nsod-bars" in source


def test_detail_replaces_legacy_report_blocks_in_default_hierarchy() -> None:
    css = _read(CSS)
    assert ".ns-market-opportunity-detail.nsod .opp-trade-result" in css
    assert ".ns-market-opportunity-detail.nsod #opp-evaluation-brief" in css
    assert "display:none!important" in css


def test_trade_center_handoff_carries_market_context_without_replacing_canonical_recheck() -> None:
    source = _read(HANDOFF)
    assert "Market context carried forward" in source
    assert "actionAuthority" in source
    assert "disposition" in source
    assert "fsfflOpenOpportunityInTradeCenter" in source
    assert "Trade Center still revalidates canonical assets" in source


def test_opportunity_detail_assets_load_after_market_layer() -> None:
    source = _read(INDEX)
    assert f"north_star_opportunity_detail.css?v={RELEASE}" in source
    assert f"north_star_opportunity_handoff.js?v={RELEASE}" in source
    assert f"north_star_opportunity_detail.js?v={RELEASE}" in source
    assert source.index("north_star_market.js") < source.index("north_star_opportunity_detail.js")
