from math import isclose, sqrt

import pytest

from fsffl.forecast.career import apply_career_transition
from fsffl.forecast.career_calibration import (
    CareerTransitionCohort,
    CareerTransitionSample,
    fit_career_transition_evidence,
    select_transition_samples,
)
from fsffl.forecast.models import ForecastDistribution
from fsffl.state.models import Position


def sample(
    player_id: str,
    *,
    season: int = 2023,
    age: float = 24.0,
    experience: int = 2,
    prior: float = 100.0,
    next_value: float | None = 100.0,
    rookie: bool = False,
    stage: str = "prime",
    usage: float | None = 200.0,
) -> CareerTransitionSample:
    return CareerTransitionSample(
        player_id=player_id,
        from_season=season,
        position=Position.WR,
        age_years=age,
        experience_years=experience,
        career_stage=stage,
        is_rookie=rookie,
        prior_production=prior,
        prior_usage=usage,
        production_band="starter",
        usage_band="high",
        next_period_production=next_value,
    )


def cohort(**overrides: object) -> CareerTransitionCohort:
    values: dict[str, object] = {
        "name": "wr-prime-high-usage",
        "position": Position.WR,
        "career_stage": "prime",
        "usage_band": "high",
    }
    values.update(overrides)
    return CareerTransitionCohort(**values)


def test_fit_transition_separates_survival_and_conditional_development() -> None:
    samples = (
        sample("a", prior=100.0, next_value=110.0),
        sample("b", prior=200.0, next_value=180.0),
        sample("c", prior=120.0, next_value=None),
        sample("d", prior=80.0, next_value=80.0),
    )

    result = fit_career_transition_evidence(
        samples,
        cohort(),
        evidence_through_season=2024,
        model_version="career-2024-v1",
        minimum_sample_size=4,
        minimum_survivor_sample_size=3,
    )

    ratios = [1.1, 0.9, 1.0]
    expected_mean = sum(ratios) / 3
    expected_sample_variance = sum((value - expected_mean) ** 2 for value in ratios) / 2
    expected_stddev = sqrt(expected_sample_variance)

    assert result.sample_size == 4
    assert result.survivor_sample_size == 3
    assert isclose(result.survival_probability, 0.75)
    assert isclose(result.conditional_production_multiplier, 1.0)
    assert isclose(result.conditional_multiplier_stddev, expected_stddev)
    assert isclose(result.conditional_multiplier_standard_error, expected_stddev / sqrt(3))
    assert result.survival_standard_error > 0


def test_transition_fit_respects_point_in_time_evidence_cutoff() -> None:
    samples = (
        sample("known", season=2023),
        sample("future", season=2024),
    )

    selected = select_transition_samples(
        samples,
        cohort(),
        evidence_through_season=2024,
    )

    assert [row.player_id for row in selected] == ["known"]


def test_narrow_rookie_cohort_is_explicit_and_fails_closed_when_thin() -> None:
    samples = (
        sample("rookie", rookie=True, stage="rookie", experience=0),
        sample("veteran", rookie=False, stage="prime", experience=3),
    )
    rookie_cohort = cohort(
        name="wr-rookies",
        career_stage="rookie",
        rookie_only=True,
        usage_band=None,
    )

    with pytest.raises(ValueError, match="requires 2"):
        fit_career_transition_evidence(
            samples,
            rookie_cohort,
            evidence_through_season=2024,
            model_version="career-2024-v1",
            minimum_sample_size=2,
            minimum_survivor_sample_size=1,
        )


def test_cohort_can_distinguish_age_experience_usage_and_prior_performance() -> None:
    samples = (
        sample("match", age=24, experience=2, prior=150, usage=250),
        sample("too-old", age=29, experience=7, prior=150, usage=250),
        sample("low-usage", age=24, experience=2, prior=150, usage=90),
        sample("low-production", age=24, experience=2, prior=50, usage=250),
    )
    selected = select_transition_samples(
        samples,
        cohort(
            min_age_years=23,
            max_age_years=25,
            min_experience_years=1,
            max_experience_years=3,
            min_prior_production=100,
            min_prior_usage=200,
        ),
        evidence_through_season=2024,
    )

    assert [row.player_id for row in selected] == ["match"]


def test_empirical_multiplier_dispersion_widens_multi_year_uncertainty() -> None:
    evidence = fit_career_transition_evidence(
        (
            sample("a", prior=100, next_value=50),
            sample("b", prior=100, next_value=150),
        ),
        cohort(),
        evidence_through_season=2024,
        model_version="career-2024-v1",
        minimum_sample_size=2,
        minimum_survivor_sample_size=2,
    )
    base = ForecastDistribution(mean=100.0, stddev=10.0)

    result = apply_career_transition(base, evidence)

    assert isclose(result.mean, 100.0)
    assert result.stddev > base.stddev
