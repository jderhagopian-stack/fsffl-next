from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from fsffl.state.models import FrozenModel
from fsffl.team_utility.scenario import TeamScenarioDelta

from .evaluation import BilateralTradeEvaluation, TradeSideEvaluation


class Direction(StrEnum):
    IMPROVES = "improves"
    WORSENS = "worsens"
    UNCHANGED = "unchanged"
    UNAVAILABLE = "unavailable"


class SideDecisionShape(StrEnum):
    UNIFORM_GAIN = "uniform_gain"
    UNIFORM_LOSS = "uniform_loss"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    INCOMPLETE = "incomplete"


class BilateralDecisionShape(StrEnum):
    MUTUAL_GAIN = "mutual_gain"
    SIDE_A_GAIN_SIDE_B_LOSS = "side_a_gain_side_b_loss"
    SIDE_B_GAIN_SIDE_A_LOSS = "side_b_gain_side_a_loss"
    MIXED_OR_INCOMPLETE = "mixed_or_incomplete"
    NEUTRAL = "neutral"


class SideDirectionalAssessment(FrozenModel):
    team_id: str
    expected_wins: Direction = Direction.UNAVAILABLE
    playoff_probability: Direction = Direction.UNAVAILABLE
    first_place_probability: Direction = Direction.UNAVAILABLE
    asset_portfolio_mean: Direction = Direction.UNAVAILABLE
    largest_single_player_lineup_drop: Direction = Direction.UNAVAILABLE
    bench_forecasted_count: Direction = Direction.UNAVAILABLE
    unavailable_count: Direction = Direction.UNAVAILABLE
    missing_forecast_count: Direction = Direction.UNAVAILABLE
    shape: SideDecisionShape


class BilateralTradeDecision(FrozenModel):
    proposal_id: str
    side_a: SideDirectionalAssessment
    side_b: SideDirectionalAssessment
    shape: BilateralDecisionShape
    model_version: str = "next5-bilateral-decision-v1"

    @model_validator(mode="after")
    def validate_decision(self) -> "BilateralTradeDecision":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("decision identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("bilateral decision requires distinct teams")
        return self


def _positive(value: float | int | None) -> Direction:
    if value is None:
        return Direction.UNAVAILABLE
    if value > 0:
        return Direction.IMPROVES
    if value < 0:
        return Direction.WORSENS
    return Direction.UNCHANGED


def _negative(value: float | int | None) -> Direction:
    """Classify metrics where a decrease is favorable."""

    if value is None:
        return Direction.UNAVAILABLE
    if value < 0:
        return Direction.IMPROVES
    if value > 0:
        return Direction.WORSENS
    return Direction.UNCHANGED


def _shape(directions: tuple[Direction, ...]) -> SideDecisionShape:
    available = tuple(direction for direction in directions if direction != Direction.UNAVAILABLE)
    if not available:
        return SideDecisionShape.INCOMPLETE

    has_gain = Direction.IMPROVES in available
    has_loss = Direction.WORSENS in available
    if has_gain and has_loss:
        return SideDecisionShape.MIXED
    if has_gain:
        return SideDecisionShape.UNIFORM_GAIN
    if has_loss:
        return SideDecisionShape.UNIFORM_LOSS
    if len(available) != len(directions):
        return SideDecisionShape.INCOMPLETE
    return SideDecisionShape.NEUTRAL


def assess_side_direction(side: TradeSideEvaluation) -> SideDirectionalAssessment:
    delta: TeamScenarioDelta = side.delta

    expected_wins = _positive(delta.competitive.expected_wins if delta.competitive else None)
    playoff_probability = _positive(
        delta.competitive.playoff_probability if delta.competitive else None
    )
    first_place_probability = _positive(
        delta.competitive.first_place_probability if delta.competitive else None
    )
    asset_portfolio_mean = _positive(
        delta.asset_portfolio.mean_value if delta.asset_portfolio else None
    )
    largest_single_player_lineup_drop = _negative(
        delta.resilience.largest_single_player_lineup_drop if delta.resilience else None
    )
    bench_forecasted_count = _positive(
        delta.resilience.bench_forecasted_count if delta.resilience else None
    )
    unavailable_count = _negative(delta.resilience.unavailable_count if delta.resilience else None)
    missing_forecast_count = _negative(
        delta.resilience.missing_forecast_count if delta.resilience else None
    )

    directions = (
        expected_wins,
        playoff_probability,
        first_place_probability,
        asset_portfolio_mean,
        largest_single_player_lineup_drop,
        bench_forecasted_count,
        unavailable_count,
        missing_forecast_count,
    )
    return SideDirectionalAssessment(
        team_id=side.team_id,
        expected_wins=expected_wins,
        playoff_probability=playoff_probability,
        first_place_probability=first_place_probability,
        asset_portfolio_mean=asset_portfolio_mean,
        largest_single_player_lineup_drop=largest_single_player_lineup_drop,
        bench_forecasted_count=bench_forecasted_count,
        unavailable_count=unavailable_count,
        missing_forecast_count=missing_forecast_count,
        shape=_shape(directions),
    )


def _bilateral_shape(
    side_a: SideDirectionalAssessment,
    side_b: SideDirectionalAssessment,
) -> BilateralDecisionShape:
    if side_a.shape == SideDecisionShape.UNIFORM_GAIN and side_b.shape == SideDecisionShape.UNIFORM_GAIN:
        return BilateralDecisionShape.MUTUAL_GAIN
    if side_a.shape == SideDecisionShape.UNIFORM_GAIN and side_b.shape == SideDecisionShape.UNIFORM_LOSS:
        return BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS
    if side_b.shape == SideDecisionShape.UNIFORM_GAIN and side_a.shape == SideDecisionShape.UNIFORM_LOSS:
        return BilateralDecisionShape.SIDE_B_GAIN_SIDE_A_LOSS
    if side_a.shape == SideDecisionShape.NEUTRAL and side_b.shape == SideDecisionShape.NEUTRAL:
        return BilateralDecisionShape.NEUTRAL
    return BilateralDecisionShape.MIXED_OR_INCOMPLETE


def classify_bilateral_trade_decision(
    evaluation: BilateralTradeEvaluation,
    *,
    model_version: str = "next5-bilateral-decision-v1",
) -> BilateralTradeDecision:
    """Classify bilateral outcome shape without scalar utility or thresholds.

    The classifier is intentionally exact and descriptive. It does not interpret
    Monte Carlo noise as materiality, estimate acceptance, recommend action, or
    weight one channel against another. Materiality/tolerance policy, if later
    required, must be separately governed rather than hidden here.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    side_a = assess_side_direction(evaluation.side_a)
    side_b = assess_side_direction(evaluation.side_b)
    return BilateralTradeDecision(
        proposal_id=evaluation.proposal_id,
        side_a=side_a,
        side_b=side_b,
        shape=_bilateral_shape(side_a, side_b),
        model_version=model_version,
    )
