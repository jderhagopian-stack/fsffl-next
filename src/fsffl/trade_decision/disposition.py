from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.utility import OwnerStrategicPosture

from .feasibility import NegotiationFeasibilityShape, TradeNegotiationFeasibility
from .material_assessment import BilateralMaterialAssessment, SideMaterialAssessment
from .materiality import MaterialityDirection
from .package_economics import (
    PackageEconomicAssessment,
    PackageEconomicResolution,
    PackageEconomicStatus,
)
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
    package_economic_resolution: PackageEconomicResolution | None = None
    strategic_resolution_applied: bool = False


class TradeDecisionDisposition(FrozenModel):
    proposal_id: str
    disposition: TradeDisposition
    evidence: TradeDispositionEvidence
    material_assessment_model_version: str
    negotiation_model_version: str
    strategic_context_model_version: str
    model_version: str = "next5-trade-disposition-v5"

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


# These are separate action-facing evidence dimensions, not a weighted score.
# Market value measures current tradable economics; intrinsic value measures the
# existing Value-owned long-term franchise/dynasty economic coordinate. Including
# both here lets a material conflict resolve to COUNTER_OR_REVIEW rather than
# silently allowing near-term/market gains to hide a long-term franchise-value loss.
_METRICS = (
    "expected_wins",
    "playoff_probability",
    "championship_probability",
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


def _apply_package_guard(
    disposition: TradeDisposition,
    package_economics: PackageEconomicAssessment | None,
    *,
    focal_team_id: str,
) -> TradeDisposition:
    if package_economics is None or package_economics.status == PackageEconomicStatus.NOT_APPLICABLE:
        return disposition
    if package_economics.status == PackageEconomicStatus.INCOMPLETE:
        return TradeDisposition.INSUFFICIENT_EVIDENCE

    resolution = package_economics.resolution
    focal_is_singleton_sender = focal_team_id == package_economics.singleton_sender_team_id
    if resolution == PackageEconomicResolution.SINGLETON_UNDERPAID and focal_is_singleton_sender:
        return TradeDisposition.DECLINE
    if (
        resolution == PackageEconomicResolution.WITHIN_PROVISIONAL_BAND
        and focal_is_singleton_sender
        and disposition not in {TradeDisposition.DECLINE, TradeDisposition.INSUFFICIENT_EVIDENCE}
    ):
        return TradeDisposition.COUNTER_OR_REVIEW
    return disposition


def decide_trade_disposition(
    material_assessment: BilateralMaterialAssessment,
    negotiation: TradeNegotiationFeasibility,
    strategic_context: StrategicTradeContext,
    *,
    focal_team_id: str,
    package_economics: PackageEconomicAssessment | None = None,
    model_version: str = "next5-trade-disposition-v5",
) -> TradeDecisionDisposition:
    """Produce the focal team's action disposition from material evidence.

    Counterparty feasibility remains separate negotiation context. It cannot turn
    a clean focal-team material gain into a counter recommendation. If a deal is
    already available and materially helps the focal team without a material loss,
    the focal action is support; whether the counterparty should agree is a separate
    question surfaced by negotiation feasibility.

    Current market economics and long-term intrinsic franchise value remain distinct
    Value-owned coordinates. They enter action synthesis once as categorical
    materiality directions; they are never blended into a master score.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    proposal_ids = {
        material_assessment.proposal_id,
        negotiation.proposal_id,
        strategic_context.proposal_id,
    }
    if package_economics is not None:
        proposal_ids.add(package_economics.proposal_id)
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
        disposition = TradeDisposition.SUPPORT
    else:
        disposition = TradeDisposition.NO_CLEAR_ADVANTAGE

    disposition = _apply_package_guard(disposition, package_economics, focal_team_id=focal_team_id)

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
            package_economic_resolution=(
                package_economics.resolution if package_economics is not None else None
            ),
            strategic_resolution_applied=False,
        ),
        material_assessment_model_version=material_assessment.model_version,
        negotiation_model_version=negotiation.model_version,
        strategic_context_model_version=strategic_context.model_version,
        model_version=model_version,
    )
