from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality_directional import (
    DirectionalEvidenceDirection,
    DirectionalEvidenceNormalizationPolicy,
    DirectionalEvidenceScoreRange,
    normalize_directional_decision_quality_component,
)
from fsffl.trade_decision.decision_quality_residual import unresolved_decision_quality_component
from fsffl.trade_decision.decision_quality_weight_robustness import (
    DecisionQualityWeightBound,
    DecisionQualityWeightFamily,
    evaluate_weight_family_robustness,
)


TRADE_AT = datetime(2023, 3, 12, 21, 21, 48, tzinfo=UTC)
EVIDENCE_THROUGH = datetime(2023, 3, 7, 12, 0, tzinfo=UTC)


def directional_policy(component_id: str, authority_id: str) -> DirectionalEvidenceNormalizationPolicy:
    return DirectionalEvidenceNormalizationPolicy(
        component_id=component_id,
        authority_id=authority_id,
        overlap_group=component_id,
        unfavorable=DirectionalEvidenceScoreRange(score_lower=0, score_center=25, score_upper=50),
        neutral=DirectionalEvidenceScoreRange(score_lower=40, score_center=50, score_upper=60),
        favorable=DirectionalEvidenceScoreRange(score_lower=50, score_center=75, score_upper=100),
        evidence_through=EVIDENCE_THROUGH,
        model_version="fsffl-research-directional-v1",
        provenance=(
            "FSFFL research regression only; broad direction-only mapping; "
            "not production or universal model truth"
        ),
    )


def research_weight_family() -> DecisionQualityWeightFamily:
    return DecisionQualityWeightFamily(
        family_id="fsffl-legacy-state-bounds-research-only",
        model_version="research-v1",
        provenance=(
            "legacy FSFFL expert-prior safety bounds: current 0.05-0.60, "
            "future 0.18-0.68, liquidity 0.07-0.24, resilience 0.08-0.18; "
            "unvalidated and used only as bounded regression provenance"
        ),
        bounds=(
            DecisionQualityWeightBound(component_id="current_impact", minimum_weight=0.05, maximum_weight=0.60),
            DecisionQualityWeightBound(component_id="future_asset_value", minimum_weight=0.18, maximum_weight=0.68),
            DecisionQualityWeightBound(component_id="liquidity", minimum_weight=0.07, maximum_weight=0.24),
            DecisionQualityWeightBound(component_id="resilience", minimum_weight=0.08, maximum_weight=0.18),
        ),
    )


def components(direction: DirectionalEvidenceDirection):
    current = normalize_directional_decision_quality_component(
        direction=direction,
        as_of=TRADE_AT,
        evidence_through=EVIDENCE_THROUGH,
        confidence=0.70,
        policy=directional_policy("current_impact", "pit-2023-current-impact-research"),
    )
    future = normalize_directional_decision_quality_component(
        direction=direction,
        as_of=TRADE_AT,
        evidence_through=EVIDENCE_THROUGH,
        confidence=0.85,
        policy=directional_policy("future_asset_value", "pit-2023-dynasty-value-research"),
    )
    liquidity = unresolved_decision_quality_component(
        component_id="liquidity",
        authority_id="unresolved-pit-liquidity",
        overlap_group="liquidity",
        as_of=TRADE_AT,
        evidence_through=TRADE_AT,
        model_version="residual-v1",
        provenance="no independent PIT liquidity estimate preserved for this regression",
    )
    resilience = unresolved_decision_quality_component(
        component_id="resilience",
        authority_id="unresolved-pit-resilience",
        overlap_group="resilience",
        as_of=TRADE_AT,
        evidence_through=TRADE_AT,
        model_version="residual-v1",
        provenance="no sufficiently complete PIT roster-resilience estimate preserved for this regression",
    )
    return (current, future, liquidity, resilience)


def test_davis_robinson_side_is_center_score_robust_to_broad_weight_uncertainty() -> None:
    # Transaction 940755540299366400, 2023-03-12.
    # One side sent Gabe Davis + Brian Robinson and the other sent Kenny Pickett +
    # Odell Beckham Jr. Independent PIT research directions favor Davis/Robinson
    # for both current-season impact and future asset value. This fixture tests only
    # coefficient robustness; it is not an authoritative team-specific grade.
    favored = evaluate_weight_family_robustness(
        components=components(DirectionalEvidenceDirection.FAVORABLE),
        family=research_weight_family(),
    )
    unfavored = evaluate_weight_family_robustness(
        components=components(DirectionalEvidenceDirection.UNFAVORABLE),
        family=research_weight_family(),
    )

    assert favored.center_score_minimum == pytest.approx(64.50)
    assert favored.center_score_maximum == pytest.approx(71.25)
    assert unfavored.center_score_minimum == pytest.approx(28.75)
    assert unfavored.center_score_maximum == pytest.approx(35.50)

    # Exact channel weights remain unknown, but every admissible weighting keeps
    # the same center-score direction. This is the first real aligned robustness
    # control; unresolved channel *evidence ranges* remain visible separately.
    assert favored.center_score_minimum > 50
    assert unfavored.center_score_maximum < 50
    assert favored.score_lower < 50 < favored.score_upper
    assert unfavored.score_lower < 50 < unfavored.score_upper
