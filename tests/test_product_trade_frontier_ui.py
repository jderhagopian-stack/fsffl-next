from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRADE_UI = ROOT / "src/fsffl/product/static/trade_center.js"
WEBAPP = ROOT / "src/fsffl/product/webapp.py"
INDEX = ROOT / "src/fsffl/product/static/index.html"


def test_trade_center_frontier_routes_through_backend_authority() -> None:
    ui = TRADE_UI.read_text(encoding="utf-8")
    webapp = WEBAPP.read_text(encoding="utf-8")
    assert "/api/trade-center/frontier" in ui
    assert 'qs("#explore-price")' in ui or "qs('#explore-price')" in ui
    assert "build_negotiation_frontier" in webapp
    assert '@application.post("/api/trade-center/frontier")' in webapp
    assert "Search does not rewrite Value" in ui


def test_trade_center_uses_authoritative_cardinal_value_not_retired_challenger() -> None:
    ui = TRADE_UI.read_text(encoding="utf-8")
    assert "fsffl_cardinal_values" in ui
    assert "Authoritative FSFFL market-cardinal Value" in ui
    assert "provisionalScoreFor" not in ui
    assert "PROVISIONAL" not in ui


def test_frontier_release_is_cache_busted_coherently() -> None:
    html = INDEX.read_text(encoding="utf-8")
    assert "20260907-session1" in html
    versions = {
        token.split("?v=")[1].split('"')[0]
        for token in html.split()
        if "?v=" in token
    }
    assert versions == {"20260907-session1"}
