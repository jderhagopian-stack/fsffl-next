from datetime import UTC, datetime

from fsffl.analytics.historical_trade import EvidenceCompleteness
from fsffl.runtime.historical_decision_evidence import build_point_in_time_decision_evidence
from fsffl.trade_decision.decision_quality import DecisionQualityPolicyAuthority, DecisionQualityScore


def test_runtime_bridge_copies_decision_quality_without_recalculation() -> None:
    as_of = datetime(2025, 8, 15, tzinfo=UTC)
    score = DecisionQualityScore(
        transaction_id="trade",
        team_id="A",
        as_of=as_of,
        score_lower=55,
        score_center=70,
        score_upper=82,
        confidence=0.8,
        component_ids=("economic", "competitive"),
        component_model_versions=("economic-v1", "competitive-v1"),
        policy_id="dq-policy",
        policy_version="dq-v1",
        policy_authority=DecisionQualityPolicyAuthority.BOUNDED_PRIOR,
    )
    evidence = EvidenceCompleteness(
        required_items=("state", "forecast", "value", "decision"),
        available_items=("state", "forecast", "value", "decision"),
    )

    result = build_point_in_time_decision_evidence(
        score,
        evidence=evidence,
        decision_disposition="accept",
        package_economics_delta=123.0,
    )

    assert result.transaction_id == "trade"
    assert result.team_id == "A"
    assert result.decision_quality_score == 70
    assert result.decision_quality_score_lower == 55
    assert result.decision_quality_score_upper == 82
    assert result.decision_quality_confidence == 0.8
    assert result.decision_quality_policy_id == "dq-policy"
    assert result.decision_quality_policy_version == "dq-v1"
    assert result.decision_quality_policy_authority == "bounded_prior"
    assert result.decision_disposition == "accept"
    assert result.package_economics_delta == 123.0
