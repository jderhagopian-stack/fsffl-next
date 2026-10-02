from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import DraftPick, FrozenModel, LeagueState

from .historical_pick import (
    GovernedDraftSlotValueCurve,
    HistoricalDraftSlotObservation,
    build_governed_draft_slot_value_curve,
)
from .models import PickValueEstimate, ValueDistribution, ValueScale
from .pick import PickOutcome, PickOutcomeSet, estimate_pick_value


ORIGIN_AWARE_PICK_VALUE_MODEL_VERSION = "origin-aware-pick-value-v1"
NO_GOVERNED_CLASS_ADJUSTMENT = "no-governed-class-adjustment"
NO_GOVERNED_HORIZON_ADJUSTMENT = "no-governed-horizon-adjustment"
AUTHORITATIVE_SIMULATION_COUNT = 50_000


class OriginAwarePickValueStatus(StrEnum):
    ORIGIN_AWARE_AUTHORITATIVE = "origin_aware_authoritative"
    ORIGIN_AWARE_PREVIEW = "origin_aware_preview_non_authoritative"
    GENERIC_FALLBACK = "generic_fallback"
    PARTIAL_MISSING_SLOT_VALUE_EVIDENCE = "partial_missing_slot_value_evidence"
    UNSUPPORTED_FUTURE_SEASON = "unsupported_future_season"
    UNAVAILABLE = "unavailable"


class OriginSlotProbabilityEvidence(FrozenModel):
    """Simulation-owned exact slot probability translated at the runtime boundary."""

    slot_in_round: Annotated[int, Field(ge=1)]
    probability: Annotated[float, Field(gt=0.0, le=1.0)]


class OriginPickProbabilityEvidence(FrozenModel):
    """Value-neutral upstream probability evidence for one origin team's next pick.

    Runtime/orchestration translates the authoritative Simulation output into this
    contract. Value consumes probabilities and provenance without importing or
    depending on NEXT-4 Simulation/Team Utility implementation types.
    """

    draft_season: Annotated[int, Field(ge=1900)]
    original_team_id: str
    slot_probabilities: tuple[OriginSlotProbabilityEvidence, ...]
    expected_slot: Annotated[float, Field(ge=1.0)]
    median_slot: Annotated[int, Field(ge=1)]
    early_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    mid_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    late_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    simulation_count: Annotated[int, Field(ge=1)]
    simulation_model_version: str
    simulation_input_fingerprint: str
    draft_order_policy_id: str
    draft_order_policy_version: str
    draft_order_policy_authority: str
    draft_order_projection_model_version: str
    provenance: str

    @model_validator(mode="after")
    def validate_probability_evidence(self) -> "OriginPickProbabilityEvidence":
        identifiers = (
            self.original_team_id,
            self.simulation_model_version,
            self.simulation_input_fingerprint,
            self.draft_order_policy_id,
            self.draft_order_policy_version,
            self.draft_order_policy_authority,
            self.draft_order_projection_model_version,
            self.provenance,
        )
        if any(not value.strip() for value in identifiers):
            raise ValueError("origin pick probability evidence identifiers cannot be blank")
        if not self.slot_probabilities:
            raise ValueError("origin pick probability evidence requires exact slots")
        slots = [item.slot_in_round for item in self.slot_probabilities]
        if len(slots) != len(set(slots)):
            raise ValueError("origin pick probability slots must be unique")
        if abs(sum(item.probability for item in self.slot_probabilities) - 1.0) > 1e-9:
            raise ValueError("origin pick probability evidence must sum to one")
        if abs(
            self.early_probability + self.mid_probability + self.late_probability - 1.0
        ) > 1e-9:
            raise ValueError("origin pick tier summaries must sum to one")
        return self


