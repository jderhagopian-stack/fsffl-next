from __future__ import annotations

from pydantic import TypeAdapter

from fsffl.forecast.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
    AnnualPreseasonProjectionSnapshot,
)

from .contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint


ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND = "annual_preseason_projection_snapshot"
NFL_SEASON_SCOPE_KIND = "nfl_season"

_adapter = TypeAdapter(AnnualPreseasonProjectionSnapshot)


def encode_annual_preseason_projection_snapshot(
    snapshot: AnnualPreseasonProjectionSnapshot,
) -> dict[str, object]:
    return _adapter.dump_python(snapshot, mode="json")


def decode_annual_preseason_projection_snapshot(
    payload: dict[str, object],
) -> AnnualPreseasonProjectionSnapshot:
    snapshot = _adapter.validate_python(payload)
    if snapshot.model_version != ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION:
        raise ValueError("stored annual preseason projection snapshot model version is stale")
    return snapshot


def annual_preseason_projection_snapshot_artifact(
    *,
    snapshot: AnnualPreseasonProjectionSnapshot,
) -> ReusableArtifactRecord:
    payload = encode_annual_preseason_projection_snapshot(snapshot)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
            scope_kind=NFL_SEASON_SCOPE_KIND,
            scope_id=str(snapshot.season),
            input_fingerprint=canonical_fingerprint(
                snapshot.season,
                snapshot.model_version,
                snapshot.governed_raw_ensemble_sha256,
                tuple(
                    (item.provider, item.provider_payload_sha256)
                    for item in snapshot.provider_evidence
                ),
            ),
            model_version=ANNUAL_PRESEASON_SNAPSHOT_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=snapshot.captured_at,
    )
