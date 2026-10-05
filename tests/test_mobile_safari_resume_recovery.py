from pathlib import Path


STATIC = Path(__file__).parents[1] / "src" / "fsffl" / "product" / "static"


def test_mobile_safari_resume_module_keeps_lifecycle_recovery_disabled():
    index = (STATIC / "index.html").read_text()
    recovery = (STATIC / "mobile_safari_recovery.js").read_text()

    assert "/static/mobile_safari_recovery.js" in index
    assert "fsfflMobileSafariRecoveryDisabled=true" in recovery
    assert "visibilitychange" not in recovery
    assert "pageshow" not in recovery
    assert "fsfflForceMobileRepaint" not in recovery
    assert "window.addEventListener('focus'" not in recovery


def test_beta_correction_observer_cannot_reenter_on_its_own_dom_mutations():
    source = (STATIC / "beta_product_corrections.js").read_text()

    assert "observer?.disconnect()" in source
    assert "requestAnimationFrame" in source
    assert "new MutationObserver(queueRefresh)" in source
    assert "new MutationObserver(()=>refresh())" not in source
    assert "if(refreshing)return" in source


def test_route_specific_modules_are_lazy_at_initial_page_load():
    index = (STATIC / "index.html").read_text()
    shell = (STATIC / "product_shell.js").read_text()

    for script, loader in (
        ("/static/league_comparison.js", "ensureLeagueComparisonScript"),
        ("/static/my_team_dashboard.js", "ensureMyTeamScript"),
        ("/static/opportunities.js", "ensureOpportunitiesScript"),
        ("/static/simulator.js", "ensureSimulatorScript"),
    ):
        assert f'<script src="{script}' not in index
        assert loader in shell
        assert script in shell


def test_base_boot_shell_has_bounded_idempotent_safari_resume_rehydrate():
    app = (STATIC / "app.js").read_text()

    assert "fsfflContextRehydratePromise" in app
    assert "FSFFL_BOOT_REHYDRATE_TIMEOUT_MS=12000" in app
    assert "window.addEventListener('pageshow',fsfflRecoverBootOnResume)" in app
    assert "document.addEventListener('visibilitychange'" in app
    assert "if(fsfflContextRehydratePromise)return fsfflContextRehydratePromise" in app
    assert "document.querySelector('.fsffl-critical-boot')" in app
    assert "data.fsfflBootRetry='true'" in app
    assert "Your last-good intelligence has not been replaced." in app
