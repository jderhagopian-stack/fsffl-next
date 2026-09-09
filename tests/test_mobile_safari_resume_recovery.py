from pathlib import Path


STATIC = Path(__file__).parents[1] / "src" / "fsffl" / "product" / "static"


def test_mobile_safari_resume_guard_is_loaded_and_handles_lifecycle_events():
    index = (STATIC / "index.html").read_text()
    recovery = (STATIC / "mobile_safari_recovery.js").read_text()

    assert "/static/mobile_safari_recovery.js" in index
    assert "visibilitychange" in recovery
    assert "pageshow" in recovery
    assert "pagehide" in recovery
    assert "fsfflRehydrateAfterMobileResume" in recovery
    assert "/api/product-context" in recovery
    assert "fsfflRestoreSession" in recovery
    assert "event.persisted" in recovery
    assert "fsfflMobileHiddenAt==null" in recovery
    assert "fsfflContextsEquivalent" in recovery
    assert "fsfflForceMobileRepaint" not in recovery
    assert "window.addEventListener('focus'" not in recovery


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
