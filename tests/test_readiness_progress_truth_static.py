from pathlib import Path


def _shell() -> str:
    return Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")


def _refresh() -> str:
    return Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")


def _index() -> str:
    return Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")


def test_shared_readiness_polls_authoritative_job_lifecycle() -> None:
    source = _shell()
    assert "const payload=await api('/api/intelligence/jobs/current')" in source
    assert "state.intelligence.job={" in source
    assert "queued:[1,'Preparing current intelligence…']" in source
    assert "building_forecasts:[2,'Building projections…']" in source
    assert "refreshing_state:[3,'Refreshing league state…']" in source
    assert "running_simulation:[4,'Running season outlook…']" in source
    assert "building_values:[5,'Building market values…']" in source
    assert "attaching_results:[6,'Attaching current intelligence…']" in source
    assert "completed:[7,'Intelligence current']" in source


def test_interrupted_refresh_is_terminal_and_truthful() -> None:
    shell = _shell()
    refresh = _refresh()
    assert "'completed','failed','interrupted'" in shell
    assert "Refresh interrupted — last-good intelligence retained" in shell
    assert "if(payload.status==='interrupted')" in refresh
    assert "if(payload.job_id&&payload.status==='interrupted')" in refresh
    assert "fsfflCurrentJobId=null" in refresh


def test_readiness_repair_busts_mobile_static_cache() -> None:
    index = _index()
    assert "/static/forecast_refresh.js?v=20260924-readiness-truth1" in index
    assert "/static/product_shell.js?v=20260924-readiness-truth1" in index
