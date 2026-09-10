from __future__ import annotations

from pydantic import TypeAdapter

from fsffl.forecast.current_runtime import LiveForecastRuntimeResult
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.simulation_runtime import LiveSimulationAnalyticsResult
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult

from .contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint, utc_now

FORECAST_ARTIFACT_KIND = "current_forecast_evidence"
SIMULATION_ARTIFACT_KIND = "live_simulation_analytics"
VALUE_ARTIFACT_KIND = "current_market_value"
LEAGUE_SCOPE_KIND = "league_state"

FORECAST_MODEL_VERSION = "next8-live-forecast-evidence-v3"
SIMULATION_MODEL_VERSION = "next8-live-simulation-analytics-v7:scoring-dispersion-diagnostic"
VALUE_MODEL_VERSION = "next3-current-market-runtime-v7:market-total-fail-closed"

_forecast_adapter = TypeAdapter(LiveForecastEvidence)
_value_adapter = TypeAdapter(CurrentMarketValueRuntimeResult)


def encode_forecast_evidence(evidence: LiveForecastEvidence) -> dict[str, object]:
    return _forecast_adapter.dump_python(evidence, mode="json")


def decode_forecast_evidence(payload: dict[str, object]) -> LiveForecastEvidence:
    evidence = _forecast_adapter.validate_python(payload)
    if evidence.model_version != FORECAST_MODEL_VERSION:
        raise ValueError("stored forecast evidence model version is stale")
    if not isinstance(evidence.runtime_result, LiveForecastRuntimeResult):
        raise ValueError("stored forecast runtime payload is invalid")
    return evidence


def encode_simulation(result: LiveSimulationAnalyticsResult) -> dict[str, object]:
    return result.model_dump(mode="json")


def decode_simulation(payload: dict[str, object]) -> LiveSimulationAnalyticsResult:
    result = LiveSimulationAnalyticsResult.model_validate(payload)
    if result.model_version != SIMULATION_MODEL_VERSION:
        raise ValueError("stored simulation model version is stale")
    return result


def encode_value_result(result: CurrentMarketValueRuntimeResult) -> dict[str, object]:
    return _value_adapter.dump_python(result, mode="json")


def decode_value_result(payload: dict[str, object]) -> CurrentMarketValueRuntimeResult:
    result = _value_adapter.validate_python(payload)
    if result.model_version != VALUE_MODEL_VERSION:
        raise ValueError("stored Value model version is stale")
    return result


def forecast_artifact(*, league_state_id: str, evidence: LiveForecastEvidence) -> ReusableArtifactRecord:
    payload = encode_forecast_evidence(evidence)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=FORECAST_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state_id,
            input_fingerprint=canonical_fingerprint(league_state_id, payload),
            model_version=FORECAST_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=utc_now(),
    )


def simulation_artifact(
    *,
    league_state_id: str,
    forecast_fingerprint: str,
    result: LiveSimulationAnalyticsResult,
) -> ReusableArtifactRecord:
    payload = encode_simulation(result)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=SIMULATION_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state_id,
            input_fingerprint=canonical_fingerprint(league_state_id, forecast_fingerprint),
            model_version=SIMULATION_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=utc_now(),
    )


def value_artifact(*, league_state_id: str, result: CurrentMarketValueRuntimeResult) -> ReusableArtifactRecord:
    payload = encode_value_result(result)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=VALUE_ARTIFACT_KIND,
            scope_kind=LEAGUE_SCOPE_KIND,
            scope_id=league_state_id,
            input_fingerprint=canonical_fingerprint(league_state_id, payload),
            model_version=VALUE_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=utc_now(),
    )
