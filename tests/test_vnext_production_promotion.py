from pathlib import Path


def test_hosted_private_beta_promotes_vnext_only_for_future_y2_y3() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")

    assert "make_resilient_forecast_loader(_persistence_store)" in source
    assert "make_preseason_baseline_authority_loader(_persistence_store)" in source

    assert "future_forecast_builder=build_vnext_future_forecast_contract" in source
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

    assert "build_vnext_future_forecast_contract" in source
    assert "install_shapley_intrinsic_routes" in source
    assert "install_league_value_lens_routes" in source
    assert "install_player_intelligence_routes" in source
    assert "0.85" not in source
    assert "global C" not in source
