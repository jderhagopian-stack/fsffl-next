from datetime import datetime, timezone
from math import isclose, sqrt

import pytest

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.value.intrinsic import ForecastValueMapping, estimate_intrinsic_player_value
from fsffl.value.models import ForecastValueInput, ValueScale


AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)
SCALE = ValueScale(scale_id="fsffl-economic", version="v1", unit_label="value units")


def forecast(*, issued_at: datetime = AS_OF, version: str = "forecast-v1") -> ForecastValueInput:
    return ForecastValueInput(
        player_id="player-1",
        horizon=ForecastHorizon.MULTI_YEAR,
        distribution=ForecastDistribution(mean=300.0, stddev=40.0, p10=240.0, p50=300.0, p90=360.0),
        forecast_model_version=version,
        forecast_as_of=issued_at,
    )


def mapping(*, residual_stddev: float = 0.0, forecast_version: str | None = "forecast-v1") -> ForecastValueMapping:
    return ForecastValueMapping(
        forecast_model_version=forecast_version,
        economic_units_per_forecast_unit=2.0,
        intercept=100.0,
        residual_stddev=residual_stddev,
        model_version="conversion-v1",
        evidence_through_season=2025,
        sample_size=500,
    )


def test_intrinsic_value_propagates_affine_forecast_moments() -> None:
    result = estimate_intrinsic_player_value(
        forecast(), mapping(), scale=SCALE, as_of=AS_OF, model_version="intrinsic-v1"
    )

    assert result.asset_id == "player-1"
    assert result.distribution.mean == 700.0
    assert result.distribution.stddev == 80.0
    assert result.distribution.p10 == 580.0
    assert result.distribution.p50 == 700.0
    assert result.distribution.p90 == 820.0


def test_conversion_error_widens_uncertainty_without_fake_quantiles() -> None:
    result = estimate_intrinsic_player_value(
        forecast(), mapping(residual_stddev=60.0), scale=SCALE, as_of=AS_OF, model_version="intrinsic-v1"
    )

    assert isclose(result.distribution.stddev, sqrt(80.0**2 + 60.0**2))
    assert result.distribution.p10 is None
    assert result.distribution.p50 is None
    assert result.distribution.p90 is None


def test_intrinsic_value_rejects_hindsight_and_mapping_version_mismatch() -> None:
    future = datetime(2026, 9, 2, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        estimate_intrinsic_player_value(
            forecast(issued_at=future), mapping(), scale=SCALE, as_of=AS_OF, model_version="intrinsic-v1"
        )

    with pytest.raises(ValueError):
        estimate_intrinsic_player_value(
            forecast(version="forecast-v2"), mapping(), scale=SCALE, as_of=AS_OF, model_version="intrinsic-v1"
        )
