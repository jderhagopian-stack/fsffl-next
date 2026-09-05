from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.materiality import (
    CompetitiveMaterialityPolicy,
    EconomicMaterialityPolicy,
    MaterialityDirection,
    classify_negative_delta,
    classify_positive_delta,
)
from fsffl.value.models import ValueScale


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def test_positive_materiality_requires_explicit_threshold() -> None:
    assert classify_positive_delta(0.21, absolute_threshold=0.20) == MaterialityDirection.MATERIAL_GAIN
    assert classify_positive_delta(-0.21, absolute_threshold=0.20) == MaterialityDirection.MATERIAL_LOSS
    assert classify_positive_delta(0.20, absolute_threshold=0.20) == MaterialityDirection.IMMATERIAL
    assert classify_positive_delta(None, absolute_threshold=0.20) == MaterialityDirection.UNAVAILABLE


def test_negative_direction_materiality_inverts_gain_and_loss() -> None:
    assert classify_negative_delta(-2.1, absolute_threshold=2.0) == MaterialityDirection.MATERIAL_GAIN
    assert classify_negative_delta(2.1, absolute_threshold=2.0) == MaterialityDirection.MATERIAL_LOSS


def test_materiality_policy_has_no_hidden_defaults_and_requires_provenance() -> None:
    policy = CompetitiveMaterialityPolicy(
        expected_wins_abs=0.2,
        playoff_probability_abs=0.02,
        first_place_probability_abs=0.01,
        lineup_drop_abs=1.0,
        model_version="test-policy-v1",
        evidence_through=AS_OF,
        provenance="synthetic test only",
    )
    assert policy.expected_wins_abs == 0.2

    with pytest.raises(ValueError, match="metadata"):
        CompetitiveMaterialityPolicy(
            expected_wins_abs=0.2,
            playoff_probability_abs=0.02,
            first_place_probability_abs=0.01,
            lineup_drop_abs=1.0,
            model_version="",
            evidence_through=AS_OF,
            provenance="synthetic test only",
        )


def test_economic_materiality_is_tied_to_value_scale() -> None:
    scale = ValueScale(scale_id="dynasty", version="v1", unit_label="points")
    policy = EconomicMaterialityPolicy(
        scale=scale,
        mean_value_abs=100.0,
        model_version="economic-materiality-test-v1",
        evidence_through=AS_OF,
        provenance="synthetic test only",
    )
    assert policy.scale == scale


def test_negative_threshold_fails_closed() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        classify_positive_delta(1.0, absolute_threshold=-0.1)
