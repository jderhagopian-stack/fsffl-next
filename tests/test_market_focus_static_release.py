from pathlib import Path

INDEX = Path("src/fsffl/product/static/index.html")
RELEASE = "20260924-home-readiness-top1"


def test_focus_and_drilldown_share_current_release_token() -> None:
    source = INDEX.read_text(encoding="utf-8")
    assert f"market_focus_server.js?v={RELEASE}" in source
    assert f"market_trade_drilldown.js?v={RELEASE}" in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert versions == {RELEASE}
