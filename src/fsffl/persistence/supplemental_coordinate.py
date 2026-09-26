from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import TypeAdapter

from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    FirstPartyFumblesLostSupplement,
)
from fsffl.forecast.supplemental_coordinate import (
    SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
    SupplementalCoordinateEnsemble,
    SupplementalCoordinateEvidencePackage,
    SupplementalCoordinateReuseAssessment,
    league_consumes_fumbles_lost,
)
from fsffl.state.models import FrozenModel, LeagueRules

from .annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
)
from .contracts import (
    ArtifactKey,
    PersistenceStore,
    ReusableArtifactRecord,
    canonical_fingerprint,
)
from .runtime_cache import (
    FORECAST_ARTIFACT_KIND,
    LEAGUE_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    SIMULATION_ARTIFACT_KIND,
    VALUE_ARTIFACT_KIND,
)


SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND = (
    "current_supplemental_coordinate_evidence"
)
SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND = (
    "current_supplemental_forecast_coordinate"
)
SUPPLEMENTAL_COORDINATE_SCOPE_KIND = "nfl_season_coordinate"

_package_adapter = TypeAdapter(SupplementalCoordinateEvidencePackage)
_ensemble_adapter = TypeAdapter(SupplementalCoordinateEnsemble)
_first_party_adapter = TypeAdapter(FirstPartyFumblesLostSupplement)


class SupplementalCoordinateInvalidationPlan(FrozenModel):
    coordinate_consumed: bool
    authority_changed: bool
    invalidate_artifact_kinds: tuple[str, ...]
    preserve_artifact_kinds: tuple[str, ...]
    rebuild_layers: tuple[str, ...]
    cause_kind: Literal[
        "supplemental_coordinate_changed",
        "supplemental_coordinate_stale",
    ] = "supplemental_coordinate_changed"
    cause_ref: str | None = None
    reason_codes: tuple[str, ...]


def supplemental_coordinate_scope_id(*, season: int) -> str:
    if season < 2000:
        raise ValueError("supplemental coordinate season is invalid")
    return f"{season}:fumbles_lost"


def encode_supplemental_coordinate_package(
    package: SupplementalCoordinateEvidencePackage,
) -> dict[str, object]:
    return _package_adapter.dump_python(package, mode="json")


def decode_supplemental_coordinate_package(
    payload: dict[str, object],
) -> SupplementalCoordinateEvidencePackage:
    package = _package_adapter.validate_python(payload)
    if package.model_version != SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION:
        raise ValueError("stored supplemental coordinate package model version is stale")
    if package.production_authority_promoted:
        raise ValueError("staged supplemental evidence artifact cannot promote authority")
    return package


def supplemental_coordinate_evidence_artifact(
    package: SupplementalCoordinateEvidencePackage,
) -> ReusableArtifactRecord:
    """Persist source evidence without making it current Forecast truth."""

    payload = encode_supplemental_coordinate_package(package)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND,
            scope_kind=SUPPLEMENTAL_COORDINATE_SCOPE_KIND,
            scope_id=supplemental_coordinate_scope_id(season=package.season),
            input_fingerprint=canonical_fingerprint(
                package.season,
                package.metric.value,
                package.source_horizon.value,
                payload,
            ),
            model_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
        ),
        payload=payload,
        computed_at=max(source.captured_at for source in package.sources),
    )


def encode_supplemental_coordinate_ensemble(
    ensemble: SupplementalCoordinateEnsemble,
) -> dict[str, object]:
    return _ensemble_adapter.dump_python(ensemble, mode="json")


def decode_supplemental_coordinate_ensemble(
    payload: dict[str, object],
) -> SupplementalCoordinateEnsemble:
    ensemble = _ensemble_adapter.validate_python(payload)
    if ensemble.model_version != SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION:
        raise ValueError("stored supplemental coordinate ensemble model version is stale")
    return ensemble


def encode_first_party_fumbles_lost_supplement(
    supplement: FirstPartyFumblesLostSupplement,
) -> dict[str, object]:
    return _first_party_adapter.dump_python(supplement, mode="json")


def decode_first_party_fumbles_lost_supplement(
    payload: dict[str, object],
) -> FirstPartyFumblesLostSupplement:
    supplement = _first_party_adapter.validate_python(payload)
    if (
        supplement.supplement_model_version
        != FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
    ):
        raise ValueError("stored first-party FUMBLES_LOST supplement model is stale")
    return supplement


def first_party_fumbles_lost_supplement_artifact(
    supplement: FirstPartyFumblesLostSupplement,
) -> ReusableArtifactRecord:
    """Persist Forecast-owned current FUMBLES_LOST under the existing supplement seam."""

    payload = encode_first_party_fumbles_lost_supplement(supplement)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND,
            scope_kind=SUPPLEMENTAL_COORDINATE_SCOPE_KIND,
            scope_id=supplemental_coordinate_scope_id(season=supplement.season),
            input_fingerprint=canonical_fingerprint(
                supplement.season,
                supplement.league_state_id,
                supplement.completed_through_week,
                supplement.model_version,
                supplement.calibration_scalar,
                supplement.current_input_sha256,
                supplement.authority_fingerprint,
            ),
            model_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
        ),
        payload=payload,
        computed_at=supplement.authority_valid_from,
    )


