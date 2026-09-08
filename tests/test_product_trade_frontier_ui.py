from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRADE_UI = ROOT / "src/fsffl/product/static/trade_center.js"
WEBAPP = ROOT / "src/fsffl/product/webapp.py"
INDEX = ROOT / "src/fsffl/product/static/index.html"
SESSION = ROOT / "src/fsffl/product/static/session_recovery.js"


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


def test_trade_decision_surface_translates_support_to_plain_language_accept() -> None:
    ui = SESSION.read_text(encoding="utf-8")
    assert "support:'Accept'" in ui
    assert "counter_or_review:'Counter'" in ui
    assert "Package / consolidation" in ui
    assert "run the post-trade simulation to finish the recommendation" in ui


def test_frontier_release_is_cache_busted_coherently() -> None:
    html = INDEX.read_text(encoding="utf-8")
    versions = {
        token.split("?v=")[1].split('"')[0]
        for token in html.split()
        if "?v=" in token
    }
    assert len(versions) == 1
    version = next(iter(versions))
    assert version.strip()
    assert version != "20260907-decision3"
