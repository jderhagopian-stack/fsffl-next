from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .decision_quality import DecisionQualityComponent


class DirectionalEvidenceDirection(StrEnum):
    UNFAVORABLE = "unfavorable"
    NEUTRAL = "neutral"
    FAVORABLE = "favorable"


class DirectionalEvidenceScoreRange(FrozenModel):
    score_lower: Annotated[float, Field(ge=0, le=100)]
    score_center: Annotated[float, Field(ge=0, le=100)]
    score_upper: Annotated[float, Field(ge=0, le=100)]

    @model_validator(mode="after")
    def validate_scores(self) -> "DirectionalEvidenceScoreRange":
        if not self.score_lower <= self.score_center <= self.score_upper:
            raise ValueError("directional score range must satisfy lower <= center <= upper")
        return self


class DirectionalEvidenceNormalizationPolicy(FrozenModel):
    """Explicit mapping for evidence that supports direction but not magnitude.

    Historical research often establishes that a channel favored one side without
    supporting a defensible cardinal effect size. This policy keeps that evidence
    usable while making the score range, neutral point, provenance, and uncertainty
    explicit. There are deliberately no default ranges.
    """

    component_id: str
    authority_id: str
    overlap_group: str
    unfavorable: DirectionalEvidenceScoreRange
    neutral: DirectionalEvidenceScoreRange
    favorable: DirectionalEvidenceScoreRange
    evidence_through: datetime
    model_version: str
    provenance: str

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("directional normalization evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "DirectionalEvidenceNormalizationPolicy":
        if any(
            not value.strip()
            for value in (
                self.component_id,
                self.authority_id,
                self.overlap_group,
                self.model_version,
                self.provenance,
            )
        ):
            raise ValueError("directional normalization metadata cannot be blank")
        if not (
            self.unfavorable.score_center
            <= self.neutral.score_center
            <= self.favorable.score_center
        ):
            raise ValueError("directional center scores must be ordered unfavorable <= neutral <= favorable")
        return self


def normalize_directional_decision_quality_component(
    *,
    direction: DirectionalEvidenceDirection,
    as_of: datetime,
    evidence_through: datetime,
    confidence: float,
    policy: DirectionalEvidenceNormalizationPolicy,
) -> DecisionQualityComponent:
    """Create a broad Decision component without manufacturing a raw magnitude."""

    if as_of.tzinfo is None or evidence_through.tzinfo is None:
        raise ValueError("directional evidence timestamps must be timezone-aware")
    if not 0 <= confidence <= 1:
        raise ValueError("directional evidence confidence must be between 0 and 1")
    if policy.evidence_through > as_of:
        raise ValueError("directional normalization policy uses evidence unavailable at as_of")
    if evidence_through > as_of:
        raise ValueError("directional evidence uses information unavailable at as_of")

    score_range = {
        DirectionalEvidenceDirection.UNFAVORABLE: policy.unfavorable,
        DirectionalEvidenceDirection.NEUTRAL: policy.neutral,
        DirectionalEvidenceDirection.FAVORABLE: policy.favorable,
    }[direction]

    return DecisionQualityComponent(
        component_id=policy.component_id,
        authority_id=policy.authority_id,
        overlap_group=policy.overlap_group,
        score_lower=score_range.score_lower,
        score_center=score_range.score_center,
        score_upper=score_range.score_upper,
        confidence=confidence,
        evidence_through=max(policy.evidence_through, evidence_through),
        model_version=policy.model_version,
        provenance=policy.provenance,
    )
