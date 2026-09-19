from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .decision_quality import DecisionQualityComponent


class DecisionQualityWeightBound(FrozenModel):
    component_id: str
    minimum_weight: Annotated[float, Field(ge=0, le=1)]
    maximum_weight: Annotated[float, Field(ge=0, le=1)]

    @field_validator("component_id")
    @classmethod
    def require_component_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("weight-bound component_id cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def validate_bounds(self) -> "DecisionQualityWeightBound":
        if self.minimum_weight > self.maximum_weight:
            raise ValueError("minimum_weight cannot exceed maximum_weight")
        return self


class DecisionQualityWeightFamily(FrozenModel):
    family_id: str
    model_version: str
    provenance: str
    bounds: tuple[DecisionQualityWeightBound, ...]

    @model_validator(mode="after")
    def validate_family(self) -> "DecisionQualityWeightFamily":
        if any(not value.strip() for value in (self.family_id, self.model_version, self.provenance)):
            raise ValueError("weight-family metadata cannot be blank")
        if not self.bounds:
            raise ValueError("weight family requires component bounds")
        ids = [item.component_id for item in self.bounds]
        if len(ids) != len(set(ids)):
            raise ValueError("weight-family component ids must be unique")
        minimum_total = sum(item.minimum_weight for item in self.bounds)
        maximum_total = sum(item.maximum_weight for item in self.bounds)
        if minimum_total > 1 + 1e-9 or maximum_total < 1 - 1e-9:
            raise ValueError("weight-family bounds must admit at least one weight vector summing to 1")
        return self


class DecisionQualityWeightWitness(FrozenModel):
    weights: dict[str, float]
    score: Annotated[float, Field(ge=0, le=100)]


class DecisionQualityWeightRobustnessEnvelope(FrozenModel):
    family_id: str
    family_version: str
    score_lower: Annotated[float, Field(ge=0, le=100)]
    center_score_minimum: Annotated[float, Field(ge=0, le=100)]
    center_score_maximum: Annotated[float, Field(ge=0, le=100)]
    score_upper: Annotated[float, Field(ge=0, le=100)]
    lower_witness: DecisionQualityWeightWitness
    upper_witness: DecisionQualityWeightWitness
    component_ids: tuple[str, ...]
    model_version: str = "decision-quality-weight-robustness-v1"

    @model_validator(mode="after")
    def validate_envelope(self) -> "DecisionQualityWeightRobustnessEnvelope":
        if not (
            self.score_lower
            <= self.center_score_minimum
            <= self.center_score_maximum
            <= self.score_upper
        ):
            raise ValueError("decision-quality robustness envelope is internally inconsistent")
        return self


def _extreme_weights(
    *,
    scores: dict[str, float],
    family: DecisionQualityWeightFamily,
    maximize: bool,
) -> DecisionQualityWeightWitness:
    weights = {item.component_id: item.minimum_weight for item in family.bounds}
    remaining = 1.0 - sum(weights.values())
    bound_by_id = {item.component_id: item for item in family.bounds}
    ordered = sorted(scores, key=lambda component_id: scores[component_id], reverse=maximize)
    for component_id in ordered:
        if remaining <= 1e-12:
            break
        bound = bound_by_id[component_id]
        capacity = bound.maximum_weight - weights[component_id]
        addition = min(capacity, remaining)
        weights[component_id] += addition
        remaining -= addition
    if remaining > 1e-9:
        raise ValueError("weight-family bounds could not construct a complete weight vector")
    score = sum(scores[component_id] * weight for component_id, weight in weights.items())
    return DecisionQualityWeightWitness(weights=weights, score=score)


def evaluate_weight_family_robustness(
    *,
    components: tuple[DecisionQualityComponent, ...],
    family: DecisionQualityWeightFamily,
    model_version: str = "decision-quality-weight-robustness-v1",
) -> DecisionQualityWeightRobustnessEnvelope:
    """Compute exact score extrema over all admissible bounded weight vectors.

    Because Decision quality is linear in channel weights, the extrema occur at
    the bounded-simplex edges and can be found greedily. This lets research use
    broad coefficient ranges without selecting one arbitrary hidden weighting.
    """

    by_id = {item.component_id: item for item in components}
    if len(by_id) != len(components):
        raise ValueError("decision-quality components must have unique ids")
    required = {item.component_id for item in family.bounds}
    if set(by_id) != required:
        raise ValueError("weight family must describe exactly the supplied components")
    authorities = [item.authority_id for item in components]
    if len(authorities) != len(set(authorities)):
        raise ValueError("weight robustness cannot count the same authority twice")
    overlap_groups = [item.overlap_group for item in components]
    if len(overlap_groups) != len(set(overlap_groups)):
        raise ValueError("weight robustness cannot count overlapping components twice")

    lower_scores = {item.component_id: item.score_lower for item in components}
    center_scores = {item.component_id: item.score_center for item in components}
    upper_scores = {item.component_id: item.score_upper for item in components}

    lower = _extreme_weights(scores=lower_scores, family=family, maximize=False)
    center_min = _extreme_weights(scores=center_scores, family=family, maximize=False)
    center_max = _extreme_weights(scores=center_scores, family=family, maximize=True)
    upper = _extreme_weights(scores=upper_scores, family=family, maximize=True)

    return DecisionQualityWeightRobustnessEnvelope(
        family_id=family.family_id,
        family_version=family.model_version,
        score_lower=lower.score,
        center_score_minimum=center_min.score,
        center_score_maximum=center_max.score,
        score_upper=upper.score,
        lower_witness=lower,
        upper_witness=upper,
        component_ids=tuple(item.component_id for item in family.bounds),
        model_version=model_version,
    )
