from __future__ import annotations

from fsffl.trade_decision import (
    AcceptanceModelStatus,
    NegotiationFeasibilityShape,
    TradeAcceptanceView,
    TradeDecisionDisposition,
    TradeDisposition,
    TradeNegotiationFeasibility,
)

from .models import (
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
    disposition: TradeDecisionDisposition | None,
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

    if disposition is None:
        reasons.append(CandidateReason.MATERIALITY_NOT_EVALUATED)
    elif disposition.disposition != TradeDisposition.SUPPORT:
        reasons.append(CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION)

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
    disposition: TradeDecisionDisposition | None = None,
    search_model_version: str = "next6-trade-evaluation-v1",
) -> OpportunityCandidate:
    """Convert authoritative NEXT-5 outputs into NEXT-6 lifecycle authority.

    Search cannot infer that a realistic deal is desirable for the focal team.
    Actionable promotion therefore requires a NEXT-5 SUPPORT disposition in addition
    to complete evidence and non-blocking acceptance/feasibility. If materiality has
    not been evaluated, the candidate may remain visible for market testing but
    cannot become actionable.
    """

    if feasibility.focal_team_id != focal_team_id:
        raise ValueError("feasibility focal team must match opportunity focal team")
    if acceptance is not None:
        if acceptance.proposal_id != feasibility.proposal_id:
            raise ValueError("acceptance must match feasibility proposal")
        if acceptance.accepting_team_id != feasibility.counterparty_team_id:
            raise ValueError("acceptance must describe feasibility counterparty")
    if disposition is not None:
        if disposition.proposal_id != feasibility.proposal_id:
            raise ValueError("disposition must match feasibility proposal")
        if disposition.evidence.focal_team_id != focal_team_id:
            raise ValueError("disposition must describe opportunity focal team")
        if disposition.evidence.counterparty_team_id != feasibility.counterparty_team_id:
            raise ValueError("disposition counterparty must match feasibility counterparty")

    reasons = _candidate_reasons(
        feasibility,
        evidence_completeness=evidence_completeness,
        acceptance=acceptance,
        disposition=disposition,
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
