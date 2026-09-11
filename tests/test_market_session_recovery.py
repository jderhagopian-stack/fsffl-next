from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "src/fsffl/product/static/market_session_recovery.js"
INDEX = ROOT / "src/fsffl/product/static/index.html"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_recovery_reconciles_persisted_context_after_silent_state_race() -> None:
    source = _source(RECOVERY)

    assert "api('/api/product-context')" in source
    assert "state.context=current" in source
    assert "applyContext()" in source
    assert "!hasPayload&&!stillLoading&&loadingPanel()" in source
    assert "loadOpportunityWorkspace({showLoading:false})" in source


def test_market_loading_state_has_visible_retry_and_reconnect_escape_hatches() -> None:
    source = _source(RECOVERY)

    assert "Retry Market" in source
    assert "Connect / change league" in source
    assert "data-market-retry" in source
    assert "data-market-reconnect" in source
    assert "12000" in source


def test_loaded_league_selector_always_offers_connect_or_change_league() -> None:
    source = _source(RECOVERY)

    assert "#league-select" in source
    assert "Connect / change league…" in source
    assert "fsfflHostedConnectSleeper" in source
    assert "populateSelectors=wrapped" in source


def test_market_recovery_is_presentation_and_session_only() -> None:
    source = _source(RECOVERY)

    assert "does not create Search, Value, Decision or Simulation truth" in source
    assert "acceptance probability" not in source
    assert "market_gap_ratio" not in source
    assert "action_authority" not in source


def test_hosted_release_eagerly_loads_market_recovery_with_one_asset_generation() -> None:
    source = _source(INDEX)

    assert "market_session_recovery.js?v=20260911-market-recovery1" in source
    versions = {token.split("?v=")[1].split('"')[0] for token in source.split() if "?v=" in token}
    assert versions == {"20260911-market-recovery1"}
