from pathlib import Path


def test_forecast_refresh_is_league_scoped_not_team_scoped() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    guard = "if(fsfflForecastRefreshInFlight||!state?.context?.league_id)return;"
    assert guard in source
    assert "!state?.context?.team_id" not in source
    assert "'/api/intelligence/refresh-forecasts'" in source


def test_mobile_timeout_polls_existing_simulation_before_full_retry() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "pollExistingSimulation" in source
    assert "'/api/product-context'" in source
    assert "fsfflSimulationPollUntil=Date.now()+180000" in source
    assert "Checking the existing simulation instead of restarting it" in source
