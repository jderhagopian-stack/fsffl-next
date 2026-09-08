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


TRADE_AT = datetime(2022, 8, 9, 15, 51, 17, tzinfo=UTC)


def directional_policy(component_id: str, authority_id: str) -> DirectionalEvidenceNormalizationPolicy:
    return DirectionalEvidenceNormalizationPolicy(
        component_id=component_id,
        authority_id=authority_id,
        overlap_group=component_id,
        unfavorable=DirectionalEvidenceScoreRange(score_lower=0, score_center=25, score_upper=50),
        neutral=DirectionalEvidenceScoreRange(score_lower=40, score_center=50, score_upper=60),
        favorable=DirectionalEvidenceScoreRange(score_lower=50, score_center=75, score_upper=100),
        evidence_through=datetime(2022, 6, 30, tzinfo=UTC),
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


def components(*, current: DirectionalEvidenceDirection, future: DirectionalEvidenceDirection):
    current_component = normalize_directional_decision_quality_component(
        direction=current,
        as_of=TRADE_AT,
        evidence_through=datetime(2022, 6, 30, tzinfo=UTC),
        confidence=0.65,
        policy=directional_policy("current_impact", "pit-2022-projection-evidence"),
    )
    future_component = normalize_directional_decision_quality_component(
        direction=future,
        as_of=TRADE_AT,
        evidence_through=datetime(2022, 6, 30, tzinfo=UTC),
        confidence=0.70,
        policy=directional_policy("future_asset_value", "pit-2022-dynasty-market-evidence"),
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
        provenance="historical roster context is approximate, so no directional resilience claim is made",
    )
    return (current_component, future_component, liquidity, resilience)


def test_kirk_for_freiermuth_trade_remains_weight_sensitive_under_conservative_pit_evidence() -> None:
    # Transaction 862758969872125952, 2022-08-09.
    # Bodini received Christian Kirk: contemporaneous 2022 projection direction favors Kirk,
    # while contemporaneous dynasty-market direction favors Pat Freiermuth.
    bodini = evaluate_weight_family_robustness(
        components=components(
            current=DirectionalEvidenceDirection.FAVORABLE,
            future=DirectionalEvidenceDirection.UNFAVORABLE,
        ),
        family=research_weight_family(),
    )
    shish = evaluate_weight_family_robustness(
        components=components(
            current=DirectionalEvidenceDirection.UNFAVORABLE,
            future=DirectionalEvidenceDirection.FAVORABLE,
        ),
        family=research_weight_family(),
    )

    assert bodini.center_score_minimum == pytest.approx(34.25)
    assert bodini.center_score_maximum == pytest.approx(60.50)
    assert bodini.score_lower == pytest.approx(2.50)
    assert bodini.score_upper == pytest.approx(91.00)

    assert shish.center_score_minimum == pytest.approx(39.50)
    assert shish.center_score_maximum == pytest.approx(65.75)
    assert shish.score_lower == pytest.approx(9.00)
    assert shish.score_upper == pytest.approx(97.50)

    # The real-world regression must remain explicitly sensitive until stronger
    # PIT channel evidence or tighter empirically justified weight bounds exist.
    assert bodini.center_score_minimum < 50 < bodini.center_score_maximum
    assert shish.center_score_minimum < 50 < shish.center_score_maximum
