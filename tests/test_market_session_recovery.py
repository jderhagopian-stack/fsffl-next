from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "src/fsffl/product/static/market_session_recovery.js"
INDEX = ROOT / "src/fsffl/product/static/index.html"
RELEASE = "20260912-market-trade5"

def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def test_market_recovery_reconciles_persisted_context_after_silent_state_race() -> None:
    source = _source(RECOVERY)
    for phrase in ("api('/api/product-context')","state.context=current","applyContext()","!hasPayload&&!stillLoading&&loadingPanel()","loadOpportunityWorkspace({showLoading:false})"):
        assert phrase in source

def test_market_loading_state_has_visible_retry_and_reconnect_escape_hatches() -> None:
    source = _source(RECOVERY)
    for phrase in ("Retry Market","Connect / change league","data-market-retry","data-market-reconnect","12000"):
        assert phrase in source

def test_loaded_league_selector_always_offers_connect_or_change_league() -> None:
    source = _source(RECOVERY)
    for phrase in ("#league-select","Connect / change league…","fsfflHostedConnectSleeper","populateSelectors=wrapped"):
        assert phrase in source

def test_market_recovery_is_presentation_and_session_only() -> None:
    source = _source(RECOVERY)
    assert "does not create Search, Value, Decision or Simulation truth" in source
    assert "acceptance probability" not in source
    assert "market_gap_ratio" not in source
    assert "action_authority" not in source

def test_hosted_release_eagerly_loads_market_recovery_with_one_asset_generation() -> None:
    source = _source(INDEX)
    assert f"market_session_recovery.js?v={RELEASE}" in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert versions == {RELEASE}
