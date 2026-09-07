from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "src/fsffl/product/webapp.py"
TRADE_UI = ROOT / "src/fsffl/product/static/trade_center.js"
POLISH = ROOT / "src/fsffl/product/static/product_polish.js"
INDEX = ROOT / "src/fsffl/product/static/index.html"


def test_trade_center_exposes_on_demand_simulation_after_fast_analysis() -> None:
    webapp = WEBAPP.read_text(encoding="utf-8")
    ui = TRADE_UI.read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")
    assert '@application.post("/api/trade-center/simulate")' in webapp
    assert "build_post_trade_simulation_comparison" in webapp
    assert 'id="simulate-trade"' in html
    assert "/api/trade-center/simulate" in ui
    assert "simulateTradeDraft" in ui
    assert "trade-simulation-result" in ui


def test_browser_only_formats_authoritative_post_trade_deltas() -> None:
    ui = TRADE_UI.read_text(encoding="utf-8")
    polish = POLISH.read_text(encoding="utf-8")
    assert "NEXT-4 Team Utility" in ui
    assert "browser only formats them" in ui
    assert "signedTradePercentPoints" in ui
    assert "Ready to simulate on demand" in polish
    assert "authoritative NEXT-4 Simulation" in polish
    assert "acceptance percentage" in polish


def test_post_trade_surface_preserves_mobile_freeze_regression() -> None:
    polish = POLISH.read_text(encoding="utf-8")
    assert "MutationObserver" not in polish
    assert "setInterval(presentRuntimeCapabilities" not in polish


def test_post_trade_static_assets_share_one_cache_busting_version() -> None:
    html = INDEX.read_text(encoding="utf-8")
    for asset in (
        "app.css",
        "explorer.css",
        "app.js",
        "trade_center.js",
        "forecast_refresh.js",
        "product_polish.js",
        "explorer.js",
        "product_shell.js",
    ):
        assert f"/static/{asset}?v=20260907-tradesim1" in html
