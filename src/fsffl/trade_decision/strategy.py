from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.utility import OwnerStrategicPosture

from .decision import BilateralTradeDecision


class StrategicSideContext(FrozenModel):
    """Owner posture attached beside calculated trade consequences.

    This object contains no weights and performs no recalculation. It exists so
    downstream preference logic can see explicit owner intent without allowing
    that intent to rewrite NEXT-4 calculated state or NEXT-5 decision evidence.
    """

    team_id: str
    owner_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED
    posture_version: str = "owner-posture-v1"

    @model_validator(mode="after")
    def validate_context(self) -> "StrategicSideContext":
        if not self.team_id.strip() or not self.posture_version.strip():
            raise ValueError("strategic context identifiers cannot be blank")
        return self


class StrategicTradeContext(FrozenModel):
    proposal_id: str
    calculated_decision: BilateralTradeDecision
    side_a: StrategicSideContext
    side_b: StrategicSideContext
    model_version: str = "next5-strategic-trade-context-v1"

    @model_validator(mode="after")
    def validate_context(self) -> "StrategicTradeContext":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("strategic trade context identifiers cannot be blank")
        if self.calculated_decision.proposal_id != self.proposal_id:
            raise ValueError("strategic context must match calculated decision proposal")
        if self.side_a.team_id != self.calculated_decision.side_a.team_id:
            raise ValueError("strategic side A must match calculated decision side A")
        if self.side_b.team_id != self.calculated_decision.side_b.team_id:
            raise ValueError("strategic side B must match calculated decision side B")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("strategic trade context requires distinct teams")
        return self


def attach_owner_strategy(
    decision: BilateralTradeDecision,
    *,
    side_a_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED,
    side_b_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED,
    posture_version: str = "owner-posture-v1",
    model_version: str = "next5-strategic-trade-context-v1",
) -> StrategicTradeContext:
    """Attach explicit owner posture without modifying calculated decision output."""

    if not posture_version.strip() or not model_version.strip():
        raise ValueError("strategy versions cannot be blank")
    return StrategicTradeContext(
        proposal_id=decision.proposal_id,
        calculated_decision=decision,
        side_a=StrategicSideContext(
            team_id=decision.side_a.team_id,
            owner_posture=side_a_posture,
            posture_version=posture_version,
        ),
        side_b=StrategicSideContext(
            team_id=decision.side_b.team_id,
            owner_posture=side_b_posture,
            posture_version=posture_version,
        ),
        model_version=model_version,
    )
