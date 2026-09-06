from pathlib import Path


PROVISIONAL_EXPLANATION = (
    "Provisional FSFFL Value is currently exposed for private-beta product testing. "
    "Calibration and validation are still in progress. "
    "Do not use this number to evaluate player or trade sanity yet."
)


def test_product_api_exposes_typed_provisional_value_without_replacing_market_percentile() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '"estimates": [' in source
    assert '"provisional_fsffl_values": [' in source
    assert "score.model_dump(mode=\"json\")" in source
    assert "evidence.provisional_fsffl_values" in source


def test_roster_presents_provisional_value_and_market_percentile_separately() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")

    assert "provisional_fsffl_values" in source
    assert "item.score" in source
    assert "item.status" in source
    assert "item.model_version" in source
    assert "item.reference_source_id" in source
    assert "item.reference_scale_id" in source
    assert PROVISIONAL_EXPLANATION in source
    assert "<th>FSFFL Value</th>" in html
    assert "<th>Market percentile</th>" in html
    assert "PROVISIONAL — calibration in progress" in html


def test_presentation_never_derives_fsffl_value_from_market_percentile() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    compact = source.replace(" ", "")
    assert "*10000" not in compact
    assert "*10,000" not in compact
    assert "provisionalScoreFor(assetId)" in source
    assert "playerMarketPercentile(player)" in source


def test_missing_provisional_value_remains_missing() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    assert "if(!item||typeof item.score!=='number')return'—'" in source
