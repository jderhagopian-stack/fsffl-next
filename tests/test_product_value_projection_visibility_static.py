from pathlib import Path


def test_value_readiness_is_owned_by_authoritative_status_payload() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert 'stage["stage"] == "value" and value_ready' in source
    assert 'stage["readiness"] = "ready"' in source
    assert 'payload["value_ready"] = value_ready' in source


def test_live_market_values_are_joined_into_my_team_view() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert "def _attach_live_value_profiles" in source
    assert "AssetValueProfile(" in source
    assert "_attach_live_value_profiles(view, runtime.value_evidence)" in source


def test_simulation_floor_forecasts_do_not_masquerade_as_direct_player_projection() -> None:
    source = Path("src/fsffl/product/simulation_runtime.py").read_text(encoding="utf-8")
    analytics_join = source.split("team_views: list[TeamAnalyticsView] = []", 1)[1]
    assert "forecasts=forecasts" in analytics_join
    assert "forecasts=effective_forecasts" not in analytics_join
