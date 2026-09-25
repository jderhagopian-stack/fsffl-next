from __future__ import annotations

from pydantic import TypeAdapter

from fsffl.forecast.late_start_snapshot import (
    LATE_START_SNAPSHOT_MODEL_VERSION,
    LateStartCurrentProjectionSnapshot,
)

from .contracts import ArtifactKey, ReusableArtifactRecord, canonical_fingerprint


LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND = (
    "late_start_current_projection_snapshot"
)
NFL_SEASON_SCOPE_KIND = "nfl_season"

_adapter = TypeAdapter(LateStartCurrentProjectionSnapshot)


def encode_late_start_current_projection_snapshot(
    snapshot: LateStartCurrentProjectionSnapshot,
) -> dict[str, object]:
    return _adapter.dump_python(snapshot, mode="json")


def decode_late_start_current_projection_snapshot(
    payload: dict[str, object],
) -> LateStartCurrentProjectionSnapshot:
    snapshot = _adapter.validate_python(payload)
    if snapshot.model_version != LATE_START_SNAPSHOT_MODEL_VERSION:
        raise ValueError("stored late-start projection snapshot model version is stale")
    return snapshot


def late_start_current_projection_snapshot_artifact(
    *,
    snapshot: LateStartCurrentProjectionSnapshot,
) -> ReusableArtifactRecord:
    """Persist the 2026 ROS exception separately from annual preseason authority."""

    payload = encode_late_start_current_projection_snapshot(snapshot)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
            scope_kind=NFL_SEASON_SCOPE_KIND,
            scope_id=str(snapshot.season),
            input_fingerprint=canonical_fingerprint(
                snapshot.season,
                snapshot.exception_version,
                snapshot.baseline_class,
                snapshot.captured_at.isoformat(),
                snapshot.evaluation_as_of.isoformat(),
                tuple(
                    (
                        item.source_id,
                        item.content_sha256,
                        item.captured_at.isoformat(),
                        item.provider_effective_at.isoformat()
                        if item.provider_effective_at is not None
                        else None,
                        item.rights_status.value,
                        item.accepted_subject_keys,
                        item.quarantined_subject_keys,
                    )
                    for item in snapshot.provider_evidence
                ),
                tuple(
                    (
                        item.subject_key,
                        item.metric.value,
                        item.independence_groups,
                        item.production_rights_independence_groups,
                        item.meets_minimum,
                        item.production_authority_meets_minimum,
                    )
                    for item in snapshot.independent_source_coverage
                ),
            ),
            model_version=LATE_START_SNAPSHOT_MODEL_VERSION,
        ),
        payload=payload,
        computed_at=snapshot.captured_at,
    )
