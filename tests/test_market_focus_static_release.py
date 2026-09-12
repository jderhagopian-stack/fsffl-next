from pathlib import Path

INDEX = Path("src/fsffl/product/static/index.html")


def test_focus_and_drilldown_share_current_release_token() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert "market_focus_server.js?v=20260912-market-trade5" in source
    assert "market_trade_drilldown.js?v=20260912-market-trade5" in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert versions == {"20260912-market-trade5"}
