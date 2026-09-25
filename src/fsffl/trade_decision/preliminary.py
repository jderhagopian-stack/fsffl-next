from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.position_strength import TeamPositionStrengthComparison

from .models import BilateralTradeProposal
from .policy_catalog import live_bounded_materiality_policy
from .roster_economics import (
    BilateralRosterAdjustedMarketNet,
    RosterAdjustedEconomicStatus,
)


class PreliminarySideShape(StrEnum):
    SUPPORTED = "supported"
    MIXED = "mixed"
    DOMINATED = "dominated"
    INCOMPLETE = "incomplete"


class PreliminaryBilateralShape(StrEnum):
    BILATERAL_SUPPORTED = "bilateral_supported"
    BILATERAL_FRICTION = "bilateral_friction"
    FOCAL_DOMINATED = "focal_dominated"
    COUNTERPARTY_DOMINATED = "counterparty_dominated"
    INCOMPLETE = "incomplete"


class PreliminarySideAssessment(FrozenModel):
    team_id: str
    shape: PreliminarySideShape
    roster_adjusted_market_delta: float | None = None
    mandatory_cut_market_cost: float | None = None
    starter_points_delta: float | None = None
    reasons: tuple[str, ...] = ()


class PreliminaryBilateralScreen(FrozenModel):
    proposal_id: str
    focal_team_id: str
    counterparty_team_id: str
    focal: PreliminarySideAssessment
    counterparty: PreliminarySideAssessment
    shape: PreliminaryBilateralShape
    acceptance_probability: None = None
    model_version: str = "next5-preliminary-bilateral-screen-v1"

    @model_validator(mode="after")
    def validate_sides(self) -> "PreliminaryBilateralScreen":
        if self.focal.team_id != self.focal_team_id:
            raise ValueError("focal preliminary assessment must match focal team")
        if self.counterparty.team_id != self.counterparty_team_id:
            raise ValueError("counterparty preliminary assessment must match counterparty team")
        if self.focal_team_id == self.counterparty_team_id:
            raise ValueError("preliminary bilateral screen requires distinct teams")
        return self


def _adjusted_side(net: BilateralRosterAdjustedMarketNet, team_id: str):
    if net.side_a.team_id == team_id:
        return net.side_a
    if net.side_b.team_id == team_id:
        return net.side_b
    raise ValueError("roster-adjusted economics do not cover requested team")


def _starter_delta(
    comparisons: Mapping[str, TeamPositionStrengthComparison],
    team_id: str,
) -> float | None:
    comparison = comparisons.get(team_id)
    if comparison is None:
        return None
    return sum(row.expected_points_delta for row in comparison.positions)


def _side_assessment(
    *,
    team_id: str,
    net: BilateralRosterAdjustedMarketNet,
    comparisons: Mapping[str, TeamPositionStrengthComparison],
    economic_materiality: float,
) -> PreliminarySideAssessment:
    adjusted = _adjusted_side(net, team_id)
    market_delta = (
        adjusted.roster_adjusted_market_delta
        if adjusted.status == RosterAdjustedEconomicStatus.COMPLETE
        else None
    )
    starter_delta = _starter_delta(comparisons, team_id)
    reasons: list[str] = []

    if market_delta is None:
        reasons.append("roster_adjusted_market_economics_incomplete")
    elif market_delta < -economic_materiality:
        reasons.append("material_market_value_loss_after_mandatory_cuts")
    elif market_delta > economic_materiality:
        reasons.append("material_market_value_gain_after_mandatory_cuts")
    else:
        reasons.append("market_economics_inside_materiality_band")

    if starter_delta is None:
        reasons.append("starter_replacement_effect_incomplete")
    elif starter_delta > 1e-9:
        reasons.append("optimized_starter_points_improve")
    elif starter_delta < -1e-9:
        reasons.append("optimized_starter_points_worsen")
    else:
        reasons.append("optimized_starter_points_unchanged")

    if market_delta is None and starter_delta is None:
        shape = PreliminarySideShape.INCOMPLETE
    elif (
        market_delta is not None
        and market_delta < -economic_materiality
        and (starter_delta is None or starter_delta <= 1e-9)
    ):
        shape = PreliminarySideShape.DOMINATED
    elif (
        starter_delta is not None
        and starter_delta < -1e-9
        and (market_delta is None or market_delta <= economic_materiality)
    ):
        shape = PreliminarySideShape.DOMINATED
    elif (
        market_delta is not None
        and market_delta >= -economic_materiality
        and starter_delta is not None
        and starter_delta >= -1e-9
        and (market_delta > economic_materiality or starter_delta > 1e-9)
    ):
        shape = PreliminarySideShape.SUPPORTED
    else:
        shape = PreliminarySideShape.MIXED

    return PreliminarySideAssessment(
        team_id=team_id,
        shape=shape,
        roster_adjusted_market_delta=market_delta,
        mandatory_cut_market_cost=adjusted.mandatory_cut_market_cost,
        starter_points_delta=starter_delta,
        reasons=tuple(reasons),
    )


def assess_preliminary_bilateral_screen(
    proposal: BilateralTradeProposal,
    *,
    focal_team_id: str,
    roster_adjusted_market_net: BilateralRosterAdjustedMarketNet,
    position_strength_comparisons: Mapping[str, TeamPositionStrengthComparison],
) -> PreliminaryBilateralScreen:
    """Classify a cheap pre-Simulation bilateral screen without a master score.

    The screen consumes Decision-owned roster-adjusted market economics plus
    Team-Utility-owned optimized starter replacement effects. It does not estimate
    acceptance, simulate season outcomes, or replace full Trade Center Decision.
    """

    side_ids = {proposal.side_a.team_id, proposal.side_b.team_id}
    if focal_team_id not in side_ids:
        raise ValueError("focal team must be one side of preliminary trade screen")
    counterparty_team_id = next(team_id for team_id in side_ids if team_id != focal_team_id)
    threshold = live_bounded_materiality_policy(
        as_of=proposal.as_of
    ).economic.mean_value_abs

    focal = _side_assessment(
        team_id=focal_team_id,
        net=roster_adjusted_market_net,
        comparisons=position_strength_comparisons,
        economic_materiality=threshold,
    )
    counterparty = _side_assessment(
        team_id=counterparty_team_id,
        net=roster_adjusted_market_net,
        comparisons=position_strength_comparisons,
        economic_materiality=threshold,
    )

    if focal.shape == PreliminarySideShape.DOMINATED:
        shape = PreliminaryBilateralShape.FOCAL_DOMINATED
    elif counterparty.shape == PreliminarySideShape.DOMINATED:
        shape = PreliminaryBilateralShape.COUNTERPARTY_DOMINATED
    elif (
        focal.shape == PreliminarySideShape.INCOMPLETE
        or counterparty.shape == PreliminarySideShape.INCOMPLETE
    ):
        shape = PreliminaryBilateralShape.INCOMPLETE
    elif (
        focal.shape == PreliminarySideShape.SUPPORTED
        and counterparty.shape == PreliminarySideShape.SUPPORTED
    ):
        shape = PreliminaryBilateralShape.BILATERAL_SUPPORTED
    else:
        shape = PreliminaryBilateralShape.BILATERAL_FRICTION

    return PreliminaryBilateralScreen(
        proposal_id=proposal.proposal_id,
        focal_team_id=focal_team_id,
        counterparty_team_id=counterparty_team_id,
        focal=focal,
        counterparty=counterparty,
        shape=shape,
    )
