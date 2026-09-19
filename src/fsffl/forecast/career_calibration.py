from __future__ import annotations

from math import sqrt
from statistics import mean, stdev
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, Position

from .career import CareerTransitionEvidence
from .models import ForecastHorizon


class CareerTransitionSample(FrozenModel):
    """One point-in-time historical player-season transition.

    `next_period_production=None` means the player did not remain in the modeled
    active/relevant football population for the next period. A realized zero is
    different: zero may be supplied explicitly when the player remained in the
    population but produced zero.

    Cohort labels such as career stage, usage band, and production band are
    supplied by the research/calibration dataset. The core fitter intentionally
    does not invent universal thresholds for those concepts.
    """

    player_id: str
    from_season: Annotated[int, Field(ge=1900)]
    position: Position
    horizon: ForecastHorizon = ForecastHorizon.SEASON
    age_years: Annotated[float, Field(ge=0)]
    experience_years: Annotated[int, Field(ge=0)]
    career_stage: str
    is_rookie: bool
    prior_production: Annotated[float, Field(gt=0)]
    prior_usage: Annotated[float | None, Field(default=None, ge=0)] = None
    production_band: str | None = None
    usage_band: str | None = None
    next_period_production: Annotated[float | None, Field(default=None, ge=0)] = None

    @model_validator(mode="after")
    def validate_labels(self) -> "CareerTransitionSample":
        if not self.player_id.strip():
            raise ValueError("player_id cannot be blank")
        if not self.career_stage.strip():
            raise ValueError("career_stage cannot be blank")
        if self.production_band is not None and not self.production_band.strip():
            raise ValueError("production_band cannot be blank")
        if self.usage_band is not None and not self.usage_band.strip():
            raise ValueError("usage_band cannot be blank")
        return self


class CareerTransitionCohort(FrozenModel):
    """Explicit selector for an empirical career-transition cohort.

    Numeric ranges and categorical labels are caller-selected and versioned by
    the calibration study. This prevents opaque age/usage thresholds from being
    embedded in runtime forecast code while still allowing the evidence process
    to distinguish position, age/career stage, experience, prior production,
    usage, rookie status, and forecast horizon.
    """

    name: str
    position: Position
    horizon: ForecastHorizon = ForecastHorizon.SEASON
    min_age_years: Annotated[float | None, Field(default=None, ge=0)] = None
    max_age_years: Annotated[float | None, Field(default=None, ge=0)] = None
    min_experience_years: Annotated[int | None, Field(default=None, ge=0)] = None
    max_experience_years: Annotated[int | None, Field(default=None, ge=0)] = None
    career_stage: str | None = None
    rookie_only: bool | None = None
    min_prior_production: Annotated[float | None, Field(default=None, ge=0)] = None
    max_prior_production: Annotated[float | None, Field(default=None, ge=0)] = None
    min_prior_usage: Annotated[float | None, Field(default=None, ge=0)] = None
    max_prior_usage: Annotated[float | None, Field(default=None, ge=0)] = None
    production_band: str | None = None
    usage_band: str | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> "CareerTransitionCohort":
        if not self.name.strip():
            raise ValueError("name cannot be blank")
        pairs = (
            (self.min_age_years, self.max_age_years, "age"),
            (self.min_experience_years, self.max_experience_years, "experience"),
            (self.min_prior_production, self.max_prior_production, "production"),
            (self.min_prior_usage, self.max_prior_usage, "usage"),
        )
        for lower, upper, label in pairs:
            if lower is not None and upper is not None and lower > upper:
                raise ValueError(f"minimum {label} cannot exceed maximum {label}")
        for value, label in (
            (self.career_stage, "career_stage"),
            (self.production_band, "production_band"),
            (self.usage_band, "usage_band"),
        ):
            if value is not None and not value.strip():
                raise ValueError(f"{label} cannot be blank")
        return self

    def matches(self, sample: CareerTransitionSample) -> bool:
        if sample.position != self.position or sample.horizon != self.horizon:
            return False
        if self.min_age_years is not None and sample.age_years < self.min_age_years:
            return False
        if self.max_age_years is not None and sample.age_years > self.max_age_years:
            return False
        if (
            self.min_experience_years is not None
            and sample.experience_years < self.min_experience_years
        ):
            return False
        if (
            self.max_experience_years is not None
            and sample.experience_years > self.max_experience_years
        ):
            return False
        if self.career_stage is not None and sample.career_stage != self.career_stage:
            return False
        if self.rookie_only is not None and sample.is_rookie != self.rookie_only:
            return False
        if (
            self.min_prior_production is not None
            and sample.prior_production < self.min_prior_production
        ):
            return False
        if (
            self.max_prior_production is not None
            and sample.prior_production > self.max_prior_production
        ):
            return False
        if self.min_prior_usage is not None:
            if sample.prior_usage is None or sample.prior_usage < self.min_prior_usage:
                return False
        if self.max_prior_usage is not None:
            if sample.prior_usage is None or sample.prior_usage > self.max_prior_usage:
                return False
        if self.production_band is not None and sample.production_band != self.production_band:
            return False
        if self.usage_band is not None and sample.usage_band != self.usage_band:
            return False
        return True


