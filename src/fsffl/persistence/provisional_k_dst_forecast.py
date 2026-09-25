from __future__ import annotations

from pydantic import TypeAdapter

from fsffl.forecast.k_dst_provisional import (
    PROVISIONAL_K_DST_MODEL_VERSION,
    ProvisionalKDstForecast,
)

from .contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint


PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND = "late_start_provisional_k_dst_forecast"
PROVISIONAL_K_DST_SCOPE_KIND = "league_state_forecast_subject"


def provisional_k_dst_scope_id(
    *,
    league_state_id: str,
    subject_key: str,
) -> str:
    if not league_state_id.strip() or not subject_key.strip():
        raise ValueError("provisional K/DST scope requires league state and subject")
    return f"{league_state_id}:{subject_key}"

_adapter = TypeAdapter(ProvisionalKDstForecast)


def encode_provisional_k_dst_forecast(
    forecast: ProvisionalKDstForecast,
) -> dict[str, object]:
    return _adapter.dump_python(forecast, mode="json")


def decode_provisional_k_dst_forecast(
    payload: dict[str, object],
) -> ProvisionalKDstForecast:
    forecast = _adapter.validate_python(payload)
    if forecast.model_version != PROVISIONAL_K_DST_MODEL_VERSION:
        raise ValueError("stored provisional K/DST forecast model version is stale")
    if forecast.season != 2026:
        raise ValueError("stored provisional K/DST forecast escaped the 2026 boundary")
    return forecast


def provisional_k_dst_forecast_artifact(
    *,
    forecast: ProvisionalKDstForecast,
) -> ReusableArtifactRecord:
    """Persist degraded-authority Forecast separately from canonical Forecast truth."""

    payload = encode_provisional_k_dst_forecast(forecast)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=PROVISIONAL_K_DST_FORECAST_ARTIFACT_KIND,
            scope_kind=PROVISIONAL_K_DST_SCOPE_KIND,
            scope_id=provisional_k_dst_scope_id(
                league_state_id=forecast.league_state_id,
                subject_key=forecast.subject_key,
            ),
            input_fingerprint=canonical_fingerprint(
                forecast.season,
                forecast.exception_version,
                forecast.league_id,
                forecast.league_state_id,
                forecast.subject_key,
                forecast.as_of.isoformat(),
                tuple(
                    (
                        item.coordinate,
                        item.fantasy_points,
                        item.source_ids,
                        item.independence_groups,
                        item.provenance_refs,
                    )
                    for item in forecast.included_coordinates
                ),
                tuple(
                    (item.coordinate, item.rule_stats, item.reason)
                    for item in forecast.omitted_coordinates
                ),
                forecast.full_authority_blockers,
            ),
            model_version=PROVISIONAL_K_DST_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=forecast.as_of,
    )
