from datetime import UTC, datetime

from fsffl.analytics.historical_grade_envelope import (
    translate_weight_robustness_to_grade_envelope,
)
from fsffl.analytics.historical_trade import GradeBand, GovernedGradePolicy
from fsffl.trade_decision.decision_quality import DecisionQualityComponent
from fsffl.trade_decision.decision_quality_weight_robustness import (
    DecisionQualityWeightBound,
    DecisionQualityWeightFamily,
    evaluate_weight_family_robustness,
)


AS_OF = datetime(2026, 7, 11, tzinfo=UTC)


def component(component_id: str, authority: str, overlap: str, lower: float, center: float, upper: float):
    return DecisionQualityComponent(
        component_id=component_id,
        authority_id=authority,
        overlap_group=overlap,
        score_lower=lower,
        score_center=center,
        score_upper=upper,
        confidence=0.8,
        evidence_through=AS_OF,
        model_version=f"{component_id}-v1",
        provenance="tests",
    )


def grade_policy() -> GovernedGradePolicy:
    return GovernedGradePolicy(
        policy_id="letters-v1",
        model_version="v1",
        provenance="tests:explicit-bands",
        bands=(
            GradeBand(minimum_score=0, letter="F"),
            GradeBand(minimum_score=60, letter="C"),
            GradeBand(minimum_score=75, letter="B"),
            GradeBand(minimum_score=90, letter="A"),
        ),
    )


def test_grade_envelope_reports_weight_and_component_uncertainty_without_inventing_center() -> None:
    components = (
        component("economic", "economic-authority", "economic", 70, 80, 90),
        component("competitive", "competitive-authority", "competitive", 60, 70, 80),
    )
    family = DecisionQualityWeightFamily(
        family_id="bounded-v1",
        model_version="v1",
        provenance="tests:bounded-family",
        bounds=(
            DecisionQualityWeightBound(component_id="economic", minimum_weight=0.4, maximum_weight=0.7),
            DecisionQualityWeightBound(component_id="competitive", minimum_weight=0.3, maximum_weight=0.6),
        ),
    )
    decision_envelope = evaluate_weight_family_robustness(components=components, family=family)
    grade_envelope = translate_weight_robustness_to_grade_envelope(
        envelope=decision_envelope,
        grade_policy=grade_policy(),
    )

    assert grade_envelope.center_score_lower <= grade_envelope.center_score_upper
    assert grade_envelope.score_lower <= grade_envelope.center_score_lower
    assert grade_envelope.center_score_upper <= grade_envelope.score_upper
    assert grade_envelope.center_possible_letters
    assert grade_envelope.possible_letters
    assert grade_envelope.letter_invariant == (len(grade_envelope.possible_letters) == 1)


def test_grade_envelope_can_prove_letter_invariance_across_all_allowed_weights() -> None:
    components = (
        component("economic", "economic-authority", "economic", 78, 82, 86),
        component("competitive", "competitive-authority", "competitive", 77, 81, 85),
    )
    family = DecisionQualityWeightFamily(
        family_id="bounded-v1",
        model_version="v1",
        provenance="tests:bounded-family",
        bounds=(
            DecisionQualityWeightBound(component_id="economic", minimum_weight=0.2, maximum_weight=0.8),
            DecisionQualityWeightBound(component_id="competitive", minimum_weight=0.2, maximum_weight=0.8),
        ),
    )
    decision_envelope = evaluate_weight_family_robustness(components=components, family=family)
    grade_envelope = translate_weight_robustness_to_grade_envelope(
        envelope=decision_envelope,
        grade_policy=grade_policy(),
    )

    assert grade_envelope.possible_letters == ("B",)
    assert grade_envelope.letter_invariant
