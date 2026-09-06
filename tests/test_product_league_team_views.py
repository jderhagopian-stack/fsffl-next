from pathlib import Path


def test_league_team_views_reuse_existing_authoritative_views() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert '@application.get("/api/league/team-views")' in source
    assert "runtime.simulation_analytics.team_views" in source
    assert "lineup_result.team_views" in source
    assert "build_forecast_team_view(" in source
    assert "build_state_only_team_view(" in source
    assert "_attach_live_value_profiles(view, runtime.value_evidence)" in source
    assert '"source_level": source_level' in source


def test_league_team_views_do_not_mutate_selected_team_context() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    block = source.split('def league_team_views', 1)[1].split('@application.get("/api/trade-center/browser")', 1)[0]
    assert "store.select_team" not in block
    assert "selected_team_id" not in block


def test_players_assets_consumes_backend_projection_and_role_evidence() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "api('/api/league/team-views')" in source
    assert "projected_starter" in source
    assert "projected_lineup_slot" in source
    assert "explorerPlayerProjection" in source
    assert "explorerSortButton('Projection','projection'" in source
    assert "explorerSortButton('Projected role','projected_role'" in source
    assert "the browser does not optimize a lineup" in source
    assert "api('/api/select-team'" not in source
