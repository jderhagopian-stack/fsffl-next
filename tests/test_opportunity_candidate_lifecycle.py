from datetime import UTC, datetime

import pytest

from fsffl.opportunity import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
    derive_action_authority,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def test_unknown_acceptance_never_becomes_automatic_action() -> None:
    authority = derive_action_authority(
        discovery_status=DiscoveryStatus.EVALUATED,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reasons=(CandidateReason.UNKNOWN_ACCEPTANCE,),
    )
    assert authority == ActionAuthority.MARKET_TEST_ONLY


def test_counterparty_dominated_candidate_is_diagnostic_only() -> None:
    authority = derive_action_authority(
        discovery_status=DiscoveryStatus.EVALUATED,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
        reasons=(CandidateReason.COUNTERPARTY_DOMINATED,),
    )
    assert authority == ActionAuthority.DIAGNOSTIC_ONLY


def test_incomplete_evidence_is_diagnostic_only() -> None:
    authority = derive_action_authority(
        discovery_status=DiscoveryStatus.EVALUATED,
        evidence_completeness=EvidenceCompleteness.PARTIAL,
        reasons=(CandidateReason.INCOMPLETE_EVIDENCE,),
    )
    assert authority == ActionAuthority.DIAGNOSTIC_ONLY


def test_complete_evaluated_unblocked_candidate_can_be_actionable() -> None:
    authority = derive_action_authority(
        discovery_status=DiscoveryStatus.EVALUATED,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
    )
    assert authority == ActionAuthority.ACTIONABLE


def test_generated_candidate_is_not_actionable_before_evaluation() -> None:
    authority = derive_action_authority(
        discovery_status=DiscoveryStatus.GENERATED,
        evidence_completeness=EvidenceCompleteness.COMPLETE,
    )
    assert authority == ActionAuthority.DIAGNOSTIC_ONLY


def test_candidate_contract_rejects_actionable_with_unknown_acceptance() -> None:
    with pytest.raises(ValueError, match="blocking reasons"):
        OpportunityCandidate(
            candidate_id="c1",
            kind=OpportunityKind.TRADE,
            focal_team_id="a",
            league_state_id="state-1",
            as_of=AS_OF,
            discovery_status=DiscoveryStatus.EVALUATED,
            action_authority=ActionAuthority.ACTIONABLE,
            evidence_completeness=EvidenceCompleteness.COMPLETE,
            reasons=(CandidateReason.UNKNOWN_ACCEPTANCE,),
            search_model_version="next6-test",
        )


def test_candidate_contract_rejects_actionable_partial_evidence() -> None:
    with pytest.raises(ValueError, match="complete evidence"):
        OpportunityCandidate(
            candidate_id="c1",
            kind=OpportunityKind.TRADE,
            focal_team_id="a",
            league_state_id="state-1",
            as_of=AS_OF,
            discovery_status=DiscoveryStatus.EVALUATED,
            action_authority=ActionAuthority.ACTIONABLE,
            evidence_completeness=EvidenceCompleteness.PARTIAL,
            search_model_version="next6-test",
        )
