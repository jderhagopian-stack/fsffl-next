from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality_normalization import (
    DecisionQualityNormalizationPoint,
    DecisionQualityNormalizationPolicy,
    normalize_decision_quality_component,
)


def policy() -> DecisionQualityNormalizationPolicy:
    return DecisionQualityNormalizationPolicy(
        component_id="economic",
        authority_id="trade-economic-net",
        overlap_group="economic-value",
        points=(
            DecisionQualityNormalizationPoint(raw_value=-100.0, score_lower=5, score_center=15, score_upper=30),
            DecisionQualityNormalizationPoint(raw_value=0.0, score_lower=45, score_center=50, score_upper=55),
            DecisionQualityNormalizationPoint(raw_value=100.0, score_lower=70, score_center=85, score_upper=95),
        ),
        evidence_through=datetime(2025, 1, 1, tzinfo=UTC),
        model_version="economic-normalizer-v1",
        provenance="tests:explicit-knots",
    )


def test_normalization_interpolates_center_and_uncertainty_without_extrapolation() -> None:
    component = normalize_decision_quality_component(
        raw_value=50.0,
        as_of=datetime(2025, 6, 1, tzinfo=UTC),
        confidence=0.8,
        policy=policy(),
    )

    assert component.score_lower == pytest.approx(57.5)
    assert component.score_center == pytest.approx(67.5)
    assert component.score_upper == pytest.approx(75.0)
    assert component.confidence == 0.8
    assert component.overlap_group == "economic-value"

    with pytest.raises(ValueError, match="outside governed normalization range"):
        normalize_decision_quality_component(
            raw_value=150.0,
            as_of=datetime(2025, 6, 1, tzinfo=UTC),
            confidence=1.0,
            policy=policy(),
        )


def test_normalization_rejects_future_policy_and_nonmonotonic_mapping() -> None:
    with pytest.raises(ValueError, match="unavailable at as_of"):
        normalize_decision_quality_component(
            raw_value=0.0,
            as_of=datetime(2024, 12, 1, tzinfo=UTC),
            confidence=1.0,
            policy=policy(),
        )

    with pytest.raises(ValueError, match="nondecreasing"):
        DecisionQualityNormalizationPolicy(
            component_id="bad",
            authority_id="authority",
            overlap_group="group",
            points=(
                DecisionQualityNormalizationPoint(raw_value=-1, score_lower=60, score_center=70, score_upper=80),
                DecisionQualityNormalizationPoint(raw_value=1, score_lower=30, score_center=40, score_upper=50),
            ),
            evidence_through=datetime(2025, 1, 1, tzinfo=UTC),
            model_version="bad-v1",
            provenance="tests",
        )


def test_normalization_requires_strictly_increasing_raw_knots() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        DecisionQualityNormalizationPolicy(
            component_id="bad",
            authority_id="authority",
            overlap_group="group",
            points=(
                DecisionQualityNormalizationPoint(raw_value=0, score_lower=40, score_center=50, score_upper=60),
                DecisionQualityNormalizationPoint(raw_value=0, score_lower=45, score_center=55, score_upper=65),
            ),
            evidence_through=datetime(2025, 1, 1, tzinfo=UTC),
            model_version="bad-v1",
            provenance="tests",
        )
