from pathlib import Path

INDEX = Path("src/fsffl/product/static/index.html")
BASE_RELEASE = "20260927-presentation-continuity1"
MARKET_RELEASE = "20260927-market-nonblocking1"


def test_nonblocking_market_assets_have_targeted_release_token() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert f"market_focus_server.js?v={MARKET_RELEASE}" in source
    assert f"progressive_delivery.js?v={MARKET_RELEASE}" in source
    assert f"market_trade_drilldown.js?v={BASE_RELEASE}" in source
    assert f"product_shell.js?v={BASE_RELEASE}" in source
