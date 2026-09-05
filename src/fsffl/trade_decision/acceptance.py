from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel

from .models import BilateralTradeProposal


class AcceptanceModelStatus(StrEnum):
    NOT_ESTIMATED = "not_estimated"
    CHALLENGER = "challenger"
    PROVISIONAL_GOVERNED = "provisional_governed"
    AUTHORITATIVE = "authoritative"


class AcceptanceEvidenceKind(StrEnum):
    LEAGUE_TRANSACTION = "league_transaction"
    LEAGUE_REJECTION_OR_COUNTER = "league_rejection_or_counter"
    MARKET_TRANSACTION = "market_transaction"
    MARKET_LISTING_OR_PRICE = "market_listing_or_price"
    OWNER_BEHAVIOR = "owner_behavior"
    OTHER = "other"


class AcceptanceEvidenceItem(FrozenModel):
    evidence_id: str
    kind: AcceptanceEvidenceKind
    observed_at: datetime
    source: str
    source_version: str | None = None
    description: str = ""

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("acceptance evidence timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_evidence(self) -> "AcceptanceEvidenceItem":
        if not self.evidence_id.strip() or not self.source.strip():
            raise ValueError("acceptance evidence identifiers cannot be blank")
        return self


class AcceptanceEvidenceSet(FrozenModel):
    proposal_id: str
    focal_team_id: str
    counterparty_team_id: str
    as_of: datetime
    items: tuple[AcceptanceEvidenceItem, ...] = ()
    model_version: str = "next5-acceptance-evidence-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("acceptance evidence as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_set(self) -> "AcceptanceEvidenceSet":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("acceptance evidence identifiers cannot be blank")
        if self.focal_team_id == self.counterparty_team_id:
            raise ValueError("acceptance evidence requires distinct teams")
        ids = [item.evidence_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("acceptance evidence ids must be unique")
        if any(item.observed_at > self.as_of for item in self.items):
            raise ValueError("acceptance evidence cannot use future observations")
        return self


class AcceptanceProbabilityEstimate(FrozenModel):
    proposal_id: str
    accepting_team_id: str
    probability_mean: Annotated[float, Field(ge=0.0, le=1.0)]
    probability_p10: Annotated[float, Field(ge=0.0, le=1.0)]
    probability_p90: Annotated[float, Field(ge=0.0, le=1.0)]
    as_of: datetime
    evidence_count: Annotated[int, Field(ge=0)]
    status: AcceptanceModelStatus
    model_version: str
    evidence_model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("acceptance estimate as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_estimate(self) -> "AcceptanceProbabilityEstimate":
        if not (
            self.probability_p10 <= self.probability_mean <= self.probability_p90
        ):
            raise ValueError("acceptance probability interval must contain the mean")
        if not self.proposal_id.strip() or not self.model_version.strip() or not self.evidence_model_version.strip():
            raise ValueError("acceptance estimate identifiers cannot be blank")
        if self.status == AcceptanceModelStatus.NOT_ESTIMATED:
            raise ValueError("a probability estimate cannot have NOT_ESTIMATED status")
        return self


class TradeAcceptanceView(FrozenModel):
    """Acceptance/negotiation evidence kept separate from franchise utility.

    This contract intentionally permits `estimate=None`. Lack of a calibrated
    acceptance model is represented as missing authority, not as a made-up 50%
    prior or a recommendation.
    """

    proposal_id: str
    accepting_team_id: str
    evidence: AcceptanceEvidenceSet
    estimate: AcceptanceProbabilityEstimate | None = None
    status: AcceptanceModelStatus = AcceptanceModelStatus.NOT_ESTIMATED

    @model_validator(mode="after")
    def validate_view(self) -> "TradeAcceptanceView":
        if self.evidence.proposal_id != self.proposal_id:
            raise ValueError("acceptance evidence must match proposal")
        if self.evidence.counterparty_team_id != self.accepting_team_id:
            raise ValueError("acceptance view must describe evidence for accepting team")
        if self.estimate is None:
            if self.status != AcceptanceModelStatus.NOT_ESTIMATED:
                raise ValueError("acceptance status must be NOT_ESTIMATED without estimate")
        else:
            if self.estimate.proposal_id != self.proposal_id:
                raise ValueError("acceptance estimate must match proposal")
            if self.estimate.accepting_team_id != self.accepting_team_id:
                raise ValueError("acceptance estimate must match accepting team")
            if self.estimate.as_of > self.evidence.as_of:
                raise ValueError("acceptance estimate cannot postdate its evidence cutoff")
            if self.status != self.estimate.status:
                raise ValueError("acceptance view status must match estimate status")
        return self


def build_unestimated_acceptance_view(
    proposal: BilateralTradeProposal,
    *,
    accepting_team_id: str,
    evidence: AcceptanceEvidenceSet,
) -> TradeAcceptanceView:
    """Bind evidence without pretending an acceptance model exists yet."""

    team_ids = {proposal.side_a.team_id, proposal.side_b.team_id}
    if accepting_team_id not in team_ids:
        raise ValueError("accepting team must be a proposal side")
    if evidence.proposal_id != proposal.proposal_id:
        raise ValueError("acceptance evidence must match proposal")
    if evidence.counterparty_team_id != accepting_team_id:
        raise ValueError("evidence counterparty must be the accepting team")
    if evidence.focal_team_id not in team_ids - {accepting_team_id}:
        raise ValueError("evidence focal team must be the other proposal side")
    return TradeAcceptanceView(
        proposal_id=proposal.proposal_id,
        accepting_team_id=accepting_team_id,
        evidence=evidence,
    )
