from __future__ import annotations

from fsffl.analytics.historical_trade import EvidenceCompleteness, PointInTimeDecisionEvidence
from fsffl.trade_decision.decision_quality import DecisionQualityScore


def build_point_in_time_decision_evidence(
    score: DecisionQualityScore,
    *,
    evidence: EvidenceCompleteness,
    decision_disposition: str | None = None,
    value_exchanged: float | None = None,
    team_utility_delta: float | None = None,
    projected_lineup_delta: float | None = None,
    replacement_value_delta: float | None = None,
    pick_value_delta: float | None = None,
    package_economics_delta: float | None = None,
    uncertainty: float | None = None,
    evidence_notes: tuple[str, ...] = (),
) -> PointInTimeDecisionEvidence:
    """Copy authoritative Decision quality into the historical grading contract.

    Runtime coordinates the cross-layer handoff. No score, confidence, policy
    identity, or grade is recalculated here; Analytics remains presentation of the
    Decision-owned result rather than a competing source of model truth.
    """

    return PointInTimeDecisionEvidence(
        transaction_id=score.transaction_id,
        team_id=score.team_id,
        as_of=score.as_of,
        decision_model_version=score.model_version,
        decision_quality_score=score.score_center,
        decision_quality_score_lower=score.score_lower,
        decision_quality_score_upper=score.score_upper,
        decision_quality_confidence=score.confidence,
        decision_quality_policy_id=score.policy_id,
        decision_quality_policy_version=score.policy_version,
        decision_quality_policy_authority=score.policy_authority.value,
        decision_disposition=decision_disposition,
        value_exchanged=value_exchanged,
        team_utility_delta=team_utility_delta,
        projected_lineup_delta=projected_lineup_delta,
        replacement_value_delta=replacement_value_delta,
        pick_value_delta=pick_value_delta,
        package_economics_delta=package_economics_delta,
        uncertainty=uncertainty,
        evidence=evidence,
        evidence_notes=evidence_notes,
    )
