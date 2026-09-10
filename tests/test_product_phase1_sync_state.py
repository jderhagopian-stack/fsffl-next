from pathlib import Path


def test_hosted_restore_exposes_visible_sync_states_without_new_polling_loop() -> None:
    source = Path("src/fsffl/product/static/mobile_safari_recovery.js").read_text()

    assert "phase1_sync_state.js" in source
    assert "publishSyncState('checking')" in source
    assert "publishSyncState('current')" in source
    assert "publishSyncState('stale'" in source
    assert "Continuing with the last valid stored league" in source
    assert source.count("/api/connect/sleeper/background/current") == 2


def test_sync_state_component_explains_stale_while_revalidate() -> None:
    source = Path("src/fsffl/product/static/phase1_sync_state.js").read_text()

    assert "Stored league is usable while Sleeper is revalidated." in source
    assert "Your last valid stored league remains usable." in source
    assert "aria-live" in source
    assert "fsffl:sync-state" in source
    assert "MutationObserver" not in source