def select_transition_samples(
    samples: tuple[CareerTransitionSample, ...],
    cohort: CareerTransitionCohort,
    *,
    evidence_through_season: int,
) -> tuple[CareerTransitionSample, ...]:
    """Select only transitions whose outcomes were knowable by the evidence cutoff."""

    return tuple(
        sample
        for sample in samples
        if sample.from_season + 1 <= evidence_through_season and cohort.matches(sample)
    )


def fit_career_transition_evidence(
    samples: tuple[CareerTransitionSample, ...],
    cohort: CareerTransitionCohort,
    *,
    evidence_through_season: int,
    model_version: str,
    minimum_sample_size: Annotated[int, Field(ge=1)],
    minimum_survivor_sample_size: Annotated[int, Field(ge=1)],
) -> CareerTransitionEvidence:
    """Estimate one career transition directly from historical player seasons.

    The thresholds are explicit study inputs, not hidden runtime constants. When
    a narrow cohort lacks support the function fails closed so the calibration
    study can deliberately pool to a broader, predeclared cohort rather than
    silently borrowing an arbitrary curve.
    """

    selected = select_transition_samples(
        samples,
        cohort,
        evidence_through_season=evidence_through_season,
    )
    if len(selected) < minimum_sample_size:
        raise ValueError(
            f"cohort {cohort.name!r} has {len(selected)} samples; "
            f"requires {minimum_sample_size}"
        )

    survivors = tuple(
        sample for sample in selected if sample.next_period_production is not None
    )
    if len(survivors) < minimum_survivor_sample_size:
        raise ValueError(
            f"cohort {cohort.name!r} has {len(survivors)} survivors; "
            f"requires {minimum_survivor_sample_size}"
        )

    ratios = [
        sample.next_period_production / sample.prior_production
        for sample in survivors
        if sample.next_period_production is not None
    ]
    multiplier_mean = mean(ratios)
    multiplier_stddev = stdev(ratios) if len(ratios) >= 2 else 0.0
    multiplier_standard_error = multiplier_stddev / sqrt(len(ratios))

    survival_probability = len(survivors) / len(selected)
    survival_standard_error = sqrt(
        survival_probability * (1.0 - survival_probability) / len(selected)
    )

    age_values = [sample.age_years for sample in selected]
    experience_values = [sample.experience_years for sample in selected]

    return CareerTransitionEvidence(
        position=cohort.position,
        horizon=cohort.horizon,
        cohort_name=cohort.name,
        age_years=mean(age_values),
        experience_years=round(mean(experience_values)),
        is_rookie_cohort=cohort.rookie_only,
        sample_size=len(selected),
        survivor_sample_size=len(survivors),
        conditional_production_multiplier=multiplier_mean,
        survival_probability=survival_probability,
        conditional_multiplier_stddev=multiplier_stddev,
        conditional_multiplier_standard_error=multiplier_standard_error,
        survival_standard_error=survival_standard_error,
        model_version=model_version,
        evidence_through_season=evidence_through_season,
    )
