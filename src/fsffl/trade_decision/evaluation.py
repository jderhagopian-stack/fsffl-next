from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility import TeamScenarioDelta, TeamUtilityVector, compare_team_utility_vectors

from .models import BilateralTradeProposal


class TradeSideEvaluation(FrozenModel):
    team_id: str
    delta: TeamScenarioDelta

    @model_validator(mode="after")
    def validate_team(self) -> "TradeSideEvaluation":
        if self.delta.team_id != self.team_id:
            raise ValueError("trade side evaluation must match delta team")
        return self


class BilateralTradeEvaluation(FrozenModel):
    """Structured bilateral consequences without a master score or recommendation."""

    proposal_id: str
    side_a: TradeSideEvaluation
    side_b: TradeSideEvaluation
    model_version: str = "next5-bilateral-evaluation-v1"

    @model_validator(mode="after")
    def validate_evaluation(self) -> "BilateralTradeEvaluation":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("bilateral evaluation identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("bilateral evaluation requires two distinct teams")
        return self


def evaluate_bilateral_trade_deltas(
    proposal: BilateralTradeProposal,
    *,
    before_a: TeamUtilityVector,
    after_a: TeamUtilityVector,
    before_b: TeamUtilityVector,
    after_b: TeamUtilityVector,
    model_version: str = "next5-bilateral-evaluation-v1",
) -> BilateralTradeEvaluation:
    """Compare authoritative NEXT-4 before/after states for both sides.

    NEXT-5 does not recompute forecasts, values, simulations, or roster utility
    here. It only binds the two independent NEXT-4 scenario deltas to the trade
    proposal so downstream decision logic can reason about bilateral effects.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")

    expected_a = proposal.side_a.team_id
    expected_b = proposal.side_b.team_id
    if before_a.team_id != expected_a or after_a.team_id != expected_a:
        raise ValueError("side A utility vectors must describe proposal side A")
    if before_b.team_id != expected_b or after_b.team_id != expected_b:
        raise ValueError("side B utility vectors must describe proposal side B")

    delta_a = compare_team_utility_vectors(before_a, after_a)
    delta_b = compare_team_utility_vectors(before_b, after_b)

    return BilateralTradeEvaluation(
        proposal_id=proposal.proposal_id,
        side_a=TradeSideEvaluation(team_id=expected_a, delta=delta_a),
        side_b=TradeSideEvaluation(team_id=expected_b, delta=delta_b),
        model_version=model_version,
    )
