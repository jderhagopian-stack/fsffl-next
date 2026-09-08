from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "src/fsffl/product/static/index.html").read_text()
TRADE_CLIENT = (ROOT / "src/fsffl/product/static/trade_center.js").read_text()
WEBAPP = (ROOT / "src/fsffl/product/webapp.py").read_text()


def test_trade_center_client_is_loaded_after_core_app() -> None:
    assert '/static/app.js?v=' in INDEX
    assert '/static/trade_center.js?v=' in INDEX
    assert INDEX.index('/static/app.js') < INDEX.index('/static/trade_center.js')


def test_trade_center_uses_canonical_browser_and_authoritative_analysis_endpoints() -> None:
    assert "api('/api/trade-center/browser')" in TRADE_CLIENT
    assert "api('/api/trade-center/analyze'" in TRADE_CLIENT
    assert "counterparty_team_id" in TRADE_CLIENT
    assert "focal_asset_refs" in TRADE_CLIENT
    assert "counterparty_asset_refs" in TRADE_CLIENT


def test_trade_center_authoritative_value_is_market_context_only() -> None:
    assert "fsffl_cardinal_values" in TRADE_CLIENT
    assert "Authoritative FSFFL market-cardinal Value" in TRADE_CLIENT
    assert "do not determine the bilateral result" in TRADE_CLIENT
    assert "not a trade grade, recommendation, acceptance probability, or package economics" in TRADE_CLIENT
    assert "provisionalScoreFor" not in TRADE_CLIENT
    assert "PROVISIONAL" not in TRADE_CLIENT
    assert "percentile*10000" not in TRADE_CLIENT.replace(" ", "").lower()
    assert "score*" not in TRADE_CLIENT.replace(" ", "").lower()


def test_trade_center_price_frontier_is_backend_governed_not_client_invented() -> None:
    assert "explore-price" in TRADE_CLIENT
    assert "/api/trade-center/frontier" in TRADE_CLIENT
    assert '@application.post("/api/trade-center/frontier")' in WEBAPP
    assert "build_negotiation_frontier" in WEBAPP
    assert "Search does not rewrite Value" in TRADE_CLIENT
    assert "opportunity_score" not in TRADE_CLIENT
    assert "trade_grade" not in TRADE_CLIENT


def test_trade_center_handles_honest_missing_value() -> None:
    assert "FSFFL Value —" in TRADE_CLIENT
    assert "typeof item.score!=='number'" in TRADE_CLIENT
