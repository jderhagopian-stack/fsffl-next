from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .decision_quality import DecisionQualityComponent


class DecisionQualityNormalizationPoint(FrozenModel):
    raw_value: float
    score_lower: Annotated[float, Field(ge=0, le=100)]
    score_center: Annotated[float, Field(ge=0, le=100)]
    score_upper: Annotated[float, Field(ge=0, le=100)]

    @model_validator(mode="after")
    def validate_scores(self) -> "DecisionQualityNormalizationPoint":
        if not self.score_lower <= self.score_center <= self.score_upper:
            raise ValueError("normalization point scores must satisfy lower <= center <= upper")
        return self


class DecisionQualityNormalizationPolicy(FrozenModel):
    """Explicit piecewise mapping from one oriented raw channel to 0..100.

    The raw value must already be oriented so larger means better for the focal
    team. Knots and uncertainty are supplied by calibration/governance. This
    function deliberately does not extrapolate beyond the governed evidence range.
    """

    component_id: str
    authority_id: str
    overlap_group: str
    points: tuple[DecisionQualityNormalizationPoint, ...]
    evidence_through: datetime
    model_version: str
    provenance: str

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("normalization policy evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "DecisionQualityNormalizationPolicy":
        if any(not value.strip() for value in (
            self.component_id,
            self.authority_id,
            self.overlap_group,
            self.model_version,
            self.provenance,
        )):
            raise ValueError("normalization policy metadata cannot be blank")
        if len(self.points) < 2:
            raise ValueError("normalization policy requires at least two points")
        raw = [point.raw_value for point in self.points]
        if raw != sorted(raw) or len(raw) != len(set(raw)):
            raise ValueError("normalization raw values must be unique and strictly increasing")
        centers = [point.score_center for point in self.points]
        if centers != sorted(centers):
            raise ValueError("normalization center scores must be nondecreasing")
        return self


def _interpolate(left: float, right: float, fraction: float) -> float:
    return left + (right - left) * fraction


def normalize_decision_quality_component(
    *,
    raw_value: float,
    as_of: datetime,
    confidence: float,
    policy: DecisionQualityNormalizationPolicy,
    evidence_through: datetime | None = None,
) -> DecisionQualityComponent:
    """Normalize one non-overlapping Decision channel without hidden thresholds.

    ``evidence_through`` is the cutoff of the raw channel evidence. The emitted
    component records the later of that cutoff and the policy evidence cutoff, so
    downstream historical grading cannot accidentally understate its information
    boundary. When omitted, the policy cutoff is retained for backward-compatible
    callers whose raw evidence has no later timestamp.
    """

    if as_of.tzinfo is None:
        raise ValueError("normalization as_of must be timezone-aware")
    if confidence < 0 or confidence > 1:
        raise ValueError("normalization confidence must be between 0 and 1")
    if policy.evidence_through > as_of:
        raise ValueError("normalization policy uses evidence unavailable at as_of")
    if evidence_through is not None:
        if evidence_through.tzinfo is None:
            raise ValueError("normalization evidence_through must be timezone-aware")
        if evidence_through > as_of:
            raise ValueError("normalization channel uses evidence unavailable at as_of")
    if raw_value < policy.points[0].raw_value or raw_value > policy.points[-1].raw_value:
        raise ValueError("raw value lies outside governed normalization range")

    for point in policy.points:
        if raw_value == point.raw_value:
            lower, center, upper = point.score_lower, point.score_center, point.score_upper
            break
    else:
        for left, right in zip(policy.points, policy.points[1:]):
            if left.raw_value < raw_value < right.raw_value:
                fraction = (raw_value - left.raw_value) / (right.raw_value - left.raw_value)
                lower = _interpolate(left.score_lower, right.score_lower, fraction)
                center = _interpolate(left.score_center, right.score_center, fraction)
                upper = _interpolate(left.score_upper, right.score_upper, fraction)
                break
        else:
            raise ValueError("raw value could not be bracketed by normalization points")

    component_evidence_through = policy.evidence_through
    if evidence_through is not None and evidence_through > component_evidence_through:
        component_evidence_through = evidence_through

    return DecisionQualityComponent(
        component_id=policy.component_id,
        authority_id=policy.authority_id,
        overlap_group=policy.overlap_group,
        score_lower=lower,
        score_center=center,
        score_upper=upper,
        confidence=confidence,
        evidence_through=component_evidence_through,
        model_version=policy.model_version,
        provenance=policy.provenance,
    )
