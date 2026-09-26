from pathlib import Path


def test_hosted_private_beta_promotes_vnext_only_for_future_y2_y3() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")

    assert "make_resilient_forecast_loader(_persistence_store)" in source
    assert "make_preseason_baseline_authority_loader(_persistence_store)" in source

    assert "future_forecast_builder=provide_vnext_future_forecast_contract" in source
    assert "future_forecast_model_version=VNEXT_FORECAST_VERSION" in source
    assert 'future_missing_fact_family="vnext_future_forecast_coordinate"' in source

    assert "_player_future_forecast_cache = PlayerFutureForecastCache(" in source
    assert "forecast_model_version=VNEXT_FORECAST_VERSION" in source
    assert "future_cache=_player_future_forecast_cache" in source

    # Promotion must be a future-coordinate wiring change. Current-season Y1
    # remains owned by the resilient live/source-health + immutable preseason
    # fallback path above.
    assert "_forecast_loader = make_resilient_forecast_loader(_persistence_store)" in source


def test_hosted_promotion_has_no_direct_downstream_value_math_override() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")

    assert "provide_vnext_future_forecast_contract" in source
    assert "install_shapley_intrinsic_routes" in source
    assert "install_league_value_lens_routes" in source
    assert "install_player_intelligence_routes" in source
    assert "0.85" not in source
    assert "global C" not in source



def test_active_vnext_provider_has_no_direct_p0_runtime_or_provider_dependency() -> None:
    source = Path("src/fsffl/product/vnext_future_forecast_provider.py").read_text(
        encoding="utf-8"
    )
    assert "p0_forecast_runtime" not in source
    assert "p0_future_forecast_provider" not in source
    assert "build_p0_standard_future_materialization" not in source
    assert "P0_FUTURE_SCORING_COORDINATE" not in source
    assert "P0_SOURCE_SEASON" not in source


def test_model_neutral_probability_primitive_excludes_p0_production_orchestration() -> None:
    source = Path("src/fsffl/forecast/future_state_primitive.py").read_text(
        encoding="utf-8"
    )
    assert '["production_models"]' not in source
    assert "P0_FINAL_ROUTE_AUTHORITY" not in source
    assert "_score_production" not in source
    assert "build_p0_standard_future_materialization" not in source


def test_downstream_future_forecast_consumers_do_not_import_p0_or_vnext_implementations() -> None:
    for path in (
        "src/fsffl/product/private_beta_shapley_runtime.py",
        "src/fsffl/product/player_intelligence.py",
        "src/fsffl/value/live_intrinsic_calendar.py",
        "src/fsffl/value/shapley_intrinsic_contract.py",
    ):
        source = Path(path).read_text(encoding="utf-8")
        assert "p0_forecast_runtime" not in source, path
        assert "p0_future_forecast_provider" not in source, path
        assert "vnext_future_forecast_provider" not in source, path
        assert "P0_FORECAST_VERSION" not in source, path
        assert "VNEXT_FORECAST_VERSION" not in source, path
