from pathlib import Path

INDEX = Path("src/fsffl/product/static/index.html")
RELEASE = "20260912-market-trade5"

def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def test_north_star_release_busts_eager_static_cache() -> None:
    source = _source(INDEX)
    for stale in ("20260910-phase3-visual2","20260911-northstar3","20260911-market-authority1","20260911-market-visual1","20260911-market-intent1","20260911-market-recovery1","20260911-opportunity-detail1","20260911-trade-center1","20260911-market-trade2","20260911-market-latency3","20260911-market-trade4"):
        assert stale not in source
    assert source.count(f"?v={RELEASE}") >= 10
    for asset in ("north_star_app.js","north_star_app.css","north_star_market.js","north_star_market.css","opportunity_posture_ui.js","trade_workflow_handoff.js","product_shell.js","market_session_recovery.js","north_star_opportunity_detail.js","north_star_opportunity_detail.css","north_star_trade_center.js","north_star_trade_center.css","market_trade_recomposition.js","market_trade_recomposition.css","market_focus_server.js","market_trade_drilldown.js"):
        assert f"{asset}?v={RELEASE}" in source
