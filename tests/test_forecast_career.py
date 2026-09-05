from math import isclose, sqrt

import pytest

from fsffl.forecast.career import (
    CareerTransitionEvidence,
    apply_career_transition,
    build_multi_year_forecast,
)
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import Position


def evidence(*, multiplier: float = 1.0, survival: float = 1.0, stddev_multiplier: float = 1.0) -> CareerTransitionEvidence:
    return CareerTransitionEvidence(
        position=Position.RB,
        age_years=26.0,
        experience_years=4,
        sample_size=250,
        conditional_production_multiplier=multiplier,
        survival_probability=survival,
        conditional_stddev_multiplier=stddev_multiplier,
        model_version="career-transition-test-v1",
        evidence_through_season=2025,
    )


def test_career_transition_separates_survival_from_conditional_production() -> None:
    base = ForecastDistribution(mean=200.0, stddev=40.0, p10=150.0, p50=200.0, p90=250.0)
    transition = evidence(multiplier=0.9, survival=0.8)

    result = apply_career_transition(base, transition)

    active_mean = 180.0
    active_stddev = 36.0
    expected_mean = 0.8 * active_mean
    expected_variance = 0.8 * (active_stddev**2 + active_mean**2) - expected_mean**2
    assert isclose(result.mean, expected_mean)
    assert isclose(result.stddev, sqrt(expected_variance))
    assert result.p10 is None
    assert result.p50 is None
    assert result.p90 is None


def test_multi_year_forecast_requires_explicit_evidence_and_accumulates_transitions() -> None:
    base = ForecastDistribution(mean=100.0, stddev=10.0)
    transitions = (
        evidence(multiplier=1.1, survival=0.9),
        evidence(multiplier=0.8, survival=0.75),
    )

    points = build_multi_year_forecast(base, transitions)

    assert len(points) == 2
    assert points[0].season_offset == 1
    assert isclose(points[0].cumulative_survival_probability, 0.9)
    assert isclose(points[0].cumulative_conditional_production_multiplier, 1.1)
    assert points[1].season_offset == 2
    assert isclose(points[1].cumulative_survival_probability, 0.675)
    assert isclose(points[1].cumulative_conditional_production_multiplier, 0.88)


def test_transition_validation_rejects_unbounded_or_unidentified_inputs() -> None:
    with pytest.raises(ValueError):
        evidence(survival=1.1)
    with pytest.raises(ValueError):
        CareerTransitionEvidence(
            position=Position.WR,
            sample_size=1,
            conditional_production_multiplier=1.0,
            survival_probability=1.0,
            model_version=" ",
            evidence_through_season=2025,
        )