class GenericPickValuePrior(FrozenModel):
    """Value-owned generic season/round prior with no origin-team authority."""

    draft_season: Annotated[int, Field(ge=1900)]
    round: Annotated[int, Field(ge=1)]
    distribution: ValueDistribution
    scale: ValueScale
    as_of: datetime
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("generic pick prior as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "GenericPickValuePrior":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("generic pick prior version/provenance cannot be blank")
        return self


class OriginAwarePickValueResult(FrozenModel):
    """One canonical pick's Value result with origin and ownership kept separate."""

    pick_id: str
    original_team_id: str
    owner_team_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    round: Annotated[int, Field(ge=1)]
    status: OriginAwarePickValueStatus
    authoritative: bool
    origin_aware_estimate: PickValueEstimate | None = None
    generic_fallback_estimate: PickValueEstimate | None = None
    fallback_reason: str | None = None

    slot_probabilities: tuple[OriginSlotProbabilityEvidence, ...] = ()
    expected_slot: float | None = Field(default=None, ge=1.0)
    median_slot: int | None = Field(default=None, ge=1)
    early_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    mid_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    late_probability: float | None = Field(default=None, ge=0.0, le=1.0)

    simulation_count: int | None = Field(default=None, ge=1)
    simulation_model_version: str | None = None
    simulation_input_fingerprint: str | None = None
    draft_order_policy_id: str | None = None
    draft_order_policy_version: str | None = None
    draft_order_policy_authority: str | None = None

    slot_value_curve_model_version: str | None = None
    slot_value_evidence_seasons: tuple[int, ...] = ()
    slot_value_source_model_versions: tuple[str, ...] = ()
    missing_slots: tuple[int, ...] = ()

    class_strength_status: str = "not_applied_no_governed_evidence"
    class_strength_model_version: str = NO_GOVERNED_CLASS_ADJUSTMENT
    horizon_adjustment_status: str = "not_applied_no_governed_evidence"
    horizon_adjustment_model_version: str = NO_GOVERNED_HORIZON_ADJUSTMENT

    dependency_fingerprint: str
    provenance: tuple[str, ...] = ()
    model_version: str = ORIGIN_AWARE_PICK_VALUE_MODEL_VERSION

    @model_validator(mode="after")
    def validate_result(self) -> "OriginAwarePickValueResult":
        for value in (
            self.pick_id,
            self.original_team_id,
            self.owner_team_id,
            self.dependency_fingerprint,
            self.model_version,
        ):
            if not value.strip():
                raise ValueError("origin-aware pick Value identifiers cannot be blank")
        if self.authoritative != (
            self.status == OriginAwarePickValueStatus.ORIGIN_AWARE_AUTHORITATIVE
        ):
            raise ValueError("authoritative flag must match origin-aware authoritative status")
        if self.origin_aware_estimate is not None:
            if self.origin_aware_estimate.asset_id != self.pick_id:
                raise ValueError("origin-aware estimate must describe the canonical pick")
            if not self.slot_probabilities:
                raise ValueError("origin-aware estimate requires exact slot probabilities")
        if self.generic_fallback_estimate is not None:
            if self.generic_fallback_estimate.asset_id != self.pick_id:
                raise ValueError("generic fallback must describe the canonical pick")
        if self.status in {
            OriginAwarePickValueStatus.ORIGIN_AWARE_AUTHORITATIVE,
            OriginAwarePickValueStatus.ORIGIN_AWARE_PREVIEW,
        } and self.origin_aware_estimate is None:
            raise ValueError("origin-aware Value status requires an origin-aware estimate")
        if self.status == OriginAwarePickValueStatus.GENERIC_FALLBACK:
            if self.generic_fallback_estimate is None:
                raise ValueError("generic fallback status requires a generic estimate")
            if self.origin_aware_estimate is not None:
                raise ValueError("generic fallback cannot masquerade as origin-aware")
        if self.status in {
            OriginAwarePickValueStatus.PARTIAL_MISSING_SLOT_VALUE_EVIDENCE,
            OriginAwarePickValueStatus.UNSUPPORTED_FUTURE_SEASON,
            OriginAwarePickValueStatus.UNAVAILABLE,
        } and self.origin_aware_estimate is not None:
            raise ValueError("non-origin-aware status cannot expose an origin-aware estimate")
        return self

    @property
    def effective_estimate(self) -> PickValueEstimate | None:
        return self.origin_aware_estimate or self.generic_fallback_estimate


def _stable_fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _prior_by_coordinate(
    priors: tuple[GenericPickValuePrior, ...],
) -> dict[tuple[int, int], GenericPickValuePrior]:
    result: dict[tuple[int, int], GenericPickValuePrior] = {}
    for prior in priors:
        key = (prior.draft_season, prior.round)
        if key in result:
            raise ValueError("generic pick priors must be unique by season/round")
        result[key] = prior
    return result


def _fallback_estimate(
    pick: DraftPick,
    prior: GenericPickValuePrior | None,
    *,
    as_of: datetime,
    model_version: str,
) -> PickValueEstimate | None:
    if prior is None:
        return None
    if prior.as_of > as_of:
        raise ValueError("generic pick prior cannot postdate Value as_of")
    return PickValueEstimate(
        asset_id=pick.pick_id,
        distribution=prior.distribution,
        scale=prior.scale,
        as_of=as_of,
        draft_season=pick.season,
        round=pick.round,
        model_version=f"{model_version}:generic-fallback",
        class_strength_model_version=NO_GOVERNED_CLASS_ADJUSTMENT,
        slot_uncertainty_model_version="generic-season-round-prior:no-origin-slot",
    )


def _curve_identity(curve: GovernedDraftSlotValueCurve) -> dict[str, object]:
    return {
        "round": curve.round,
        "as_of": curve.as_of.isoformat(),
        "scale": curve.scale.model_dump(mode="json"),
        "model_version": curve.model_version,
        "slots": [
            {
                "slot": row.slot_in_round,
                "value": row.value.model_dump(mode="json"),
                "evidence_seasons": row.evidence_seasons,
                "source_model_versions": row.source_model_versions,
                "dominance_adjusted": row.dominance_adjusted,
            }
            for row in curve.slots
        ],
    }


def _simulation_identity(
    distribution: OriginPickProbabilityEvidence,
) -> dict[str, object]:
    return {
        "simulation_count": distribution.simulation_count,
        "simulation_model_version": distribution.simulation_model_version,
        "simulation_input_fingerprint": distribution.simulation_input_fingerprint,
        "draft_order_policy_id": distribution.draft_order_policy_id,
        "draft_order_policy_version": distribution.draft_order_policy_version,
        "draft_order_policy_authority": distribution.draft_order_policy_authority,
        "draft_order_projection_model_version": (
            distribution.draft_order_projection_model_version
        ),
        "slot_probabilities": [
            row.model_dump(mode="json") for row in distribution.slot_probabilities
        ],
    }


def _base_result(
    *,
    pick: DraftPick,
    owner_team_id: str,
    status: OriginAwarePickValueStatus,
    authoritative: bool,
    dependency_payload: dict[str, object],
    model_version: str,
    origin_aware_estimate: PickValueEstimate | None = None,
    fallback: PickValueEstimate | None = None,
    fallback_reason: str | None = None,
    distribution: OriginPickProbabilityEvidence | None = None,
    missing_slots: tuple[int, ...] = (),
    curve: GovernedDraftSlotValueCurve | None = None,
    provenance: tuple[str, ...] = (),
) -> OriginAwarePickValueResult:
    slot_rows = distribution.slot_probabilities if distribution is not None else ()
    source_versions = (
        tuple(
            sorted(
                {
                    version
                    for row in curve.slots
                    for version in row.source_model_versions
                }
            )
        )
        if curve is not None
        else ()
    )
    evidence_seasons = (
        tuple(
            sorted(
                {
                    season
                    for row in curve.slots
                    for season in row.evidence_seasons
                }
            )
        )
        if curve is not None
        else ()
    )
    return OriginAwarePickValueResult(
        pick_id=pick.pick_id,
        original_team_id=pick.original_team_id,
        owner_team_id=owner_team_id,
        draft_season=pick.season,
        round=pick.round,
        status=status,
        authoritative=authoritative,
        origin_aware_estimate=origin_aware_estimate,
        generic_fallback_estimate=fallback,
        fallback_reason=fallback_reason,
        slot_probabilities=slot_rows,
        expected_slot=(distribution.expected_slot if distribution is not None else None),
        median_slot=(distribution.median_slot if distribution is not None else None),
        early_probability=(
            distribution.early_probability if distribution is not None else None
        ),
        mid_probability=(
            distribution.mid_probability if distribution is not None else None
        ),
        late_probability=(
            distribution.late_probability if distribution is not None else None
        ),
        simulation_count=(
            distribution.simulation_count if distribution is not None else None
        ),
        simulation_model_version=(
            distribution.simulation_model_version
            if distribution is not None
            else None
        ),
        simulation_input_fingerprint=(
            distribution.simulation_input_fingerprint
            if distribution is not None
            else None
        ),
        draft_order_policy_id=(
            distribution.draft_order_policy_id if distribution is not None else None
        ),
        draft_order_policy_version=(
            distribution.draft_order_policy_version if distribution is not None else None
        ),
        draft_order_policy_authority=(
            distribution.draft_order_policy_authority
            if distribution is not None
            else None
        ),
        slot_value_curve_model_version=(
            curve.model_version if curve is not None else None
        ),
        slot_value_evidence_seasons=evidence_seasons,
        slot_value_source_model_versions=source_versions,
        missing_slots=missing_slots,
        dependency_fingerprint=_stable_fingerprint(dependency_payload),
        provenance=provenance,
        model_version=model_version,
    )


def build_origin_aware_pick_values(
    league_state: LeagueState,
    origin_slot_evidence: tuple[OriginPickProbabilityEvidence, ...],
    *,
    slot_value_observations: tuple[HistoricalDraftSlotObservation, ...] = (),
    slot_value_scale: ValueScale | None = None,
    governed_slot_value_curves: tuple[GovernedDraftSlotValueCurve, ...] = (),
    generic_priors: tuple[GenericPickValuePrior, ...] = (),
    authoritative_simulation_count: int = AUTHORITATIVE_SIMULATION_COUNT,
    model_version: str = ORIGIN_AWARE_PICK_VALUE_MODEL_VERSION,
) -> tuple[OriginAwarePickValueResult, ...]:
    """Value canonical picks without recreating Simulation or draft-order authority.

    Next-draft picks may use exact team-of-origin probability evidence translated
    from Simulation by runtime/orchestration. Value never imports or recreates
    Simulation. The economic expectation is the full exact probability mixture over
    the governed slot-value curve. Farther-future picks never inherit next-draft
    probabilities.
    """

    if league_state.as_of.tzinfo is None:
        raise ValueError("origin-aware pick Value requires timezone-aware State")
    if authoritative_simulation_count < 1:
        raise ValueError("authoritative Simulation count must be positive")
    if not model_version.strip():
        raise ValueError("origin-aware pick Value model_version cannot be blank")

    distribution_by_origin: dict[str, OriginPickProbabilityEvidence] = {}
    next_season = league_state.league.season + 1
    for row in origin_slot_evidence:
        if row.draft_season != next_season:
            raise ValueError(
                "Value origin-slot evidence must be scoped to the next draft season"
            )
        if row.original_team_id in distribution_by_origin:
            raise ValueError("origin-slot evidence requires unique origin teams")
        distribution_by_origin[row.original_team_id] = row

    owner_by_pick = {
        row.pick_id: row.owner_team_id for row in league_state.pick_ownership
    }
    if len(owner_by_pick) != len(league_state.pick_ownership):
        raise ValueError("canonical pick ownership requires unique pick ids")
    priors = _prior_by_coordinate(generic_priors)
    curve_by_round: dict[int, GovernedDraftSlotValueCurve] = {}
    if governed_slot_value_curves:
        rounds = [curve.round for curve in governed_slot_value_curves]
        if len(rounds) != len(set(rounds)):
            raise ValueError("governed slot-value curves require unique rounds")
        scales = {curve.scale for curve in governed_slot_value_curves}
        if len(scales) != 1:
            raise ValueError("governed slot-value curves must share one ValueScale")
        if slot_value_observations:
            raise ValueError(
                "provide governed slot-value curves or raw slot observations, not both"
            )
        curve_by_round.update(
            {curve.round: curve for curve in governed_slot_value_curves}
        )
    elif slot_value_scale is None:
        raise ValueError(
            "slot_value_scale is required when governed slot-value curves are absent"
        )

    results: list[OriginAwarePickValueResult] = []
    for pick in sorted(
        league_state.draft_picks,
        key=lambda item: (item.season, item.round, item.pick_id),
    ):
        owner = owner_by_pick.get(pick.pick_id)
        if owner is None:
            raise ValueError("canonical pick ownership is required for Value")
        prior = priors.get((pick.season, pick.round))

        if pick.season != next_season:
            fallback = _fallback_estimate(
                pick, prior, as_of=league_state.as_of, model_version=model_version
            )
            status = (
                OriginAwarePickValueStatus.GENERIC_FALLBACK
                if fallback is not None
                else OriginAwarePickValueStatus.UNSUPPORTED_FUTURE_SEASON
            )
            reason = (
                "Simulation origin-team slot probability is authoritative only for "
                f"the next draft season ({next_season}); no farther-future "
                "distribution was extrapolated."
            )
            results.append(
                _base_result(
                    pick=pick,
                    owner_team_id=owner,
                    status=status,
                    authoritative=False,
                    fallback=fallback,
                    fallback_reason=reason,
                    dependency_payload={
                        "pick": {
                            "pick_id": pick.pick_id,
                            "season": pick.season,
                            "round": pick.round,
                            "original_team_id": pick.original_team_id,
                        },
                        "generic_prior": (
                            prior.model_dump(mode="json") if prior is not None else None
                        ),
                        "model_version": model_version,
                    },
                    model_version=model_version,
                    provenance=((prior.provenance,) if prior is not None else ()),
                )
            )
            continue

        distribution = distribution_by_origin.get(pick.original_team_id)
        if distribution is None:
            fallback = _fallback_estimate(
                pick, prior, as_of=league_state.as_of, model_version=model_version
            )
            status = (
                OriginAwarePickValueStatus.GENERIC_FALLBACK
                if fallback is not None
                else OriginAwarePickValueStatus.UNAVAILABLE
            )
            reason = (
                "Matching next-draft Simulation origin distribution is unavailable; "
                "Value did not infer team strength or draft slot."
            )
            results.append(
                _base_result(
                    pick=pick,
                    owner_team_id=owner,
                    status=status,
                    authoritative=False,
                    fallback=fallback,
                    fallback_reason=reason,
                    dependency_payload={
                        "pick": {
                            "pick_id": pick.pick_id,
                            "season": pick.season,
                            "round": pick.round,
                            "original_team_id": pick.original_team_id,
                        },
                        "origin_slot_evidence": None,
                        "generic_prior": (
                            prior.model_dump(mode="json") if prior is not None else None
                        ),
                        "model_version": model_version,
                    },
                    model_version=model_version,
                    provenance=((prior.provenance,) if prior is not None else ()),
                )
            )
            continue

        if any(
            row.slot_in_round > league_state.league.rules.team_count
            for row in distribution.slot_probabilities
        ):
            raise ValueError("origin distribution slot exceeds league team count")

        curve = curve_by_round.get(pick.round)
        if curve is None:
            if slot_value_scale is None:
                raise ValueError(
                    f"governed slot-value curve missing for rookie round {pick.round}"
                )
            curve = build_governed_draft_slot_value_curve(
                slot_value_observations,
                round=pick.round,
                as_of=league_state.as_of,
                scale=slot_value_scale,
                league_rules=league_state.league.rules,
            )
            curve_by_round[pick.round] = curve
        if curve.as_of > league_state.as_of:
            raise ValueError("governed slot-value curve cannot postdate LeagueState")
        if slot_value_scale is not None and curve.scale != slot_value_scale:
            raise ValueError("slot-value curve scale does not match requested ValueScale")
        curve_by_slot = {row.slot_in_round: row for row in curve.slots}
        probability_slots = {
            row.slot_in_round
            for row in distribution.slot_probabilities
            if row.probability > 0
        }
        missing_slots = tuple(sorted(probability_slots - set(curve_by_slot)))
        dependency_payload = {
            "pick": {
                "pick_id": pick.pick_id,
                "season": pick.season,
                "round": pick.round,
                "original_team_id": pick.original_team_id,
            },
            "simulation": _simulation_identity(distribution),
            "slot_value_curve": _curve_identity(curve),
            "class_strength": NO_GOVERNED_CLASS_ADJUSTMENT,
            "horizon_adjustment": NO_GOVERNED_HORIZON_ADJUSTMENT,
            "generic_prior": (
                prior.model_dump(mode="json") if prior is not None else None
            ),
            "model_version": model_version,
        }

        if missing_slots:
            fallback = _fallback_estimate(
                pick, prior, as_of=league_state.as_of, model_version=model_version
            )
            status = (
                OriginAwarePickValueStatus.GENERIC_FALLBACK
                if fallback is not None
                else OriginAwarePickValueStatus.PARTIAL_MISSING_SLOT_VALUE_EVIDENCE
            )
            reason = (
                "Exact economic evidence is missing for probability-bearing slot(s): "
                + ", ".join(str(slot) for slot in missing_slots)
                + ". No round-median or early/mid/late interpolation was used."
            )
            results.append(
                _base_result(
                    pick=pick,
                    owner_team_id=owner,
                    status=status,
                    authoritative=False,
                    fallback=fallback,
                    fallback_reason=reason,
                    distribution=distribution,
                    missing_slots=missing_slots,
                    curve=curve,
                    dependency_payload=dependency_payload,
                    model_version=model_version,
                    provenance=(
                        tuple(
                            sorted(
                                {
                                    item
                                    for row in curve.slots
                                    for item in row.provenance
                                }
                            )
                        )
                        + ((prior.provenance,) if prior is not None else ())
                    ),
                )
            )
            continue

        outcome_set = PickOutcomeSet(
            outcomes=tuple(
                PickOutcome(
                    slot=row.slot_in_round,
                    probability=row.probability,
                    value=curve_by_slot[row.slot_in_round].value,
                )
                for row in distribution.slot_probabilities
                if row.probability > 0
            )
        )
        slot_uncertainty_version = (
            f"{distribution.simulation_model_version}+"
            f"{distribution.draft_order_policy_id}:"
            f"{distribution.draft_order_policy_version}+"
            f"{distribution.draft_order_projection_model_version}"
        )
        estimate = estimate_pick_value(
            outcome_set,
            asset_id=pick.pick_id,
            scale=curve.scale,
            as_of=league_state.as_of,
            draft_season=pick.season,
            round=pick.round,
            model_version=model_version,
            class_strength_model_version=NO_GOVERNED_CLASS_ADJUSTMENT,
            slot_uncertainty_model_version=slot_uncertainty_version,
        )
        simulation_authoritative = (
            distribution.simulation_count == authoritative_simulation_count
        )
        status = (
            OriginAwarePickValueStatus.ORIGIN_AWARE_AUTHORITATIVE
            if simulation_authoritative
            else OriginAwarePickValueStatus.ORIGIN_AWARE_PREVIEW
        )
        result = _base_result(
            pick=pick,
            owner_team_id=owner,
            status=status,
            authoritative=simulation_authoritative,
            origin_aware_estimate=estimate,
            distribution=distribution,
            curve=curve,
            dependency_payload=dependency_payload,
            model_version=model_version,
            provenance=tuple(
                sorted(
                    {
                        item
                        for row in curve.slots
                        if row.slot_in_round in probability_slots
                        for item in row.provenance
                    }
                )
            )
            + (
                (
                    "No governed draft-class strength adjustment applied.",
                    "No governed horizon/time-to-realization adjustment applied.",
                    distribution.provenance,
                )
            ),
        )
        results.append(result)

    return tuple(results)
