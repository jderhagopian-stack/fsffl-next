from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_hotfix_disables_line_level_background_tracing() -> None:
    source = Path("src/fsffl/product/background_jobs.py").read_text()
    hosted = Path("src/fsffl/product/persistent_webapp.py").read_text()
    assert "sys.settrace" not in source
    assert "cooperative_trace" not in source
    assert "install_foreground_pressure(app)" not in hosted
    assert "_deprioritize_background_thread()" in source


def test_page_entry_does_not_auto_start_intelligence() -> None:
    source = (STATIC / "forecast_refresh.js").read_text()
    maintain = source[source.index("async function maintainFsfflIntelligence()"):]
    assert "await maybeStartIntelligenceJob();" not in maintain.split("setInterval(", 1)[0]
    assert "manualIntelligenceRefresh" in source


def test_market_progressive_delivery_is_route_scoped() -> None:
    source = (STATIC / "progressive_delivery.js").read_text()
    assert "productState()?.route!=='opportunities'" in source
    assert "productState()?.route==='opportunities'&&requestId===store.requestSequence" in source


def test_boot_shell_precedes_product_and_hides_raw_shell() -> None:
    source = (STATIC / "index.html").read_text()
    assert "document.documentElement.classList.add('fsffl-booting')" in source
    assert "html.fsffl-booting .app-shell{visibility:hidden}" in source
    assert source.index('class="fsffl-critical-boot"') < source.index('class="app-shell"')
    app = (STATIC / "app.js").read_text()
    assert "fsfflFinishBoot" in app
    assert "applyContext();fsfflFinishBoot()" in app


def test_franchise_keeps_last_good_view_while_reads_refresh() -> None:
    source = (STATIC / "my_team_dashboard.js").read_text()
    assert "const hasLastGood=Boolean(fsfflMyTeamState.view)" in source
    assert "if(hasLastGood){" in source
    assert "renderFranchiseNorthStar();" in source
