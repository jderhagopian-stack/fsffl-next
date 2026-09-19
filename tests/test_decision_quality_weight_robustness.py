from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality import DecisionQualityComponent
from fsffl.trade_decision.decision_quality_weight_robustness import (
    DecisionQualityWeightBound,
    DecisionQualityWeightFamily,
    evaluate_weight_family_robustness,
)


def component(component_id: str, authority: str, group: str, lower: float, center: float, upper: float):
    return DecisionQualityComponent(
        component_id=component_id,
        authority_id=authority,
        overlap_group=group,
        score_lower=lower,
        score_center=center,
        score_upper=upper,
        confidence=0.8,
        evidence_through=datetime(2025, 1, 1, tzinfo=UTC),
        model_version=f"{component_id}-v1",
        provenance="tests",
    )


def family() -> DecisionQualityWeightFamily:
    return DecisionQualityWeightFamily(
        family_id="broad-research-family",
        model_version="v1",
        provenance="tests:explicit-bounds",
        bounds=(
            DecisionQualityWeightBound(component_id="economic", minimum_weight=0.2, maximum_weight=0.8),
            DecisionQualityWeightBound(component_id="competitive", minimum_weight=0.2, maximum_weight=0.8),
        ),
    )


def test_weight_robustness_computes_exact_extrema_over_bounded_simplex() -> None:
    envelope = evaluate_weight_family_robustness(
        components=(
            component("economic", "economic-authority", "economic", 70, 80, 90),
            component("competitive", "competitive-authority", "competitive", 30, 40, 50),
        ),
        family=family(),
    )

    assert envelope.score_lower == pytest.approx(38.0)
    assert envelope.center_score_minimum == pytest.approx(48.0)
    assert envelope.center_score_maximum == pytest.approx(72.0)
    assert envelope.score_upper == pytest.approx(82.0)
    assert envelope.lower_witness.weights["economic"] == pytest.approx(0.2)
    assert envelope.upper_witness.weights["economic"] == pytest.approx(0.8)


def test_weight_family_must_admit_a_unit_sum_vector() -> None:
    with pytest.raises(ValueError, match="admit at least one"):
        DecisionQualityWeightFamily(
            family_id="bad",
            model_version="v1",
            provenance="tests",
            bounds=(
                DecisionQualityWeightBound(component_id="a", minimum_weight=0.1, maximum_weight=0.2),
                DecisionQualityWeightBound(component_id="b", minimum_weight=0.1, maximum_weight=0.2),
            ),
        )


def test_weight_robustness_rejects_overlap_and_component_mismatch() -> None:
    with pytest.raises(ValueError, match="overlapping"):
        evaluate_weight_family_robustness(
            components=(
                component("economic", "a", "same", 40, 50, 60),
                component("competitive", "b", "same", 40, 50, 60),
            ),
            family=family(),
        )

    with pytest.raises(ValueError, match="exactly"):
        evaluate_weight_family_robustness(
            components=(component("economic", "a", "economic", 40, 50, 60),),
            family=family(),
        )
