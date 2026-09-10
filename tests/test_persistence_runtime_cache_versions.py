from __future__ import annotations

from fsffl.persistence.runtime_cache import (
    FORECAST_MODEL_VERSION,
    SIMULATION_MODEL_VERSION,
    VALUE_MODEL_VERSION,
)
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.simulation_runtime import LiveSimulationAnalyticsResult
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult


def test_durable_cache_versions_match_authoritative_runtime_models() -> None:
    assert LiveForecastEvidence.__dataclass_fields__["model_version"].default == FORECAST_MODEL_VERSION
    assert (
        LiveSimulationAnalyticsResult.model_fields["model_version"].default
        == SIMULATION_MODEL_VERSION
    )
    assert CurrentMarketValueRuntimeResult.__dataclass_fields__["model_version"].default == VALUE_MODEL_VERSION
