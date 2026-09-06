from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "src/fsffl/product/static/index.html").read_text()
TRADE_CLIENT = (ROOT / "src/fsffl/product/static/trade_center.js").read_text()


def test_trade_center_client_is_loaded_after_core_app() -> None:
    assert '<script src="/static/app.js" defer></script>' in INDEX
    assert '<script src="/static/trade_center.js" defer></script>' in INDEX
    assert INDEX.index('/static/app.js') < INDEX.index('/static/trade_center.js')


def test_trade_center_uses_canonical_browser_and_authoritative_analysis_endpoints() -> None:
    assert "api('/api/trade-center/browser')" in TRADE_CLIENT
    assert "api('/api/trade-center/analyze'" in TRADE_CLIENT
    assert "counterparty_team_id" in TRADE_CLIENT
    assert "focal_asset_refs" in TRADE_CLIENT
    assert "counterparty_asset_refs" in TRADE_CLIENT


def test_trade_center_provisional_value_is_display_only() -> None:
    assert "provisionalScoreFor" in TRADE_CLIENT
    assert "PROVISIONAL" in TRADE_CLIENT
    assert "do not determine the result" in TRADE_CLIENT
    assert "not a trade grade, recommendation, acceptance probability, or package economics" in TRADE_CLIENT
    assert "percentile*10000" not in TRADE_CLIENT.replace(" ", "").lower()
    assert "score*" not in TRADE_CLIENT.replace(" ", "").lower()


def test_trade_center_does_not_invent_price_frontier_or_action_authority() -> None:
    assert "explore-price" not in TRADE_CLIENT
    assert "acceptance_probability" not in TRADE_CLIENT
    assert "opportunity_score" not in TRADE_CLIENT
    assert "trade_grade" not in TRADE_CLIENT


def test_trade_center_handles_honest_missing_value() -> None:
    assert "Value —" in TRADE_CLIENT
    assert "typeof item.score!=='number'" in TRADE_CLIENT
