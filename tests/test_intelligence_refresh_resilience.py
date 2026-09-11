from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFRESH_JS = ROOT / "src" / "fsffl" / "product" / "static" / "forecast_refresh.js"
CURRENT_RUNTIME = ROOT / "src" / "fsffl" / "forecast" / "current_runtime.py"


def test_refresh_failure_copy_is_consumer_safe_and_keeps_diagnostics_drilldown():
    source = REFRESH_JS.read_text(encoding="utf-8")

    assert "Intelligence refresh unavailable. Your current projections are still in place. Try again later." in source
    assert "Intelligence refresh unavailable. We could not validate enough projection sources. Try again later." in source
    assert "setForecastRefreshMessage(`Intelligence refresh failed: ${payload.error}`)" not in source
    assert "setRefreshTechnicalDetail(payload?.error)" in source
    assert "runtime-refresh-error-detail" in source
    assert "Refresh diagnostics" in source


def test_refresh_failure_does_not_weaken_authoritative_source_minimum():
    source = CURRENT_RUNTIME.read_text(encoding="utf-8")

    assert "minimum_independent_sources: int = 2" in source
    assert "if len(batches) < minimum_independent_sources:" in source
