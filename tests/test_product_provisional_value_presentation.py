from pathlib import Path


def test_product_api_exposes_authoritative_cardinal_value_without_replacing_market_percentile() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '"estimates": [' in source
    assert '"fsffl_cardinal_values": [' in source
    assert "evidence.fsffl_cardinal_values" in source
    assert '"cardinal_player_coverage": evidence.cardinal_player_coverage' in source
    # Challenger evidence may remain exposed for research/debugging, but is no
    # longer the product's displayed FSFFL Value authority.
    assert '"provisional_fsffl_values": [' in source


def test_roster_presents_authoritative_value_and_market_percentile_separately() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")

    assert "fsffl_cardinal_values" in polish
    assert "item.score" in polish
    assert "item.authority_status" in polish
    assert "item.model_version" in polish
    assert "item.evidence_source_id" in polish
    assert "Authoritative NEXT-3 FSFFL Cardinal Market Score" in polish
    assert "<th>FSFFL Value</th>" in html
    assert "<th>Market percentile</th>" in html
    assert "authoritative NEXT-3 market-cardinal score" in html
    assert "PROVISIONAL — calibration in progress" not in html


def test_presentation_never_derives_fsffl_value_from_market_percentile() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    compact = (source + polish).replace(" ", "")
    assert "*10000" not in compact
    assert "*10,000" not in compact
    assert "fsfflCardinalScoreFor(assetId)" in polish
    assert "playerMarketPercentile(player)" in source


def test_missing_authoritative_value_remains_missing() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    assert "if(!item||typeof item.score!=='number')return'—'" in polish


def test_trade_report_is_human_first_and_mobile_stacks() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    assert "What this deal changes" in polish
    assert "What changes now" in polish
    assert "Market context" in polish
    assert "Technical evidence & limitations" in polish
    assert ".human-trade-summary-grid,.human-trade-next,.technical-evidence-grid{grid-template-columns:1fr}" in polish


def test_core_readiness_does_not_present_downstream_capabilities_as_failed_prerequisites() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    assert "Core ready" in polish
    assert "not a missing core-intelligence prerequisite" in polish
    assert "Opportunity discovery activates downstream" in polish
