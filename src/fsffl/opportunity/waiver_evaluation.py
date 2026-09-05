from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility import TeamScenarioDelta
from fsffl.trade_decision import (
    CompetitiveMaterialityPolicy,
    EconomicMaterialityPolicy,
    MaterialityDirection,
    classify_negative_delta,
    classify_positive_delta,
)
from fsffl.value.models import ValueScale

from .models import (
    ActionAuthority,
    CandidateReason,
    DiscoveryStatus,
    EvidenceCompleteness,
    OpportunityCandidate,
    OpportunityKind,
)


class WaiverOpportunityDisposition(StrEnum):
    SUPPORT = "support"
    DECLINE = "decline"
    REVIEW = "review"
    NO_CLEAR_ADVANTAGE = "no_clear_advantage"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class WaiverMaterialAssessment(FrozenModel):
    team_id: str
    expected_wins: MaterialityDirection
    playoff_probability: MaterialityDirection
    first_place_probability: MaterialityDirection
    largest_single_player_lineup_drop: MaterialityDirection
    asset_portfolio_mean: MaterialityDirection
    disposition: WaiverOpportunityDisposition
    competitive_policy_version: str
    economic_policy_version: str | None = None
    model_version: str = "next6-waiver-material-v1"

    @model_validator(mode="after")
    def validate_assessment(self) -> "WaiverMaterialAssessment":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("waiver assessment identifiers cannot be blank")
        if not self.competitive_policy_version.strip():
            raise ValueError("waiver assessment must record competitive policy version")
        return self


def assess_waiver_materiality(
    delta: TeamScenarioDelta,
    *,
    as_of,
    competitive_policy: CompetitiveMaterialityPolicy,
    economic_policy: EconomicMaterialityPolicy | None = None,
    economic_scale: ValueScale | None = None,
    model_version: str = "next6-waiver-material-v1",
) -> WaiverMaterialAssessment:
    """Interpret one add/drop scenario with explicit governed materiality only.

    NEXT-6 does not choose thresholds. It consumes the same versioned materiality
    contracts used by Trade Decision. Missing economic policy/scale remains
    unavailable rather than being silently treated as neutral.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if competitive_policy.evidence_through > as_of:
        raise ValueError("competitive materiality policy cannot use future evidence")
    if economic_policy is not None:
        if economic_policy.evidence_through > as_of:
            raise ValueError("economic materiality policy cannot use future evidence")
        if economic_scale is None:
            raise ValueError("economic scale is required when economic policy is supplied")
        if economic_policy.scale != economic_scale:
            raise ValueError("economic materiality policy must match scenario value scale")

    competitive = delta.competitive
    resilience = delta.resilience
    wins = classify_positive_delta(
        competitive.expected_wins if competitive else None,
        absolute_threshold=competitive_policy.expected_wins_abs,
    )
    playoff = classify_positive_delta(
        competitive.playoff_probability if competitive else None,
        absolute_threshold=competitive_policy.playoff_probability_abs,
    )
    first = classify_positive_delta(
        competitive.first_place_probability if competitive else None,
        absolute_threshold=competitive_policy.first_place_probability_abs,
    )
    lineup_drop = classify_negative_delta(
        resilience.largest_single_player_lineup_drop if resilience else None,
        absolute_threshold=competitive_policy.lineup_drop_abs,
    )
    if economic_policy is None:
        economics = MaterialityDirection.UNAVAILABLE
    else:
        economics = classify_positive_delta(
            delta.asset_portfolio.mean_value if delta.asset_portfolio else None,
            absolute_threshold=economic_policy.mean_value_abs,
        )

    directions = (wins, playoff, first, lineup_drop, economics)
    available = tuple(direction for direction in directions if direction != MaterialityDirection.UNAVAILABLE)
    if not available or MaterialityDirection.UNAVAILABLE in directions:
        disposition = WaiverOpportunityDisposition.INSUFFICIENT_EVIDENCE
    else:
        gains = MaterialityDirection.MATERIAL_GAIN in available
        losses = MaterialityDirection.MATERIAL_LOSS in available
        if gains and losses:
            disposition = WaiverOpportunityDisposition.REVIEW
        elif losses:
            disposition = WaiverOpportunityDisposition.DECLINE
        elif gains:
            disposition = WaiverOpportunityDisposition.SUPPORT
        else:
            disposition = WaiverOpportunityDisposition.NO_CLEAR_ADVANTAGE

    return WaiverMaterialAssessment(
        team_id=delta.team_id,
        expected_wins=wins,
        playoff_probability=playoff,
        first_place_probability=first,
        largest_single_player_lineup_drop=lineup_drop,
        asset_portfolio_mean=economics,
        disposition=disposition,
        competitive_policy_version=competitive_policy.model_version,
        economic_policy_version=economic_policy.model_version if economic_policy else None,
        model_version=model_version,
    )


def candidate_from_waiver_evaluation(
    *,
    candidate_id: str,
    focal_team_id: str,
    league_state_id: str,
    as_of,
    evidence_completeness: EvidenceCompleteness,
    assessment: WaiverMaterialAssessment | None,
    search_model_version: str = "next6-waiver-evaluation-v1",
) -> OpportunityCandidate:
    """Map explicit waiver materiality to candidate action authority."""

    reasons: list[CandidateReason] = []
    if evidence_completeness != EvidenceCompleteness.COMPLETE:
        reasons.append(CandidateReason.INCOMPLETE_EVIDENCE)
    if assessment is None:
        reasons.append(CandidateReason.MATERIALITY_NOT_EVALUATED)
    else:
        if assessment.team_id != focal_team_id:
            raise ValueError("waiver assessment must describe focal team")
        if assessment.disposition != WaiverOpportunityDisposition.SUPPORT:
            reasons.append(CandidateReason.FOCAL_DISPOSITION_BLOCKS_ACTION)

    if evidence_completeness != EvidenceCompleteness.COMPLETE:
        authority = ActionAuthority.DIAGNOSTIC_ONLY
    elif assessment is None:
        authority = ActionAuthority.DIAGNOSTIC_ONLY
    elif assessment.disposition == WaiverOpportunityDisposition.SUPPORT:
        authority = ActionAuthority.ACTIONABLE
    else:
        authority = ActionAuthority.DIAGNOSTIC_ONLY

    return OpportunityCandidate(
        candidate_id=candidate_id,
        kind=OpportunityKind.WAIVER,
        focal_team_id=focal_team_id,
        league_state_id=league_state_id,
        as_of=as_of,
        discovery_status=DiscoveryStatus.EVALUATED,
        action_authority=authority,
        evidence_completeness=evidence_completeness,
        reasons=tuple(reasons),
        search_model_version=search_model_version,
    )
