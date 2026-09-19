from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel


class OpportunityKind(StrEnum):
    TRADE = "trade"
    WAIVER = "waiver"
    SHOP = "shop"
    PRICE_DISCOVERY = "price_discovery"


class DiscoveryStatus(StrEnum):
    GENERATED = "generated"
    STRUCTURALLY_VALID = "structurally_valid"
    EVALUATED = "evaluated"
    PRUNED = "pruned"
    REJECTED = "rejected"


class ActionAuthority(StrEnum):
    NONE = "none"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    MARKET_TEST_ONLY = "market_test_only"
    ACTIONABLE = "actionable"


class EvidenceCompleteness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class CandidateReason(StrEnum):
    UNKNOWN_ACCEPTANCE = "unknown_acceptance"
    COUNTERPARTY_DOMINATED = "counterparty_dominated"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"
    INVALID_OWNERSHIP = "invalid_ownership"
    OUTSIDE_SEARCH_BOUNDS = "outside_search_bounds"
    ECONOMIC_SCALE_MISMATCH = "economic_scale_mismatch"
    MATERIALITY_NOT_EVALUATED = "materiality_not_evaluated"
    FOCAL_DISPOSITION_BLOCKS_ACTION = "focal_disposition_blocks_action"
    REDUNDANT = "redundant"
    DOMINATED = "dominated"


class OpportunityCandidate(FrozenModel):
    candidate_id: str
    kind: OpportunityKind
    focal_team_id: str
    league_state_id: str
    as_of: datetime
    discovery_status: DiscoveryStatus
    action_authority: ActionAuthority = ActionAuthority.NONE
    evidence_completeness: EvidenceCompleteness = EvidenceCompleteness.INSUFFICIENT
    reasons: tuple[CandidateReason, ...] = ()
    search_model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_candidate(self) -> "OpportunityCandidate":
        if any(not value.strip() for value in (
            self.candidate_id,
            self.focal_team_id,
            self.league_state_id,
            self.search_model_version,
        )):
            raise ValueError("candidate identifiers cannot be blank")
        if self.action_authority == ActionAuthority.ACTIONABLE:
            if self.discovery_status != DiscoveryStatus.EVALUATED:
                raise ValueError("actionable candidates must be evaluated")
            if self.evidence_completeness != EvidenceCompleteness.COMPLETE:
                raise ValueError("actionable candidates require complete evidence")
            blocking = {
                CandidateReason.UNKNOWN_ACCEPTANCE,
                CandidateReason.COUNTERPARTY_DOMINATED,
                CandidateReason.INCOMPLETE_EVIDENCE,
                CandidateReason.INVALID_OWNERSHIP,
                CandidateReason.ECONOMIC_SCALE_MISMATCH,
                CandidateReason.MATERIALITY_NOT_EVALUATED,
                CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION,
            }
            if blocking.intersection(self.reasons):
                raise ValueError("blocking reasons cannot coexist with actionable authority")
        if self.discovery_status in {DiscoveryStatus.PRUNED, DiscoveryStatus.REJECTED}:
            if self.action_authority == ActionAuthority.ACTIONABLE:
                raise ValueError("pruned or rejected candidates cannot be actionable")
        return self


def derive_action_authority(
    *,
    discovery_status: DiscoveryStatus,
    evidence_completeness: EvidenceCompleteness,
    reasons: tuple[CandidateReason, ...] = (),
    allow_market_test_when_acceptance_unknown: bool = True,
) -> ActionAuthority:
    """Conservatively derive promotion authority from explicit candidate state.

    Search discovery is intentionally broader than action authority. Unknown
    acceptance or missing materiality may permit a market-test candidate but never
    automatic action. Counterparty domination, adverse focal disposition,
    structural invalidity, and incomplete evidence remain diagnostic-only at most.
    """

    if discovery_status in {DiscoveryStatus.PRUNED, DiscoveryStatus.REJECTED}:
        return ActionAuthority.NONE

    reason_set = set(reasons)
    hard_blocks = {
        CandidateReason.COUNTERPARTY_DOMINATED,
        CandidateReason.INCOMPLETE_EVIDENCE,
        CandidateReason.INVALID_OWNERSHIP,
        CandidateReason.ECONOMIC_SCALE_MISMATCH,
        CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION,
    }
    if reason_set.intersection(hard_blocks):
        return ActionAuthority.DIAGNOSTIC_ONLY

    soft_market_test_blocks = {
        CandidateReason.UNKNOWN_ACCEPTANCE,
        CandidateReason.MATERIALITY_NOT_EVALUATED,
    }
    if reason_set.intersection(soft_market_test_blocks):
        return (
            ActionAuthority.MARKET_TEST_ONLY
            if allow_market_test_when_acceptance_unknown
            and discovery_status == DiscoveryStatus.EVALUATED
            and evidence_completeness == EvidenceCompleteness.COMPLETE
            else ActionAuthority.DIAGNOSTIC_ONLY
        )

    if (
        discovery_status == DiscoveryStatus.EVALUATED
        and evidence_completeness == EvidenceCompleteness.COMPLETE
    ):
        return ActionAuthority.ACTIONABLE

    if discovery_status in {DiscoveryStatus.GENERATED, DiscoveryStatus.STRUCTURALLY_VALID}:
        return ActionAuthority.DIAGNOSTIC_ONLY

    return ActionAuthority.NONE
