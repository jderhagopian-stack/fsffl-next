from __future__ import annotations

from math import sqrt
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, Position

from .models import ForecastDistribution


class CareerTransitionEvidence(FrozenModel):
    """Empirically estimated one-season football transition.

    Values are inputs produced by historical calibration, not hard-coded career
    curves.  `conditional_production_multiplier` describes expected production
    next season conditional on remaining an active/relevant player;
    `survival_probability` carries attrition separately so dynasty value is not
    smuggled into the football forecast.
    """

    position: Position
    age_years: float | None = Field(default=None, ge=0)
    experience_years: int | None = Field(default=None, ge=0)
    sample_size: Annotated[int, Field(ge=1)]
    conditional_production_multiplier: Annotated[float, Field(ge=0)]
    survival_probability: Annotated[float, Field(ge=0, le=1)]
    conditional_stddev_multiplier: Annotated[float, Field(gt=0)] = 1.0
    model_version: str
    evidence_through_season: Annotated[int, Field(ge=1900)]

    @model_validator(mode="after")
    def require_nonempty_version(self) -> "CareerTransitionEvidence":
        if not self.model_version.strip():
            raise ValueError("model_version cannot be empty")
        return self


class MultiYearForecastPoint(FrozenModel):
    season_offset: Annotated[int, Field(ge=1)]
    distribution: ForecastDistribution
    cumulative_survival_probability: Annotated[float, Field(ge=0, le=1)]
    cumulative_conditional_production_multiplier: Annotated[float, Field(ge=0)]
    transition_model_version: str


def apply_career_transition(
    distribution: ForecastDistribution,
    evidence: CareerTransitionEvidence,
) -> ForecastDistribution:
    """Apply one evidence-backed career transition to a football forecast.

    The result is an unconditional outcome distribution: a player who does not
    survive the modeled football state contributes zero production.  This is a
    standard two-state mixture calculation and does not apply dynasty value,
    market price, roster fit, or competitive-window logic.
    """

    active_mean = distribution.mean * evidence.conditional_production_multiplier
    active_stddev = (
        distribution.stddev
        * evidence.conditional_production_multiplier
        * evidence.conditional_stddev_multiplier
    )
    survival = evidence.survival_probability
    mean = survival * active_mean
    second_moment = survival * (active_stddev**2 + active_mean**2)
    variance = max(0.0, second_moment - mean**2)

    # Quantiles of a zero-inflated mixture are not obtained by scaling provider
    # quantiles.  Leave them unset until the calibrated mixture is sampled or an
    # explicit distributional method supplies them.
    return ForecastDistribution(mean=mean, stddev=sqrt(variance))


def build_multi_year_forecast(
    base_distribution: ForecastDistribution,
    transitions: tuple[CareerTransitionEvidence, ...],
) -> tuple[MultiYearForecastPoint, ...]:
    """Roll an annual football forecast forward through calibrated transitions.

    No fallback coefficients exist here by design.  Callers must provide the
    evidence table selected for the player's point-in-time age/experience state.
    """

    current = base_distribution
    cumulative_survival = 1.0
    cumulative_production = 1.0
    output: list[MultiYearForecastPoint] = []

    for offset, transition in enumerate(transitions, start=1):
        current = apply_career_transition(current, transition)
        cumulative_survival *= transition.survival_probability
        cumulative_production *= transition.conditional_production_multiplier
        output.append(
            MultiYearForecastPoint(
                season_offset=offset,
                distribution=current,
                cumulative_survival_probability=cumulative_survival,
                cumulative_conditional_production_multiplier=cumulative_production,
                transition_model_version=transition.model_version,
            )
        )

    return tuple(output)
