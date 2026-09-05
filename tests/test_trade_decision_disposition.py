from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    Direction,
    SideDecisionShape,
    SideDirectionalAssessment,
)
from fsffl.trade_decision.disposition import TradeDisposition, decide_trade_disposition
from fsffl.trade_decision.feasibility import (
    NegotiationFeasibilityShape,
    TradeNegotiationFeasibility,
)
from fsffl.trade_decision.material_assessment import (
    BilateralMaterialAssessment,
    SideMaterialAssessment,
)
from fsffl.trade_decision.materiality import MaterialityDirection
from fsffl.trade_decision.strategy import attach_owner_strategy


def _material_side(team_id: str, *, gain=False, loss=False, unavailable=False):
    if unavailable:
        directions = [MaterialityDirection.UNAVAILABLE] * 6
    elif gain:
        directions = [MaterialityDirection.MATERIAL_GAIN] * 6
    elif loss:
        directions = [MaterialityDirection.MATERIAL_LOSS] * 6
    else:
        directions = [MaterialityDirection.IMMATERIAL] * 6
    return SideMaterialAssessment(
        team_id=team_id,
        expected_wins=directions[0],
        playoff_probability=directions[1],
        first_place_probability=directions[2],
        largest_single_player_lineup_drop=directions[3],
        market_value=directions[4],
        intrinsic_value=directions[5],
    )


def _mixed_material_side(team_id: str):
    return SideMaterialAssessment(
        team_id=team_id,
        expected_wins=MaterialityDirection.MATERIAL_GAIN,
        playoff_probability=MaterialityDirection.MATERIAL_GAIN,
        first_place_probability=MaterialityDirection.IMMATERIAL,
        largest_single_player_lineup_drop=MaterialityDirection.IMMATERIAL,
        market_value=MaterialityDirection.MATERIAL_LOSS,
        intrinsic_value=MaterialityDirection.MATERIAL_LOSS,
    )


def _calculated_decision() -> BilateralTradeDecision:
    side = lambda team_id: SideDirectionalAssessment(
        team_id=team_id,
        expected_wins=Direction.IMPROVES,
        playoff_probability=Direction.IMPROVES,
        first_place_probability=Direction.UNCHANGED,
        asset_portfolio_mean=Direction.WORSENS,
        largest_single_player_lineup_drop=Direction.UNCHANGED,
        bench_forecasted_count=Direction.UNCHANGED,
        unavailable_count=Direction.UNCHANGED,
        missing_forecast_count=Direction.UNCHANGED,
        shape=SideDecisionShape.MIXED,
    )
    return BilateralTradeDecision(
        proposal_id="p1",
        side_a=side("a"),
        side_b=side("b"),
        shape=BilateralDecisionShape.MIXED_OR_INCOMPLETE,
    )


def _assessment(a, b):
    return BilateralMaterialAssessment(
        proposal_id="p1",
        side_a=a,
        side_b=b,
        competitive_policy_version="cp1",
        economic_policy_version="ep1",
    )


def _negotiation(shape: NegotiationFeasibilityShape):
    return TradeNegotiationFeasibility(
        proposal_id="p1",
        focal_team_id="a",
        counterparty_team_id="b",
        shape=shape,
        counterparty_decision_shape=SideDecisionShape.MIXED,
    )


def _strategy(posture=OwnerStrategicPosture.DEFAULT_CALCULATED):
    return attach_owner_strategy(
        _calculated_decision(),
        side_a_posture=posture,
        side_b_posture=OwnerStrategicPosture.DEFAULT_CALCULATED,
    )


def test_complete_material_gain_can_support_when_counterparty_not_dominated() -> None:
    result = decide_trade_disposition(
        _assessment(_material_side("a", gain=True), _material_side("b", gain=True)),
        _negotiation(NegotiationFeasibilityShape.MUTUAL_GAIN_CANDIDATE),
        _strategy(),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.SUPPORT
    assert result.evidence.material_losses == ()


def test_uniform_material_loss_declines() -> None:
    result = decide_trade_disposition(
        _assessment(_material_side("a", loss=True), _material_side("b", gain=True)),
        _negotiation(NegotiationFeasibilityShape.MIXED),
        _strategy(),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.DECLINE


def test_mixed_material_tradeoffs_require_counter_or_review() -> None:
    result = decide_trade_disposition(
        _assessment(_mixed_material_side("a"), _mixed_material_side("b")),
        _negotiation(NegotiationFeasibilityShape.MIXED),
        _strategy(OwnerStrategicPosture.WIN_NOW),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.COUNTER_OR_REVIEW
    assert result.evidence.owner_posture == OwnerStrategicPosture.WIN_NOW
    assert result.evidence.strategic_resolution_applied is False


def test_missing_required_channel_yields_insufficient_evidence() -> None:
    result = decide_trade_disposition(
        _assessment(_material_side("a", unavailable=True), _material_side("b", gain=True)),
        _negotiation(NegotiationFeasibilityShape.INCOMPLETE),
        _strategy(),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.INSUFFICIENT_EVIDENCE
    assert "market_value" in result.evidence.unavailable_metrics


def test_focal_gain_with_counterparty_dominated_is_not_auto_supported() -> None:
    result = decide_trade_disposition(
        _assessment(_material_side("a", gain=True), _material_side("b", loss=True)),
        _negotiation(NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED),
        _strategy(),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.COUNTER_OR_REVIEW


def test_all_immaterial_changes_have_no_clear_advantage() -> None:
    result = decide_trade_disposition(
        _assessment(_material_side("a"), _material_side("b")),
        _negotiation(NegotiationFeasibilityShape.NEUTRAL),
        _strategy(),
        focal_team_id="a",
    )
    assert result.disposition == TradeDisposition.NO_CLEAR_ADVANTAGE
