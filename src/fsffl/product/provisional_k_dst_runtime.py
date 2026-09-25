from __future__ import annotations

from fsffl.forecast.k_dst_provisional import build_provisional_k_dst_forecast
from fsffl.forecast.late_start_snapshot import (
    LateStartCurrentProjectionSnapshot,
    ros_subject_key,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.persistence.provisional_k_dst_forecast import (
    provisional_k_dst_forecast_artifact,
)
from fsffl.state.models import FrozenModel, LeagueState


class ProvisionalKDstMaterializationSummary(FrozenModel):
    season: int
    league_id: str
    league_state_id: str
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
    snapshot: LateStartCurrentProjectionSnapshot,
    persistence_store: PersistenceStore,
) -> ProvisionalKDstMaterializationSummary:
    """Persist exact-state provisional K/DST from one explicitly governed ROS snapshot.

    Acquisition/source-health remains upstream. Callers must supply the snapshot that
    was acquired/revalidated for the current orchestration; this function deliberately
    does not look up an arbitrary older "latest" ROS snapshot and rebind it to a newer
    state after games may have completed.
    """

    if league_state.league.season != 2026 or snapshot.season != 2026:
        raise ValueError("provisional K/DST materialization is authorized only for 2026")
    if snapshot.evaluation_as_of > league_state.as_of:
        raise ValueError("provisional K/DST evidence cannot postdate canonical league state")

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
    if not subjects:
        blockers.append("no_rights_cleared_accepted_ros_subjects")
        if research_only:
            blockers.append(
                "research_only_ros_sources_cannot_promote_private_beta_forecast"
            )
    if unavailable:
        blockers.append(
            "some_subjects_have_no_governed_supported_scoring_coordinates"
        )
    if subjects and not persisted:
        blockers.append("no_provisional_k_dst_subject_acquired_usable_authority")

    return ProvisionalKDstMaterializationSummary(
        season=league_state.league.season,
        league_id=league_state.league.league_id,
        league_state_id=league_state.state_id,
        rights_cleared_provider_ids=rights_cleared,
        research_only_provider_ids=research_only,
        eligible_subject_keys=tuple(sorted(subjects)),
        persisted_subject_keys=tuple(persisted),
        unavailable_subject_keys=tuple(unavailable),
        blockers=tuple(blockers),
    )
