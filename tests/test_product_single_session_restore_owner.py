from pathlib import Path


def test_legacy_session_bridge_delegates_restore_to_hosted_owner() -> None:
    source = Path("src/fsffl/product/static/session_recovery.js").read_text()

    assert "const hostedRestore=window.fsfflRestoreSession" in source
    assert "return await hostedRestore()" in source
    assert "fsfflOriginalApi('/api/connect/sleeper'" not in source
    assert "window.addEventListener('load'" in source
    assert "hosted restore-first flow" in source


def test_mobile_hosted_module_remains_the_provider_restore_owner() -> None:
    source = Path("src/fsffl/product/static/mobile_safari_recovery.js").read_text()

    assert "window.fsfflRestoreSession=restoreSavedSession" in source
    assert "'/api/connect/sleeper/background'" in source
    assert "'/api/connect/sleeper/background/refresh'" in source
