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


def test_market_value_percentile_and_age_are_presented_as_separate_concepts() -> None:
    source = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert "estimate.scale?.scale_id==='dynasty-market-percentile'" in source
    assert "estimate.distribution.mean*100" in source
    assert "function fmtAge" in source
    assert "Number.isInteger(value)?value.toFixed(0):value.toFixed(1)" in source
    assert "<th>Market percentile</th>" in html
    assert 'value="total_market_value">Total market value' in html
    assert 'value="total_cardinal_value">Total FSFFL Cardinal Value' in html
    assert "team_market_value_portfolios" in source
    assert "team_cardinal_portfolios" in source
    assert "<th>Dynasty value</th>" not in html
    assert ">Draft capital<" not in html
    assert "Pick inventory" in html


def test_player_display_uses_explicit_full_nfl_season_contract_without_changing_simulation_horizon() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    analytics = Path("src/fsffl/analytics/team.py").read_text(encoding="utf-8")
    simulation = Path("src/fsffl/product/simulation_runtime.py").read_text(encoding="utf-8")

    assert "season_fantasy_points_projection" in analytics
    assert "ForecastHorizon.SEASON" in analytics
    assert "ForecastMetric.FANTASY_POINTS" in analytics
    assert "season_fantasy_points_projection" in shell
    assert "item.horizon==='season'" in shell
    assert "item.horizon==='fantasy_regular_season'" not in shell
    assert "NFL season projection" in shell

    # Simulation still owns and uses the shorter fantasy-regular-season horizon.
    assert "weeks=fantasy_weeks" in simulation
    assert "build_regular_season_simulation_input" in simulation


def test_explorer_missing_and_zero_values_sort_after_real_values() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "fsfflExplorerMissingForSort" in shell
    assert "if(am)return 1" in shell
    assert "if(bm)return-1" in shell
    assert "['value','market_percentile','projection']" in shell


def test_core_ready_presentation_exposes_live_trade_and_opportunity_capabilities() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "presentDownstreamReadiness" in shell
    assert "context?.forecast_ready&&context?.simulation_ready&&context?.value_ready" in shell
    assert "Trade Decision is available for submitted deals" in shell
    assert "Opportunity discovery is available" in shell
