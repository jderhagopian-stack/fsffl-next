from datetime import UTC, datetime

from fsffl.opportunity import ActionAuthority, CandidateReason, EvidenceCompleteness
from fsffl.opportunity.trade_evaluation import candidate_from_trade_evaluation
from fsffl.team_utility import OwnerStrategicPosture
from fsffl.trade_decision import (
    AcceptanceEvidenceSet,
    AcceptanceModelStatus,
    NegotiationFeasibilityShape,
    SideDecisionShape,
    TradeAcceptanceView,
    TradeDecisionDisposition,
    TradeDisposition,
    TradeDispositionEvidence,
    TradeNegotiationFeasibility,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _feasibility(shape: NegotiationFeasibilityShape) -> TradeNegotiationFeasibility:
    return TradeNegotiationFeasibility(
        proposal_id="p1",
        focal_team_id="a",
        counterparty_team_id="b",
        shape=shape,
        counterparty_decision_shape=(
            SideDecisionShape.UNIFORM_LOSS
            if shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED
            else SideDecisionShape.MIXED
        ),
    )


def _unknown_acceptance() -> TradeAcceptanceView:
    evidence = AcceptanceEvidenceSet(
        proposal_id="p1",
        focal_team_id="a",
        counterparty_team_id="b",
        as_of=AS_OF,
    )
    return TradeAcceptanceView(
        proposal_id="p1",
        accepting_team_id="b",
        evidence=evidence,
        status=AcceptanceModelStatus.NOT_ESTIMATED,
    )


def _disposition(value: TradeDisposition) -> TradeDecisionDisposition:
    return TradeDecisionDisposition(
        proposal_id="p1",
        disposition=value,
        evidence=TradeDispositionEvidence(
            focal_team_id="a",
            counterparty_team_id="b",
            negotiation_shape=NegotiationFeasibilityShape.MIXED,
            owner_posture=OwnerStrategicPosture.DEFAULT_CALCULATED,
        ),
        material_assessment_model_version="material-v1",
        negotiation_model_version="negotiation-v1",
        strategic_context_model_version="strategy-v1",
    )


def test_unknown_acceptance_maps_to_market_test_only_when_other_evidence_complete() -> None:
    candidate = candidate_from_trade_evaluation(
        candidate_id="c1",
        focal_team_id="a",
        league_state_id="s1",
        as_of=AS_OF,
        feasibility=_feasibility(NegotiationFeasibilityShape.MIXED),
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        acceptance=_unknown_acceptance(),
    )
    assert candidate.action_authority == ActionAuthority.MARKET_TEST_ONLY
    assert CandidateReason.UNKNOWN_ACCEPTANCE in candidate.reasons
    assert CandidateReason.MATERIALITY_NOT_EVALUATED in candidate.reasons


def test_counterparty_dominated_remains_diagnostic_even_with_unknown_acceptance() -> None:
    candidate = candidate_from_trade_evaluation(
        candidate_id="c1",
        focal_team_id="a",
        league_state_id="s1",
        as_of=AS_OF,
        feasibility=_feasibility(NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED),
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        acceptance=_unknown_acceptance(),
    )
    assert candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY
    assert CandidateReason.COUNTERPARTY_DOMINATED in candidate.reasons


def test_incomplete_next5_feasibility_cannot_be_promoted() -> None:
    candidate = candidate_from_trade_evaluation(
        candidate_id="c1",
        focal_team_id="a",
        league_state_id="s1",
        as_of=AS_OF,
        feasibility=_feasibility(NegotiationFeasibilityShape.INCOMPLETE),
        evidence_completeness=EvidenceCompleteness.PARTIAL,
    )
    assert candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY
    assert CandidateReason.INCOMPLETE_EVIDENCE in candidate.reasons


def test_focal_decline_blocks_promotion_even_if_candidate_is_otherwise_complete() -> None:
    candidate = candidate_from_trade_evaluation(
        candidate_id="c1",
        focal_team_id="a",
        league_state_id="s1",
        as_of=AS_OF,
        feasibility=_feasibility(NegotiationFeasibilityShape.MIXED),
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        acceptance=_unknown_acceptance(),
        disposition=_disposition(TradeDisposition.DECLINE),
    )

    assert candidate.action_authority == ActionAuthority.DIAGNOSTIC_ONLY
    assert CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION in candidate.reasons
