from pathlib import Path


def test_forecast_refresh_is_league_scoped_not_team_scoped() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    guard = "if(fsfflForecastRefreshInFlight||!state?.context?.league_id)return;"
    assert guard in source
    assert "!state?.context?.team_id" not in source
    assert "'/api/intelligence/refresh-forecasts'" in source
