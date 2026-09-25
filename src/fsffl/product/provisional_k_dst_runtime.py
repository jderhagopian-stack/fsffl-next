from __future__ import annotations

from fsffl.forecast.k_dst_provisional import build_provisional_k_dst_forecast
from fsffl.forecast.late_start_snapshot import (
    LATE_START_SNAPSHOT_MODEL_VERSION,
    ros_subject_key,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.persistence.late_start_projection_snapshot import (
    LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
    NFL_SEASON_SCOPE_KIND,
    decode_late_start_current_projection_snapshot,
)
from fsffl.persistence.provisional_k_dst_forecast import (
    provisional_k_dst_forecast_artifact,
)
from fsffl.state.models import FrozenModel, LeagueState


class ProvisionalKDstMaterializationSummary(FrozenModel):
    season: int
    league_id: str
    league_state_id: str
    late_start_snapshot_available: bool
    rights_cleared_provider_ids: tuple[str, ...] = ()
    research_only_provider_ids: tuple[str, ...] = ()
    eligible_subject_keys: tuple[str, ...] = ()
    persisted_subject_keys: tuple[str, ...] = ()
    unavailable_subject_keys: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    model_version: str = "provisional-kdst-materialization-v1"


def materialize_provisional_k_dst_for_state(
    league_state: LeagueState,
    *,
    persistence_store: PersistenceStore | None,
) -> ProvisionalKDstMaterializationSummary:
    """Persist exact-state 2026 provisional K/DST where governed ROS evidence permits.

    Acquisition remains upstream. This orchestration never changes provider rights or
    source health; it only consumes the already-governed late-start snapshot and writes
    the distinct provisional artifact when the existing rights/independence/rule gates
    produce a usable result.
    """

    base = {
        "season": league_state.league.season,
        "league_id": league_state.league.league_id,
        "league_state_id": league_state.state_id,
    }
    if league_state.league.season != 2026:
        return ProvisionalKDstMaterializationSummary(
            **base,
            late_start_snapshot_available=False,
            blockers=("provisional_k_dst_exception_not_authorized_outside_2026",),
        )
    if persistence_store is None:
        return ProvisionalKDstMaterializationSummary(
            **base,
            late_start_snapshot_available=False,
            blockers=("persistence_unavailable",),
        )

    record = persistence_store.get_latest_reusable_artifact(
        artifact_kind=LATE_START_CURRENT_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        scope_kind=NFL_SEASON_SCOPE_KIND,
        scope_id="2026",
        model_version=LATE_START_SNAPSHOT_MODEL_VERSION,
    )
    if record is None:
        return ProvisionalKDstMaterializationSummary(
            **base,
            late_start_snapshot_available=False,
            blockers=("no_governed_2026_late_start_ros_snapshot",),
        )

    snapshot = decode_late_start_current_projection_snapshot(dict(record.payload))
    rights_cleared = tuple(
        sorted(
            item.source_id
            for item in snapshot.provider_evidence
            if item.production_rights_eligible
        )
    )
    research_only = tuple(
        sorted(
            item.source_id
            for item in snapshot.provider_evidence
            if not item.production_rights_eligible
        )
    )

    subjects: set[str] = set()
    for provider in snapshot.provider_evidence:
        if not provider.production_rights_eligible:
            continue
        accepted = set(provider.accepted_subject_keys)
        for row in provider.raw_rows:
            subject_key = ros_subject_key(row)
            if subject_key in accepted:
                subjects.add(subject_key)

    if not subjects:
        blockers = ["no_rights_cleared_accepted_ros_subjects"]
        if research_only:
            blockers.append("research_only_ros_sources_cannot_promote_private_beta_forecast")
        return ProvisionalKDstMaterializationSummary(
            **base,
            late_start_snapshot_available=True,
            rights_cleared_provider_ids=rights_cleared,
            research_only_provider_ids=research_only,
            blockers=tuple(blockers),
        )

    persisted: list[str] = []
    unavailable: list[str] = []
    for subject_key in sorted(subjects):
        try:
            forecast = build_provisional_k_dst_forecast(
                snapshot,
                league_id=league_state.league.league_id,
                league_state_id=league_state.state_id,
                subject_key=subject_key,
                rules=league_state.league.rules,
            )
        except ValueError:
            unavailable.append(subject_key)
            continue
        if not forecast.available:
            unavailable.append(subject_key)
            continue
        persistence_store.put_artifact(
            provisional_k_dst_forecast_artifact(forecast=forecast)
        )
        persisted.append(subject_key)

    blockers: list[str] = []
    if unavailable:
        blockers.append("some_subjects_have_no_governed_supported_scoring_coordinates")
    if not persisted:
        blockers.append("no_provisional_k_dst_subject_acquired_usable_authority")

    return ProvisionalKDstMaterializationSummary(
        **base,
        late_start_snapshot_available=True,
        rights_cleared_provider_ids=rights_cleared,
        research_only_provider_ids=research_only,
        eligible_subject_keys=tuple(sorted(subjects)),
        persisted_subject_keys=tuple(persisted),
        unavailable_subject_keys=tuple(unavailable),
        blockers=tuple(blockers),
    )
