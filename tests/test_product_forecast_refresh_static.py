from pathlib import Path


def test_intelligence_refresh_is_league_scoped_not_team_scoped() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "!state?.context?.league_id" in source
    assert "!state?.context?.team_id" not in source
    assert "'/api/intelligence/jobs'" in source


def test_mobile_client_polls_server_owned_job_instead_of_holding_long_request() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "pollIntelligenceJob" in source
    assert "'/api/intelligence/jobs/current'" in source
    assert "'/api/intelligence/refresh-forecasts'" not in source
    assert "setInterval(maintainFsfflIntelligence,2500)" in source


def test_job_progress_is_rendered_from_server_authoritative_status() -> None:
    source = Path("src/fsffl/product/static/forecast_refresh.js").read_text(encoding="utf-8")
    assert "phaseMessage(payload)" in source
    assert "payload.status==='queued'||payload.status==='running'" in source
    assert "Forecasts and 50,000-run simulation are ready." in source
