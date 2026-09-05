from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.utility import OwnerStrategicPosture

from .feasibility import NegotiationFeasibilityShape, TradeNegotiationFeasibility
from .material_assessment import BilateralMaterialAssessment, SideMaterialAssessment
from .materiality import MaterialityDirection
from .strategy import StrategicTradeContext


class TradeDisposition(StrEnum):
    SUPPORT = "support"
    DECLINE = "decline"
    COUNTER_OR_REVIEW = "counter_or_review"
    NO_CLEAR_ADVANTAGE = "no_clear_advantage"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class TradeDispositionEvidence(FrozenModel):
    focal_team_id: str
    counterparty_team_id: str
    material_gains: tuple[str, ...] = ()
    material_losses: tuple[str, ...] = ()
    unavailable_metrics: tuple[str, ...] = ()
    negotiation_shape: NegotiationFeasibilityShape
    owner_posture: OwnerStrategicPosture
    strategic_resolution_applied: bool = False


class TradeDecisionDisposition(FrozenModel):
    proposal_id: str
    disposition: TradeDisposition
    evidence: TradeDispositionEvidence
    material_assessment_model_version: str
    negotiation_model_version: str
    strategic_context_model_version: str
    model_version: str = "next5-trade-disposition-v1"

    @model_validator(mode="after")
    def validate_disposition(self) -> "TradeDecisionDisposition":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("trade disposition identifiers cannot be blank")
        for version in (
            self.material_assessment_model_version,
            self.negotiation_model_version,
            self.strategic_context_model_version,
        ):
            if not version.strip():
                raise ValueError("trade disposition must record upstream model versions")
        return self


_METRICS = (
    "expected_wins",
    "playoff_probability",
    "first_place_probability",
    "largest_single_player_lineup_drop",
    "market_value",
    "intrinsic_value",
)


def _side_material(
    assessment: BilateralMaterialAssessment,
    focal_team_id: str,
) -> tuple[SideMaterialAssessment, SideMaterialAssessment]:
    if assessment.side_a.team_id == focal_team_id:
        return assessment.side_a, assessment.side_b
    if assessment.side_b.team_id == focal_team_id:
        return assessment.side_b, assessment.side_a
    raise ValueError("focal team must be one side of material assessment")


def _strategic_posture(context: StrategicTradeContext, focal_team_id: str) -> OwnerStrategicPosture:
    if context.side_a.team_id == focal_team_id:
        return context.side_a.owner_posture
    if context.side_b.team_id == focal_team_id:
        return context.side_b.owner_posture
    raise ValueError("focal team must be one side of strategic context")


def _metric_sets(side: SideMaterialAssessment) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    gains: list[str] = []
    losses: list[str] = []
    unavailable: list[str] = []
    for metric in _METRICS:
        direction = getattr(side, metric)
        if direction == MaterialityDirection.MATERIAL_GAIN:
            gains.append(metric)
        elif direction == MaterialityDirection.MATERIAL_LOSS:
            losses.append(metric)
        elif direction == MaterialityDirection.UNAVAILABLE:
            unavailable.append(metric)
    return tuple(gains), tuple(losses), tuple(unavailable)


def decide_trade_disposition(
    material_assessment: BilateralMaterialAssessment,
    negotiation: TradeNegotiationFeasibility,
    strategic_context: StrategicTradeContext,
    *,
    focal_team_id: str,
    model_version: str = "next5-trade-disposition-v1",
) -> TradeDecisionDisposition:
    """Produce a conservative disposition from explicit, material evidence.

    No scalar score is used. Any unavailable required channel yields insufficient
    evidence. Material gains plus material losses remain mixed and require review
    or a future governed strategic-resolution policy. Owner posture is recorded
    but does not silently resolve mixed evidence in v1.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    proposal_ids = {
        material_assessment.proposal_id,
        negotiation.proposal_id,
        strategic_context.proposal_id,
    }
    if len(proposal_ids) != 1:
        raise ValueError("trade disposition inputs must describe the same proposal")
    if negotiation.focal_team_id != focal_team_id:
        raise ValueError("negotiation feasibility must use the requested focal team")

    focal, counterparty = _side_material(material_assessment, focal_team_id)
    if counterparty.team_id != negotiation.counterparty_team_id:
        raise ValueError("material assessment counterparty must match negotiation feasibility")
    posture = _strategic_posture(strategic_context, focal_team_id)

    gains, losses, unavailable = _metric_sets(focal)
    if unavailable:
        disposition = TradeDisposition.INSUFFICIENT_EVIDENCE
    elif gains and losses:
        disposition = TradeDisposition.COUNTER_OR_REVIEW
    elif losses:
        disposition = TradeDisposition.DECLINE
    elif gains:
        if negotiation.shape in {
            NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED,
            NegotiationFeasibilityShape.MIXED,
        }:
            disposition = TradeDisposition.COUNTER_OR_REVIEW
        elif negotiation.shape == NegotiationFeasibilityShape.INCOMPLETE:
            disposition = TradeDisposition.INSUFFICIENT_EVIDENCE
        else:
            disposition = TradeDisposition.SUPPORT
    else:
        disposition = TradeDisposition.NO_CLEAR_ADVANTAGE

    return TradeDecisionDisposition(
        proposal_id=material_assessment.proposal_id,
        disposition=disposition,
        evidence=TradeDispositionEvidence(
            focal_team_id=focal_team_id,
            counterparty_team_id=counterparty.team_id,
            material_gains=gains,
            material_losses=losses,
            unavailable_metrics=unavailable,
            negotiation_shape=negotiation.shape,
            owner_posture=posture,
            strategic_resolution_applied=False,
        ),
        material_assessment_model_version=material_assessment.model_version,
        negotiation_model_version=negotiation.model_version,
        strategic_context_model_version=strategic_context.model_version,
        model_version=model_version,
    )
