from pathlib import Path


def test_product_api_exposes_authoritative_cardinal_value_without_replacing_market_percentile() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '"estimates": [' in source
    assert '"fsffl_cardinal_values": [' in source
    assert "evidence.fsffl_cardinal_values" in source
    assert '"cardinal_player_coverage": evidence.cardinal_player_coverage' in source
    assert '"provisional_fsffl_values": [' in source


def test_roster_foregrounds_broad_market_and_intrinsic_without_cardinal() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")

    assert "fsfflBroadMarketFor" in polish
    assert "dynasty-market-percentile" in polish
    assert "Governed Broad Market percentile" in polish
    assert "FSFFL Intrinsic" in polish
    assert "fsffl_cardinal_values" not in polish
    assert "<th>FSFFL Cardinal Value</th>" not in html
    assert "<th>Broad Market percentile</th>" in html
    assert "<th>Value lens</th>" in html
    assert "PROVISIONAL — calibration in progress" not in html


def test_presentation_never_derives_fsffl_value_from_market_percentile() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    compact = (source + polish).replace(" ", "")
    assert "*10000" not in compact
    assert "*10,000" not in compact
    assert "fsfflBroadMarketFor(assetId)" in polish
    assert "playerMarketPercentile(player)" in source


def test_missing_broad_market_value_remains_missing() -> None:
    polish = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    assert "Broad Market —" in polish
    assert "typeof value!=='number'||!Number.isFinite(value)" in polish


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
    assert "Decision capability is connected to the product" in polish
    assert "Opportunity discovery is live as a downstream consumer" in polish
