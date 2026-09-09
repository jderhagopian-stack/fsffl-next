from __future__ import annotations

from datetime import datetime

from pydantic import field_validator, model_validator

from fsffl.behavioral.trade_shape_context import BehavioralTradeShape, OwnerTradeShapePreferenceProfile
from fsffl.state.models import FrozenModel

from .models import BilateralTradeProposal


class OwnerTradeShapeProposalFit(FrozenModel):
    """Non-probabilistic Behavioral evidence about a proposal's package shape.

    This is deliberately not an acceptance probability or value adjustment. It
    records the proposed shape from one team's perspective and the owner's
    context-controlled residual tendency toward that shape.
    """

    proposal_id: str
    accepting_team_id: str
    owner_id: str
    proposed_shape: BehavioralTradeShape
    observed_historical_share: float | None = None
    context_expected_share: float | None = None
    residual_share: float | None = None
    confidence: float
    historical_coverage_rate: float
    status: str
    source_profile_as_of: datetime
    source_profile_model_version: str
    model_version: str = "owner-trade-shape-proposal-fit-v1"

    @field_validator("source_profile_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("owner trade-shape proposal fit timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_fit(self) -> "OwnerTradeShapeProposalFit":
        if any(not value.strip() for value in (self.proposal_id, self.accepting_team_id, self.owner_id, self.source_profile_model_version, self.model_version)):
            raise ValueError("owner trade-shape proposal fit metadata cannot be blank")
        if not 0.0 <= self.confidence <= 1.0 or not 0.0 <= self.historical_coverage_rate <= 1.0:
            raise ValueError("owner trade-shape proposal fit confidence/coverage must be between zero and one")
        metrics = (self.observed_historical_share, self.context_expected_share, self.residual_share)
        if self.status == "estimated":
            if any(value is None for value in metrics):
                raise ValueError("estimated owner trade-shape fit requires complete metrics")
        elif self.status == "unavailable":
            if any(value is not None for value in metrics):
                raise ValueError("unavailable owner trade-shape fit cannot claim metrics")
        else:
            raise ValueError("owner trade-shape proposal fit status is invalid")
        return self


def _shape_from_team_perspective(proposal: BilateralTradeProposal, team_id: str) -> BehavioralTradeShape:
    if proposal.side_a.team_id == team_id:
        sent = len(proposal.side_a.sends)
        received = len(proposal.side_b.sends)
    elif proposal.side_b.team_id == team_id:
        sent = len(proposal.side_b.sends)
        received = len(proposal.side_a.sends)
    else:
        raise ValueError("trade-shape fit team must be one side of the proposal")
    if sent > received:
        return BehavioralTradeShape.CONSOLIDATION
    if received > sent:
        return BehavioralTradeShape.DIVERSIFICATION
    return BehavioralTradeShape.BALANCED


def assess_owner_trade_shape_proposal_fit(
    proposal: BilateralTradeProposal,
    *,
    accepting_team_id: str,
    owner_id: str,
    profile: OwnerTradeShapePreferenceProfile,
) -> OwnerTradeShapeProposalFit:
    """Bind context-controlled shape history to the current proposal without scoring it."""
    if not owner_id.strip():
        raise ValueError("owner trade-shape proposal fit owner_id cannot be blank")
    if profile.owner_id != owner_id:
        raise ValueError("owner trade-shape profile owner must match requested owner")
    if profile.as_of > proposal.as_of:
        raise ValueError("owner trade-shape profile cannot use evidence after proposal cutoff")
    proposed_shape = _shape_from_team_perspective(proposal, accepting_team_id)
    row = profile.shape(proposed_shape)
    if row.status != "estimated" or row.shrunk_residual_share is None:
        return OwnerTradeShapeProposalFit(
            proposal_id=proposal.proposal_id,
            accepting_team_id=accepting_team_id,
            owner_id=owner_id,
            proposed_shape=proposed_shape,
            confidence=0.0,
            historical_coverage_rate=profile.coverage_rate,
            status="unavailable",
            source_profile_as_of=profile.as_of,
            source_profile_model_version=profile.model_version,
        )
    return OwnerTradeShapeProposalFit(
        proposal_id=proposal.proposal_id,
        accepting_team_id=accepting_team_id,
        owner_id=owner_id,
        proposed_shape=proposed_shape,
        observed_historical_share=row.observed_share,
        context_expected_share=row.context_expected_share,
        residual_share=row.shrunk_residual_share,
        confidence=profile.confidence,
        historical_coverage_rate=profile.coverage_rate,
        status="estimated",
        source_profile_as_of=profile.as_of,
        source_profile_model_version=profile.model_version,
    )
