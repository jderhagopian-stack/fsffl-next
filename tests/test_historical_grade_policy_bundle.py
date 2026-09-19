from datetime import UTC, datetime

import pytest

from fsffl.analytics.historical_grade_policy_bundle import HistoricalGradePolicyBundle
from fsffl.analytics.historical_trade import GradeBand, GovernedGradePolicy
from fsffl.trade_decision.decision_quality_normalization import (
    DecisionQualityNormalizationPoint,
    DecisionQualityNormalizationPolicy,
)
from fsffl.trade_decision.decision_quality_weight_robustness import (
    DecisionQualityWeightBound,
    DecisionQualityWeightFamily,
)


AS_OF = datetime(2026, 1, 1, tzinfo=UTC)


def normalizer(component_id: str, authority: str, overlap: str) -> DecisionQualityNormalizationPolicy:
    return DecisionQualityNormalizationPolicy(
        component_id=component_id,
        authority_id=authority,
        overlap_group=overlap,
        points=(
            DecisionQualityNormalizationPoint(raw_value=-1, score_lower=20, score_center=30, score_upper=40),
            DecisionQualityNormalizationPoint(raw_value=1, score_lower=60, score_center=70, score_upper=80),
        ),
        evidence_through=AS_OF,
        model_version=f"{component_id}-v1",
        provenance="tests",
    )


def grade_policy() -> GovernedGradePolicy:
    return GovernedGradePolicy(
        policy_id="grades",
        model_version="v1",
        provenance="tests",
        bands=(GradeBand(minimum_score=0, letter="F"), GradeBand(minimum_score=60, letter="C")),
    )


def test_bundle_requires_exact_nonoverlapping_weighted_components() -> None:
    policies = (
        normalizer("economic", "economic-authority", "economic"),
        normalizer("competitive", "competitive-authority", "competitive"),
    )
    family = DecisionQualityWeightFamily(
        family_id="weights",
        model_version="v1",
        provenance="tests",
        bounds=(
            DecisionQualityWeightBound(component_id="economic", minimum_weight=0.4, maximum_weight=0.6),
            DecisionQualityWeightBound(component_id="competitive", minimum_weight=0.4, maximum_weight=0.6),
        ),
    )
    bundle = HistoricalGradePolicyBundle(
        bundle_id="bundle-v1",
        model_version="v1",
        provenance="tests:explicit-runtime-config",
        normalization_policies=policies,
        weight_family=family,
        grade_policy=grade_policy(),
    )
    assert bundle.normalization_policy("economic").component_id == "economic"

    bad_family = DecisionQualityWeightFamily(
        family_id="bad",
        model_version="v1",
        provenance="tests",
        bounds=(DecisionQualityWeightBound(component_id="economic", minimum_weight=1, maximum_weight=1),),
    )
    with pytest.raises(ValueError, match="exactly the bundle normalization components"):
        HistoricalGradePolicyBundle(
            bundle_id="bad",
            model_version="v1",
            provenance="tests",
            normalization_policies=policies,
            weight_family=bad_family,
            grade_policy=grade_policy(),
        )
