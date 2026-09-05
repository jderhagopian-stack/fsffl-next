from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    Direction,
    SideDecisionShape,
    SideDirectionalAssessment,
)
from fsffl.trade_decision.strategy import attach_owner_strategy


def _side(team_id: str) -> SideDirectionalAssessment:
    return SideDirectionalAssessment(
        team_id=team_id,
        expected_wins=Direction.IMPROVES,
        playoff_probability=Direction.IMPROVES,
        first_place_probability=Direction.IMPROVES,
        asset_portfolio_mean=Direction.WORSENS,
        largest_single_player_lineup_drop=Direction.IMPROVES,
        bench_forecasted_count=Direction.UNCHANGED,
        unavailable_count=Direction.UNCHANGED,
        missing_forecast_count=Direction.UNCHANGED,
        shape=SideDecisionShape.MIXED,
    )


def _decision() -> BilateralTradeDecision:
    return BilateralTradeDecision(
        proposal_id="p1",
        side_a=_side("a"),
        side_b=_side("b"),
        shape=BilateralDecisionShape.MIXED_OR_INCOMPLETE,
    )


def test_owner_posture_is_attached_without_rewriting_calculated_decision() -> None:
    decision = _decision()
    context = attach_owner_strategy(
        decision,
        side_a_posture=OwnerStrategicPosture.WIN_NOW,
        side_b_posture=OwnerStrategicPosture.REBUILD,
    )

    assert context.calculated_decision == decision
    assert context.side_a.owner_posture == OwnerStrategicPosture.WIN_NOW
    assert context.side_b.owner_posture == OwnerStrategicPosture.REBUILD
    assert context.calculated_decision.side_a.asset_portfolio_mean == Direction.WORSENS


def test_different_owner_postures_do_not_change_calculated_output() -> None:
    decision = _decision()
    first = attach_owner_strategy(
        decision,
        side_a_posture=OwnerStrategicPosture.WIN_NOW,
        side_b_posture=OwnerStrategicPosture.BALANCED,
    )
    second = attach_owner_strategy(
        decision,
        side_a_posture=OwnerStrategicPosture.REBUILD,
        side_b_posture=OwnerStrategicPosture.RETOOL,
    )

    assert first.calculated_decision == second.calculated_decision == decision
    assert first.side_a.owner_posture != second.side_a.owner_posture