def supplemental_coordinate_ensemble_artifact(
    ensemble: SupplementalCoordinateEnsemble,
) -> ReusableArtifactRecord:
    """Persist a future certified target-period coordinate separately from Forecast."""

    payload = encode_supplemental_coordinate_ensemble(ensemble)
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND,
            scope_kind=SUPPLEMENTAL_COORDINATE_SCOPE_KIND,
            scope_id=supplemental_coordinate_scope_id(season=ensemble.season),
            input_fingerprint=canonical_fingerprint(
                ensemble.season,
                ensemble.metric,
                ensemble.evidence_horizon,
                ensemble.target_horizon,
                ensemble.target_period_start.isoformat(),
                ensemble.target_period_end.isoformat(),
                ensemble.source_ids,
                ensemble.independence_groups,
                ensemble.uncertainty_evidence_id,
                ensemble.uncertainty_model_version,
                payload,
            ),
            model_version=SUPPLEMENTAL_COORDINATE_CONTRACT_VERSION,
        ),
        payload=payload,
        computed_at=ensemble.authority_valid_from,
    )


def plan_fumbles_lost_supplement_invalidation(
    rules: LeagueRules,
    *,
    previous_authority_fingerprint: str | None,
    new_authority_fingerprint: str | None,
    reuse_assessment: SupplementalCoordinateReuseAssessment | None = None,
) -> SupplementalCoordinateInvalidationPlan:
    """Plan only the dependencies a certified FUMBLES_LOST change can affect."""

    consumed = league_consumes_fumbles_lost(rules)
    changed = (
        bool(new_authority_fingerprint)
        and new_authority_fingerprint != previous_authority_fingerprint
    )
    preserved = (
        PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
        ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
        VALUE_ARTIFACT_KIND,
    )
    stale = reuse_assessment is not None and not reuse_assessment.reusable
    if consumed and stale:
        return SupplementalCoordinateInvalidationPlan(
            coordinate_consumed=True,
            authority_changed=changed,
            invalidate_artifact_kinds=(
                FORECAST_ARTIFACT_KIND,
                SIMULATION_ARTIFACT_KIND,
            ),
            preserve_artifact_kinds=preserved,
            rebuild_layers=(
                "current_forecast",
                "simulation",
                "forecast_derived_team_intelligence",
            ),
            cause_kind="supplemental_coordinate_stale",
            cause_ref=new_authority_fingerprint or previous_authority_fingerprint,
            reason_codes=(
                reuse_assessment.reason_codes
                if reuse_assessment is not None
                else ("supplemental_coordinate_stale",)
            ),
        )

    if not consumed:
        return SupplementalCoordinateInvalidationPlan(
            coordinate_consumed=False,
            authority_changed=changed,
            invalidate_artifact_kinds=(),
            preserve_artifact_kinds=preserved,
            rebuild_layers=(),
            cause_ref=new_authority_fingerprint,
            reason_codes=("league_does_not_score_fumbles_lost",),
        )
    if not changed:
        return SupplementalCoordinateInvalidationPlan(
            coordinate_consumed=True,
            authority_changed=False,
            invalidate_artifact_kinds=(),
            preserve_artifact_kinds=preserved,
            rebuild_layers=(),
            cause_ref=new_authority_fingerprint,
            reason_codes=("supplement_authority_fingerprint_unchanged",),
        )
    return SupplementalCoordinateInvalidationPlan(
        coordinate_consumed=True,
        authority_changed=True,
        invalidate_artifact_kinds=(
            FORECAST_ARTIFACT_KIND,
            SIMULATION_ARTIFACT_KIND,
        ),
        preserve_artifact_kinds=preserved,
        rebuild_layers=(
            "current_forecast",
            "simulation",
            "forecast_derived_team_intelligence",
        ),
        cause_ref=new_authority_fingerprint,
        reason_codes=("certified_fumbles_lost_coordinate_changed",),
    )


def apply_fumbles_lost_supplement_invalidation(
    store: PersistenceStore,
    *,
    league_state_id: str,
    plan: SupplementalCoordinateInvalidationPlan,
    observed_at: datetime | None = None,
) -> None:
    """Invalidate exact-State current dependencies; never preseason or current Value."""

    if not plan.invalidate_artifact_kinds:
        return
    store.invalidate_scope(
        scope_kind=LEAGUE_SCOPE_KIND,
        scope_id=league_state_id,
        cause_kind=plan.cause_kind,
        cause_ref=plan.cause_ref,
        artifact_kinds=plan.invalidate_artifact_kinds,
        observed_at=observed_at,
    )
