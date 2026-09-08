from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import DraftPick, FrozenModel, LeagueRules

from .models import PickValueEstimate, ValueDistribution, ValueScale
from .pick import PickOutcome, PickOutcomeSet, estimate_pick_value


class HistoricalDraftSlotObservation(FrozenModel):
    """A slot-value observation that became knowable at ``available_at``.

    The selected player's later career is not represented here. Upstream research
    must freeze the slot value using evidence available at the observation time.
    """

    draft_season: int
    round: Annotated[int, Field(ge=1)]
    slot_in_round: Annotated[int, Field(ge=1)]
    value: ValueDistribution
    scale: ValueScale
    available_at: datetime
    model_version: str
    provenance: str

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "HistoricalDraftSlotObservation":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("historical draft observation version/provenance cannot be blank")
        return self


class HistoricalSlotProbability(FrozenModel):
    slot_in_round: Annotated[int, Field(ge=1)]
    probability: Annotated[float, Field(gt=0, le=1)]
    evidence_as_of: datetime
    model_version: str
    provenance: str

    @field_validator("evidence_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("slot-probability evidence timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "HistoricalSlotProbability":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("slot-probability version/provenance cannot be blank")
        return self


class HorizonAdjustment(FrozenModel):
    """Explicit governed/research time adjustment supplied by Value research.

    There is deliberately no default factor. A factor of 1 means no adjustment.
    """

    seasons_to_realization: Annotated[int, Field(ge=0)]
    factor: Annotated[float, Field(gt=0)]
    model_version: str
    provenance: str

    @model_validator(mode="after")
    def validate_identity(self) -> "HorizonAdjustment":
        if not self.model_version.strip() or not self.provenance.strip():
            raise ValueError("horizon adjustment version/provenance cannot be blank")
        return self


class HistoricalPickCoordinateEvidence(FrozenModel):
    pick: DraftPick
    as_of: datetime
    observations: tuple[HistoricalDraftSlotObservation, ...]
    slot_probabilities: tuple[HistoricalSlotProbability, ...]
    exact_slot_in_round: Annotated[int | None, Field(default=None, ge=1)] = None
    exact_slot_known_at: datetime | None = None
    horizon_adjustment: HorizonAdjustment | None = None

    @field_validator("as_of", "exact_slot_known_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("historical pick timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_evidence(self) -> "HistoricalPickCoordinateEvidence":
        if self.exact_slot_in_round is not None:
            if self.exact_slot_known_at is None:
                raise ValueError("exact slot requires an evidence-availability timestamp")
            if self.exact_slot_known_at > self.as_of:
                raise ValueError("exact historical slot was not knowable at as_of")
        elif self.exact_slot_known_at is not None:
            raise ValueError("exact_slot_known_at requires exact_slot_in_round")
        if any(item.available_at > self.as_of for item in self.observations):
            raise ValueError("future draft observations cannot enter historical pick evidence")
        if any(item.evidence_as_of > self.as_of for item in self.slot_probabilities):
            raise ValueError("future slot probabilities cannot enter historical pick evidence")
        if self.horizon_adjustment is not None:
            expected = max(0, self.pick.season - self.as_of.year)
            if self.horizon_adjustment.seasons_to_realization != expected:
                raise ValueError("horizon adjustment must match pick/as_of horizon")
        return self


class HistoricalPickCoordinateResult(FrozenModel):
    estimate: PickValueEstimate | None = None
    status: str
    evidence_quality: str
    used_draft_seasons: tuple[int, ...] = ()
    missing_slots: tuple[int, ...] = ()
    exact_slot_used: bool = False
    provenance: tuple[str, ...] = ()
    model_version: str = "historical-pick-coordinate-v1"


def _aggregate_slot_values(
    observations: tuple[HistoricalDraftSlotObservation, ...],
    *,
    round: int,
    as_of: datetime,
    scale: ValueScale,
    league_rules: LeagueRules,
) -> tuple[dict[int, ValueDistribution], bool]:
    """Aggregate PIT slot evidence and enforce draft-position dominance.

    Within one otherwise identical rookie draft, an earlier overall pick weakly
    dominates a later pick because its manager can always select an asset that
    remains available later. Raw historical drafted-player evidence can violate
    that structural property through sampling noise. We therefore project the
    observed slot means onto a non-increasing curve using weighted pooled-adjacent
    violators. This is a no-arbitrage constraint, not a fitted economic coefficient.

    Missing slots remain missing. The projection only reorders evidence that
    already exists, and any mean adjustment is added to the reported uncertainty
    rather than hidden.
    """

    by_overall_slot: dict[int, list[ValueDistribution]] = defaultdict(list)
    for observation in observations:
        if observation.available_at > as_of or observation.scale != scale:
            continue
        if observation.round > league_rules.rookie_draft_rounds:
            continue
        if observation.slot_in_round > league_rules.team_count:
            raise ValueError("historical draft observation slot exceeds league team count")
        overall_slot = (observation.round - 1) * league_rules.team_count + observation.slot_in_round
        by_overall_slot[overall_slot].append(observation.value)

    raw: dict[int, tuple[float, float, int]] = {}
    for overall_slot, values in by_overall_slot.items():
        mean = sum(value.mean for value in values) / len(values)
        second = sum(value.stddev**2 + value.mean**2 for value in values) / len(values)
        raw[overall_slot] = (mean, sqrt(max(0.0, second - mean**2)), len(values))

    blocks: list[dict[str, object]] = []
    for overall_slot in sorted(raw):
        mean, _, count = raw[overall_slot]
        blocks.append({"slots": [overall_slot], "weight": float(count), "mean": mean})
        while len(blocks) >= 2 and float(blocks[-2]["mean"]) < float(blocks[-1]["mean"]):
            right = blocks.pop()
            left = blocks.pop()
            weight = float(left["weight"]) + float(right["weight"])
            pooled_mean = (
                float(left["mean"]) * float(left["weight"])
                + float(right["mean"]) * float(right["weight"])
            ) / weight
            blocks.append(
                {
                    "slots": list(left["slots"]) + list(right["slots"]),
                    "weight": weight,
                    "mean": pooled_mean,
                }
            )

    fitted: dict[int, float] = {}
    for block in blocks:
        for overall_slot in block["slots"]:
            fitted[int(overall_slot)] = float(block["mean"])

    adjusted = False
    result: dict[int, ValueDistribution] = {}
    for overall_slot, (raw_mean, raw_stddev, _) in raw.items():
        fitted_mean = fitted[overall_slot]
        if abs(fitted_mean - raw_mean) > 1e-12:
            adjusted = True
        round_number = ((overall_slot - 1) // league_rules.team_count) + 1
        slot_in_round = ((overall_slot - 1) % league_rules.team_count) + 1
        if round_number != round:
            continue
        adjustment = raw_mean - fitted_mean
        result[slot_in_round] = ValueDistribution(
            mean=fitted_mean,
            stddev=sqrt(raw_stddev**2 + adjustment**2),
        )
    return result, adjusted


def reconstruct_historical_pick_coordinate(
    evidence: HistoricalPickCoordinateEvidence,
    *,
    league_rules: LeagueRules,
    scale: ValueScale,
    model_version: str = "historical-pick-coordinate-v1",
) -> HistoricalPickCoordinateResult:
    """Reconstruct a pick value from only explicit point-in-time evidence.

    This function does not infer team strength, slot probabilities, draft-class
    strength, or time discount. Those remain authoritative upstream inputs.
    """

    if evidence.pick.round > league_rules.rookie_draft_rounds:
        return HistoricalPickCoordinateResult(
            status="EXCLUDED_OUTSIDE_LEAGUE_ROOKIE_DRAFT",
            evidence_quality="EXCLUDED",
            model_version=model_version,
        )

    slot_values, dominance_adjusted = _aggregate_slot_values(
        evidence.observations,
        round=evidence.pick.round,
        as_of=evidence.as_of,
        scale=scale,
        league_rules=league_rules,
    )

    if evidence.exact_slot_in_round is not None:
        probabilities = {evidence.exact_slot_in_round: 1.0}
        probability_version = "exact-slot"
        probability_provenance = "historically-known exact draft slot"
        exact = True
    else:
        probabilities = {item.slot_in_round: item.probability for item in evidence.slot_probabilities}
        if not probabilities:
            return HistoricalPickCoordinateResult(
                status="NOT_RECONSTRUCTED_MISSING_SLOT_PROBABILITY_EVIDENCE",
                evidence_quality="INSUFFICIENT",
                used_draft_seasons=tuple(sorted({item.draft_season for item in evidence.observations})),
                model_version=model_version,
            )
        if len(probabilities) != len(evidence.slot_probabilities):
            raise ValueError("historical slot probabilities must have unique slots")
        if abs(sum(probabilities.values()) - 1.0) > 1e-9:
            raise ValueError("historical slot probabilities must sum to 1")
        if any(slot > league_rules.team_count for slot in probabilities):
            raise ValueError("historical slot probability exceeds league team count")
        probability_version = "+".join(sorted({item.model_version for item in evidence.slot_probabilities}))
        probability_provenance = "; ".join(sorted({item.provenance for item in evidence.slot_probabilities}))
        exact = False

    missing = tuple(sorted(slot for slot in probabilities if slot not in slot_values))
    if missing:
        return HistoricalPickCoordinateResult(
            status="NOT_RECONSTRUCTED_MISSING_SLOT_VALUE_EVIDENCE",
            evidence_quality="INSUFFICIENT",
            used_draft_seasons=tuple(sorted({item.draft_season for item in evidence.observations})),
            missing_slots=missing,
            exact_slot_used=exact,
            provenance=(probability_provenance,),
            model_version=model_version,
        )

    factor = evidence.horizon_adjustment.factor if evidence.horizon_adjustment is not None else 1.0
    outcomes = PickOutcomeSet(
        outcomes=tuple(
            PickOutcome(
                slot=slot,
                probability=probability,
                value=ValueDistribution(
                    mean=slot_values[slot].mean * factor,
                    stddev=slot_values[slot].stddev * factor,
                ),
            )
            for slot, probability in sorted(probabilities.items())
        )
    )
    draft_versions = sorted({item.model_version for item in evidence.observations})
    class_version = "+".join(draft_versions) if draft_versions else "missing"
    if dominance_adjusted:
        class_version += "+draft-position-dominance-v1"
    if evidence.horizon_adjustment is not None:
        class_version += "+" + evidence.horizon_adjustment.model_version

    estimate = estimate_pick_value(
        outcomes,
        asset_id=evidence.pick.pick_id,
        scale=scale,
        as_of=evidence.as_of,
        draft_season=evidence.pick.season,
        round=evidence.pick.round,
        model_version=model_version,
        class_strength_model_version=class_version,
        slot_uncertainty_model_version=probability_version,
    )
    seasons = tuple(sorted({item.draft_season for item in evidence.observations}))
    quality = "HIGH" if exact and len(seasons) >= 2 else "MEDIUM" if len(seasons) >= 2 else "LOW"
    provenance = sorted({item.provenance for item in evidence.observations})
    provenance.append(probability_provenance)
    if dominance_adjusted:
        provenance.append("structural draft-position dominance projection")
    if evidence.horizon_adjustment is not None:
        provenance.append(evidence.horizon_adjustment.provenance)

    return HistoricalPickCoordinateResult(
        estimate=estimate,
        status="RECONSTRUCTED",
        evidence_quality=quality,
        used_draft_seasons=seasons,
        exact_slot_used=exact,
        provenance=tuple(provenance),
        model_version=model_version,
    )
