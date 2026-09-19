from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


class DecisionQualityPolicyAuthority(StrEnum):
    BOUNDED_PRIOR = "bounded_prior"
    CALIBRATED = "calibrated"
    GOVERNED = "governed"


class DecisionQualityComponent(FrozenModel):
    """One normalized, authority-owned contribution to historical decision quality.

    Scores are normalized upstream onto 0..100. Decision does not convert raw
    football/economic quantities here; this boundary only combines already
    normalized evidence under an explicit policy. ``overlap_group`` lets the
    policy reject two components that encode the same underlying effect.
    """

    component_id: str
    authority_id: str
    overlap_group: str
    score_lower: Annotated[float, Field(ge=0, le=100)]
    score_center: Annotated[float, Field(ge=0, le=100)]
    score_upper: Annotated[float, Field(ge=0, le=100)]
    confidence: Annotated[float, Field(ge=0, le=1)]
    evidence_through: datetime
    model_version: str
    provenance: str

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality component evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_component(self) -> "DecisionQualityComponent":
        if any(not value.strip() for value in (
            self.component_id,
            self.authority_id,
            self.overlap_group,
            self.model_version,
            self.provenance,
        )):
            raise ValueError("decision-quality component metadata cannot be blank")
        if not self.score_lower <= self.score_center <= self.score_upper:
            raise ValueError("decision-quality component scores must satisfy lower <= center <= upper")
        return self


class DecisionQualityWeight(FrozenModel):
    component_id: str
    weight: Annotated[float, Field(gt=0, le=1)]

    @field_validator("component_id")
    @classmethod
    def require_component_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("decision-quality weight component_id cannot be blank")
        return value.strip()


class DecisionQualityPolicy(FrozenModel):
    """Explicit policy combining non-overlapping Decision evidence.

    There are deliberately no default components or weights. A bounded-prior
    policy is allowed, but it must identify itself as such and carry provenance so
    it can later be replaced by a calibrated policy without redesigning the API.
    """

    policy_id: str
    model_version: str
    provenance: str
    evidence_through: datetime
    weights: tuple[DecisionQualityWeight, ...]
    authority: DecisionQualityPolicyAuthority

    @field_validator("evidence_through")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality policy evidence_through must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "DecisionQualityPolicy":
        if any(not value.strip() for value in (self.policy_id, self.model_version, self.provenance)):
            raise ValueError("decision-quality policy metadata cannot be blank")
        if not self.weights:
            raise ValueError("decision-quality policy requires explicit component weights")
        ids = [item.component_id for item in self.weights]
        if len(ids) != len(set(ids)):
            raise ValueError("decision-quality policy component weights must be unique")
        if abs(sum(item.weight for item in self.weights) - 1.0) > 1e-9:
            raise ValueError("decision-quality policy weights must sum to 1")
        return self


class DecisionQualityScore(FrozenModel):
    transaction_id: str
    team_id: str
    as_of: datetime
    score_lower: Annotated[float, Field(ge=0, le=100)]
    score_center: Annotated[float, Field(ge=0, le=100)]
    score_upper: Annotated[float, Field(ge=0, le=100)]
    confidence: Annotated[float, Field(ge=0, le=1)]
    component_ids: tuple[str, ...]
    component_model_versions: tuple[str, ...]
    policy_id: str
    policy_version: str
    policy_authority: DecisionQualityPolicyAuthority
    model_version: str = "historical-decision-quality-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decision-quality score as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_score(self) -> "DecisionQualityScore":
        if any(not value.strip() for value in (
            self.transaction_id,
            self.team_id,
            self.policy_id,
            self.policy_version,
            self.model_version,
        )):
            raise ValueError("decision-quality score metadata cannot be blank")
        if not self.score_lower <= self.score_center <= self.score_upper:
            raise ValueError("decision-quality score must satisfy lower <= center <= upper")
        if not self.component_ids or not self.component_model_versions:
            raise ValueError("decision-quality score must record contributing components")
        return self


def score_historical_decision_quality(
    *,
    transaction_id: str,
    team_id: str,
    as_of: datetime,
    components: tuple[DecisionQualityComponent, ...],
    policy: DecisionQualityPolicy,
    model_version: str = "historical-decision-quality-v1",
) -> DecisionQualityScore:
    """Combine explicit normalized evidence without inventing hidden weights.

    Any missing policy component, future evidence, duplicate authority component,
    or overlapping contribution fails closed. The output retains a score interval
    and confidence so Analytics can express grading uncertainty explicitly.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if policy.evidence_through > as_of:
        raise ValueError("decision-quality policy uses evidence unavailable at as_of")
    by_id = {item.component_id: item for item in components}
    if len(by_id) != len(components):
        raise ValueError("decision-quality components must have unique component_id")

    required_ids = tuple(item.component_id for item in policy.weights)
    missing = tuple(sorted(set(required_ids) - set(by_id)))
    if missing:
        raise ValueError(f"decision-quality policy components are missing: {missing}")
    selected = tuple(by_id[item_id] for item_id in required_ids)
    if any(item.evidence_through > as_of for item in selected):
        raise ValueError("decision-quality component uses evidence unavailable at as_of")

    authority_ids = [item.authority_id for item in selected]
    if len(authority_ids) != len(set(authority_ids)):
        raise ValueError("decision-quality policy cannot count the same authority twice")
    overlap_groups = [item.overlap_group for item in selected]
    if len(overlap_groups) != len(set(overlap_groups)):
        raise ValueError("decision-quality policy contains overlapping/double-counted components")

    weights = {item.component_id: item.weight for item in policy.weights}
    lower = sum(item.score_lower * weights[item.component_id] for item in selected)
    center = sum(item.score_center * weights[item.component_id] for item in selected)
    upper = sum(item.score_upper * weights[item.component_id] for item in selected)
    confidence = sum(item.confidence * weights[item.component_id] for item in selected)

    return DecisionQualityScore(
        transaction_id=transaction_id,
        team_id=team_id,
        as_of=as_of,
        score_lower=lower,
        score_center=center,
        score_upper=upper,
        confidence=confidence,
        component_ids=required_ids,
        component_model_versions=tuple(item.model_version for item in selected),
        policy_id=policy.policy_id,
        policy_version=policy.model_version,
        policy_authority=policy.authority,
        model_version=model_version,
    )
