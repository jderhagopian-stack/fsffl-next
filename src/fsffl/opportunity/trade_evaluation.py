from __future__ import annotations

from fsffl.trade_decision import (
    AcceptanceModelStatus,
    NegotiationFeasibilityShape,
    TradeAcceptanceView,
    TradeNegotiationFeasibility,
)

from .models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
    derive_action_authority,
)


def _candidate_reasons(
    feasibility: TradeNegotiationFeasibility,
    *,
    evidence_completeness: EvidenceCompleteness,
    acceptance: TradeAcceptanceView | None,
) -> tuple[CandidateReason, ...]:
    reasons: list[CandidateReason] = []

    if evidence_completeness != EvidenceCompleteness.COMPLETE:
        reasons.append(CandidateReason.INCOMPLETE_EVIDENCE)

    if feasibility.shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED:
        reasons.append(CandidateReason.COUNTERPARTY_DOMINATED)
    elif feasibility.shape == NegotiationFeasibilityShape.INCOMPLETE:
        reasons.append(CandidateReason.INCOMPLETE_EVIDENCE)

    if acceptance is None or acceptance.status == AcceptanceModelStatus.NOT_ESTIMATED:
        reasons.append(CandidateReason.UNKNOWN_ACCEPTANCE)

    return tuple(dict.fromkeys(reasons))


def candidate_from_trade_evaluation(
    *,
    candidate_id: str,
    focal_team_id: str,
    league_state_id: str,
    as_of,
    feasibility: TradeNegotiationFeasibility,
    evidence_completeness: EvidenceCompleteness,
    acceptance: TradeAcceptanceView | None = None,
    search_model_version: str = "next6-trade-evaluation-v1",
) -> OpportunityCandidate:
    """Convert authoritative NEXT-5 outputs into NEXT-6 lifecycle authority.

    This function does not reinterpret team utility, economics, or acceptance.
    It translates explicit NEXT-5 uncertainty/feasibility states into search-level
    discovery and action authority so theoretical candidates remain visible without
    becoming recommendations by accident.
    """

    if feasibility.focal_team_id != focal_team_id:
        raise ValueError("feasibility focal team must match opportunity focal team")
    if acceptance is not None:
        if acceptance.proposal_id != feasibility.proposal_id:
            raise ValueError("acceptance must match feasibility proposal")
        if acceptance.accepting_team_id != feasibility.counterparty_team_id:
            raise ValueError("acceptance must describe feasibility counterparty")

    reasons = _candidate_reasons(
        feasibility,
        evidence_completeness=evidence_completeness,
        acceptance=acceptance,
    )
    discovery_status = DiscoveryStatus.EVALUATED
    authority = derive_action_authority(
        discovery_status=discovery_status,
        evidence_completeness=evidence_completeness,
        reasons=reasons,
    )
    return OpportunityCandidate(
        candidate_id=candidate_id,
        kind=OpportunityKind.TRADE,
        focal_team_id=focal_team_id,
        league_state_id=league_state_id,
        as_of=as_of,
        discovery_status=discovery_status,
        action_authority=authority,
        evidence_completeness=evidence_completeness,
        reasons=reasons,
        search_model_version=search_model_version,
    )
