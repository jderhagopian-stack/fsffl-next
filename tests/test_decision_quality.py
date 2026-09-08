from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.decision_quality import (
    DecisionQualityComponent,
    DecisionQualityPolicy,
    DecisionQualityPolicyAuthority,
    DecisionQualityWeight,
    score_historical_decision_quality,
)


AS_OF = datetime(2024, 5, 1, tzinfo=UTC)


def component(
    component_id: str,
    *,
    authority_id: str,
    overlap_group: str,
    lower: float,
    center: float,
    upper: float,
    confidence: float = 0.8,
) -> DecisionQualityComponent:
    return DecisionQualityComponent(
        component_id=component_id,
        authority_id=authority_id,
        overlap_group=overlap_group,
        score_lower=lower,
        score_center=center,
        score_upper=upper,
        confidence=confidence,
        evidence_through=AS_OF,
        model_version=f"{component_id}-v1",
        provenance=f"{component_id} normalized PIT evidence",
    )


def policy(*weights: tuple[str, float]) -> DecisionQualityPolicy:
    return DecisionQualityPolicy(
        policy_id="decision-quality-research",
        model_version="dq-policy-v1",
        provenance="explicit research policy; no hidden defaults",
        evidence_through=AS_OF,
        weights=tuple(DecisionQualityWeight(component_id=name, weight=weight) for name, weight in weights),
        authority=DecisionQualityPolicyAuthority.BOUNDED_PRIOR,
    )


def test_explicit_non_overlapping_policy_produces_score_interval():
    result = score_historical_decision_quality(
        transaction_id="trade",
        team_id="A",
        as_of=AS_OF,
        components=(
            component("economic", authority_id="decision-economic", overlap_group="economic", lower=60, center=70, upper=80),
            component("competitive", authority_id="team-utility", overlap_group="competitive", lower=40, center=50, upper=60, confidence=0.6),
        ),
        policy=policy(("economic", 0.6), ("competitive", 0.4)),
    )
    assert result.score_lower == pytest.approx(52)
    assert result.score_center == pytest.approx(62)
    assert result.score_upper == pytest.approx(72)
    assert result.confidence == pytest.approx(0.72)
    assert result.policy_authority == DecisionQualityPolicyAuthority.BOUNDED_PRIOR


def test_policy_has_no_default_weights_and_requires_sum_to_one():
    with pytest.raises(ValueError, match="requires explicit"):
        policy()
    with pytest.raises(ValueError, match="sum to 1"):
        policy(("economic", 0.6), ("competitive", 0.3))


def test_missing_required_component_fails_closed():
    with pytest.raises(ValueError, match="components are missing"):
        score_historical_decision_quality(
            transaction_id="trade",
            team_id="A",
            as_of=AS_OF,
            components=(component("economic", authority_id="economic", overlap_group="economic", lower=60, center=70, upper=80),),
            policy=policy(("economic", 0.5), ("competitive", 0.5)),
        )


def test_same_authority_cannot_be_counted_twice():
    components = (
        component("a", authority_id="shared-utility", overlap_group="a", lower=60, center=70, upper=80),
        component("b", authority_id="shared-utility", overlap_group="b", lower=50, center=60, upper=70),
    )
    with pytest.raises(ValueError, match="same authority twice"):
        score_historical_decision_quality(
            transaction_id="trade", team_id="A", as_of=AS_OF,
            components=components, policy=policy(("a", 0.5), ("b", 0.5)),
        )


def test_overlapping_components_cannot_be_double_counted_even_from_different_authorities():
    components = (
        component("a", authority_id="value", overlap_group="asset-economics", lower=60, center=70, upper=80),
        component("b", authority_id="team-utility", overlap_group="asset-economics", lower=50, center=60, upper=70),
    )
    with pytest.raises(ValueError, match="overlapping/double-counted"):
        score_historical_decision_quality(
            transaction_id="trade", team_id="A", as_of=AS_OF,
            components=components, policy=policy(("a", 0.5), ("b", 0.5)),
        )


def test_future_component_or_policy_cannot_leak_into_historical_score():
    future = datetime(2024, 5, 2, tzinfo=UTC)
    future_component = component("economic", authority_id="economic", overlap_group="economic", lower=60, center=70, upper=80).model_copy(update={"evidence_through": future})
    with pytest.raises(ValueError, match="component uses evidence unavailable"):
        score_historical_decision_quality(
            transaction_id="trade", team_id="A", as_of=AS_OF,
            components=(future_component,), policy=policy(("economic", 1.0)),
        )
    future_policy = policy(("economic", 1.0)).model_copy(update={"evidence_through": future})
    with pytest.raises(ValueError, match="policy uses evidence unavailable"):
        score_historical_decision_quality(
            transaction_id="trade", team_id="A", as_of=AS_OF,
            components=(component("economic", authority_id="economic", overlap_group="economic", lower=60, center=70, upper=80),),
            policy=future_policy,
        )
