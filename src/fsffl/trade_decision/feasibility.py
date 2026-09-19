from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel

from .acceptance import TradeAcceptanceView
from .decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    SideDecisionShape,
    SideDirectionalAssessment,
)


class NegotiationFeasibilityShape(StrEnum):
    MUTUAL_GAIN_CANDIDATE = "mutual_gain_candidate"
    COUNTERPARTY_DOMINATED = "counterparty_dominated"
    MIXED = "mixed"
    INCOMPLETE = "incomplete"
    NEUTRAL = "neutral"


class TradeNegotiationFeasibility(FrozenModel):
    """Descriptive feasibility shape, not an acceptance probability or recommendation."""

    proposal_id: str
    focal_team_id: str
    counterparty_team_id: str
    shape: NegotiationFeasibilityShape
    counterparty_decision_shape: SideDecisionShape
    acceptance: TradeAcceptanceView | None = None
    model_version: str = "next5-negotiation-feasibility-v1"

    @model_validator(mode="after")
    def validate_feasibility(self) -> "TradeNegotiationFeasibility":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("negotiation feasibility identifiers cannot be blank")
        if self.focal_team_id == self.counterparty_team_id:
            raise ValueError("negotiation feasibility requires distinct teams")
        if self.acceptance is not None:
            if self.acceptance.proposal_id != self.proposal_id:
                raise ValueError("acceptance evidence must match feasibility proposal")
            if self.acceptance.accepting_team_id != self.counterparty_team_id:
                raise ValueError("acceptance evidence must describe the counterparty")
        return self


def _sides_for_focal(
    decision: BilateralTradeDecision,
    focal_team_id: str,
) -> tuple[SideDirectionalAssessment, SideDirectionalAssessment]:
    if decision.side_a.team_id == focal_team_id:
        return decision.side_a, decision.side_b
    if decision.side_b.team_id == focal_team_id:
        return decision.side_b, decision.side_a
    raise ValueError("focal team must be one side of the bilateral decision")


def _feasibility_shape(
    decision: BilateralTradeDecision,
    counterparty: SideDirectionalAssessment,
) -> NegotiationFeasibilityShape:
    if counterparty.shape == SideDecisionShape.INCOMPLETE:
        return NegotiationFeasibilityShape.INCOMPLETE
    if counterparty.shape == SideDecisionShape.UNIFORM_LOSS:
        return NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED
    if decision.shape == BilateralDecisionShape.MUTUAL_GAIN:
        return NegotiationFeasibilityShape.MUTUAL_GAIN_CANDIDATE
    if decision.shape == BilateralDecisionShape.NEUTRAL:
        return NegotiationFeasibilityShape.NEUTRAL
    return NegotiationFeasibilityShape.MIXED


def assess_negotiation_feasibility(
    decision: BilateralTradeDecision,
    *,
    focal_team_id: str,
    acceptance: TradeAcceptanceView | None = None,
    model_version: str = "next5-negotiation-feasibility-v1",
) -> TradeNegotiationFeasibility:
    """Describe obvious bilateral feasibility without inventing acceptance odds.

    A complete uniform loss for the counterparty is explicitly surfaced as
    counterparty-dominated. Mixed outcomes remain mixed and incomplete evidence
    remains incomplete. An optional acceptance estimate/evidence view is attached
    beside this shape and never rewrites calculated consequences.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    focal, counterparty = _sides_for_focal(decision, focal_team_id)
    return TradeNegotiationFeasibility(
        proposal_id=decision.proposal_id,
        focal_team_id=focal.team_id,
        counterparty_team_id=counterparty.team_id,
        shape=_feasibility_shape(decision, counterparty),
        counterparty_decision_shape=counterparty.shape,
        acceptance=acceptance,
        model_version=model_version,
    )
