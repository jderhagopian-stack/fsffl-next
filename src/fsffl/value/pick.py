from __future__ import annotations

from math import sqrt
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel

from .models import PickValueEstimate, ValueDistribution, ValueScale


class PickOutcome(FrozenModel):
    """One possible realized draft-slot outcome and its economic value.

    Slot probabilities and slot values are evidence inputs. This module only
    performs the probability mixture; it does not invent class-strength or slot
    coefficients.
    """

    slot: Annotated[int, Field(ge=1)]
    probability: Annotated[float, Field(gt=0, le=1)]
    value: ValueDistribution


class PickOutcomeSet(FrozenModel):
    outcomes: tuple[PickOutcome, ...]

    @model_validator(mode="after")
    def validate_distribution(self) -> "PickOutcomeSet":
        if not self.outcomes:
            raise ValueError("pick outcome set cannot be empty")
        slots = [outcome.slot for outcome in self.outcomes]
        if len(slots) != len(set(slots)):
            raise ValueError("pick outcome slots must be unique")
        probability = sum(outcome.probability for outcome in self.outcomes)
        if abs(probability - 1.0) > 1e-9:
            raise ValueError("pick outcome probabilities must sum to 1")
        return self


def estimate_pick_value(
    outcome_set: PickOutcomeSet,
    *,
    asset_id: str,
    scale: ValueScale,
    as_of,
    draft_season: int,
    round: int,
    model_version: str,
    class_strength_model_version: str,
    slot_uncertainty_model_version: str,
) -> PickValueEstimate:
    """Collapse explicit slot uncertainty into an unconditional pick distribution.

    Mean and variance use exact mixture moments. Quantiles intentionally remain
    unset because quantiles of a mixture cannot be recovered from component
    quantiles alone without an explicit distributional assumption or sampling.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    mean = sum(outcome.probability * outcome.value.mean for outcome in outcome_set.outcomes)
    second_moment = sum(
        outcome.probability * (outcome.value.stddev**2 + outcome.value.mean**2)
        for outcome in outcome_set.outcomes
    )
    variance = max(0.0, second_moment - mean**2)

    return PickValueEstimate(
        asset_id=asset_id,
        distribution=ValueDistribution(mean=mean, stddev=sqrt(variance)),
        scale=scale,
        as_of=as_of,
        draft_season=draft_season,
        round=round,
        model_version=model_version,
        class_strength_model_version=class_strength_model_version,
        slot_uncertainty_model_version=slot_uncertainty_model_version,
    )
