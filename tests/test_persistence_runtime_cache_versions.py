from __future__ import annotations

from fsffl.persistence.runtime_cache import (
    FORECAST_MODEL_VERSION,
    SIMULATION_MODEL_VERSION,
    VALUE_MODEL_VERSION,
)
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.simulation_runtime import (
    LiveSimulationAnalyticsResult,
    simulation_model_version_for_rng_protocol,
)
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult


def test_durable_cache_versions_match_authoritative_runtime_models() -> None:
    assert FORECAST_MODEL_VERSION == "next8-live-forecast-evidence-v7:rolling-fumbles-lost-materiality"
    assert LiveForecastEvidence.__dataclass_fields__["model_version"].default == FORECAST_MODEL_VERSION
    simulation_model_version = simulation_model_version_for_rng_protocol(
        "python-random-gauss-v1"
    )
    assert LiveSimulationAnalyticsResult.model_fields["model_version"].default == simulation_model_version
    assert SIMULATION_MODEL_VERSION.startswith(
        f"{simulation_model_version}:python-random-gauss-v1;"
    )
    assert CurrentMarketValueRuntimeResult.__dataclass_fields__["model_version"].default == VALUE_MODEL_VERSION
