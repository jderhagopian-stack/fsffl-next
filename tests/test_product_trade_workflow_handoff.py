from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_trade_workflow_handoff_is_loaded_with_coherent_static_version():
    html = (STATIC / "index.html").read_text()
    assert '/static/trade_workflow_handoff.js?v=20260909-beta-feedback1' in html


def test_opportunity_handoff_carries_exact_asset_refs_and_revalidates_current_state():
    source = (STATIC / "trade_workflow_handoff.js").read_text()
    assert "focalAssetRefs:(row?.send||[]).map(item=>item.asset_ref)" in source
    assert "counterpartyAssetRefs:(row?.receive||[]).map(item=>item.asset_ref)" in source
    assert "handoff.stateId!==tradeUiState.browser.state_id" in source
    assert "handoff.focalAssetRefs.every(ref=>focalRefs.has(ref))" in source
    assert "handoff.counterpartyAssetRefs.every(ref=>otherRefs.has(ref))" in source
    assert "This opportunity is no longer current" in source


def test_opportunity_handoff_connects_discovery_to_trade_center_without_new_model_truth():
    source = (STATIC / "trade_workflow_handoff.js").read_text()
    assert "Work in Trade Center" in source
    assert "Open deal" in source
    assert "Opportunity package loaded" in source
    assert "Analyze this trade" in source
    assert "setRoute('trade_center')" in source
    assert "tradeUiState.focalSelected=new Set(handoff.focalAssetRefs)" in source
    assert "tradeUiState.counterpartySelected=new Set(handoff.counterpartyAssetRefs)" in source
    # This layer is workflow/presentation only. It must reuse existing browser and
    # analysis actions rather than creating another model endpoint or client score.
    assert "fetch(" not in source
    assert "api('/api/" not in source
    assert "acceptance probability" not in source.lower()
    assert "score=" not in source.lower()


def test_handoff_banner_is_cleared_when_user_edits_the_loaded_package():
    source = (STATIC / "trade_workflow_handoff.js").read_text()
    assert ".asset-option,.draft-chip,#clear-trade" in source
    assert "#counterparty-select" in source
    assert "clearHandoff()" in source
