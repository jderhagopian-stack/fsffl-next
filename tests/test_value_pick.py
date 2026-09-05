from datetime import datetime, timezone
from math import isclose, sqrt

import pytest

from fsffl.value.models import ValueDistribution, ValueScale
from fsffl.value.pick import PickOutcome, PickOutcomeSet, estimate_pick_value


AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)
SCALE = ValueScale(scale_id="fsffl-economic", version="v1", unit_label="value units")


def test_pick_value_uses_exact_slot_mixture_moments() -> None:
    outcomes = PickOutcomeSet(
        outcomes=(
            PickOutcome(slot=1, probability=0.25, value=ValueDistribution(mean=1000.0, stddev=100.0)),
            PickOutcome(slot=2, probability=0.75, value=ValueDistribution(mean=600.0, stddev=80.0)),
        )
    )

    result = estimate_pick_value(
        outcomes,
        asset_id="2027-round1-teamA",
        scale=SCALE,
        as_of=AS_OF,
        draft_season=2027,
        round=1,
        model_version="pick-v1",
        class_strength_model_version="class-v1",
        slot_uncertainty_model_version="slot-v1",
    )

    expected_mean = 700.0
    expected_second = 0.25 * (100.0**2 + 1000.0**2) + 0.75 * (80.0**2 + 600.0**2)
    assert result.distribution.mean == expected_mean
    assert isclose(result.distribution.stddev, sqrt(expected_second - expected_mean**2))
    assert result.distribution.p10 is None


def test_pick_outcomes_require_unique_slots_and_probability_mass_one() -> None:
    with pytest.raises(ValueError):
        PickOutcomeSet(
            outcomes=(
                PickOutcome(slot=1, probability=0.5, value=ValueDistribution(mean=1.0)),
                PickOutcome(slot=1, probability=0.5, value=ValueDistribution(mean=2.0)),
            )
        )

    with pytest.raises(ValueError):
        PickOutcomeSet(
            outcomes=(PickOutcome(slot=1, probability=0.9, value=ValueDistribution(mean=1.0)),)
        )
