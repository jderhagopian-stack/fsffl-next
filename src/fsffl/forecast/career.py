from __future__ import annotations

from math import sqrt
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, Position

from .models import ForecastDistribution, ForecastHorizon


class CareerTransitionEvidence(FrozenModel):
    """Empirically estimated one-period football transition.

    Values are produced by historical calibration, not hard-coded career curves.
    `conditional_production_multiplier` describes expected production in the next
    period conditional on remaining active/relevant. `survival_probability`
    carries attrition separately so dynasty value is not smuggled into the
    football forecast.

    `conditional_multiplier_stddev` represents observed player-to-player
    transition dispersion while `conditional_multiplier_standard_error` captures
    uncertainty in the cohort estimate itself. Keeping both separate prevents
    long-horizon forecasts from becoming falsely precise when evidence is weak.
    """

    position: Position
    horizon: ForecastHorizon = ForecastHorizon.SEASON
    cohort_name: str | None = None
    age_years: float | None = Field(default=None, ge=0)
    experience_years: int | None = Field(default=None, ge=0)
    is_rookie_cohort: bool | None = None
    prior_production_quartile: int | None = Field(default=None, ge=1, le=4)
    sample_size: Annotated[int, Field(ge=1)]
    survivor_sample_size: Annotated[int, Field(ge=0)] = 0
    conditional_production_multiplier: Annotated[float, Field(ge=0)]
    survival_probability: Annotated[float, Field(ge=0, le=1)]
    conditional_multiplier_stddev: Annotated[float, Field(ge=0)] = 0.0
    conditional_multiplier_standard_error: Annotated[float, Field(ge=0)] = 0.0
    survival_standard_error: Annotated[float, Field(ge=0)] = 0.0
    conditional_stddev_multiplier: Annotated[float, Field(gt=0)] = 1.0
    model_version: str
    evidence_through_season: Annotated[int, Field(ge=1900)]

    @model_validator(mode="after")
    def validate_evidence(self) -> "CareerTransitionEvidence":
        if not self.model_version.strip():
            raise ValueError("model_version cannot be empty")
        if self.cohort_name is not None and not self.cohort_name.strip():
            raise ValueError("cohort_name cannot be blank")
        if self.survivor_sample_size > self.sample_size:
            raise ValueError("survivor_sample_size cannot exceed sample_size")
        if self.survival_probability > 0 and self.survivor_sample_size == 0:
            # Legacy/manual evidence may omit the survivor count; allow the
            # default only when no empirical dispersion/error is claimed.
            if (
                self.conditional_multiplier_stddev > 0
                or self.conditional_multiplier_standard_error > 0
                or self.survival_standard_error > 0
            ):
                raise ValueError(
                    "empirical transition uncertainty requires survivor_sample_size"
                )
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

    The result is an unconditional outcome distribution. A player who does not
    survive the modeled football state contributes zero production. Conditional
    on survival, the transition multiplier is itself treated as uncertain using
    both observed cohort dispersion and estimation error. This is a two-state
    mixture calculation and does not apply dynasty value, market price, roster
    fit, or competitive-window logic.
    """

    multiplier_mean = evidence.conditional_production_multiplier
    multiplier_variance = (
        evidence.conditional_multiplier_stddev**2
        + evidence.conditional_multiplier_standard_error**2
    )

    base_second_moment = distribution.stddev**2 + distribution.mean**2
    multiplier_second_moment = multiplier_variance + multiplier_mean**2

    active_mean = distribution.mean * multiplier_mean
    # For independent X (base production) and M (career transition),
    # E[(XM)^2] = E[X^2]E[M^2]. This propagates transition dispersion and
    # estimation uncertainty without inventing a long-horizon uncertainty
    # multiplier.
    active_second_moment = base_second_moment * multiplier_second_moment

    # Retained only for an explicitly calibrated forecast-error inflation term
    # that is distinct from dispersion in the career multiplier itself.
    if evidence.conditional_stddev_multiplier != 1.0:
        active_variance = max(0.0, active_second_moment - active_mean**2)
        active_variance *= evidence.conditional_stddev_multiplier**2
        active_second_moment = active_variance + active_mean**2

    survival = evidence.survival_probability
    mean = survival * active_mean
    second_moment = survival * active_second_moment
    variance = max(0.0, second_moment - mean**2)

    # Quantiles of a zero-inflated mixture are not obtained by scaling provider
    # quantiles. Leave them unset until the calibrated mixture is sampled or an
    # explicit distributional method supplies them.
    return ForecastDistribution(mean=mean, stddev=sqrt(variance))


def build_multi_year_forecast(
    base_distribution: ForecastDistribution,
    transitions: tuple[CareerTransitionEvidence, ...],
) -> tuple[MultiYearForecastPoint, ...]:
    """Roll an annual football forecast forward through calibrated transitions.

    No fallback coefficients exist here by design. Callers must provide the
    evidence table selected for the player's point-in-time age/experience/
    production state.
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
