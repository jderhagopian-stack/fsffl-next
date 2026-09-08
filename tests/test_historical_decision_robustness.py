import pytest

from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    SideDecisionShape,
    SideDirectionalAssessment,
)
from fsffl.trade_decision.historical_robustness import (
    HistoricalDecisionRobustnessStatus,
    HistoricalDecisionScenario,
    assess_historical_decision_robustness,
)


def decision(
    *,
    proposal_id: str = "trade-1",
    side_a_shape: SideDecisionShape,
    side_b_shape: SideDecisionShape,
    bilateral_shape: BilateralDecisionShape,
    model_version: str = "decision-v1",
) -> BilateralTradeDecision:
    return BilateralTradeDecision(
        proposal_id=proposal_id,
        side_a=SideDirectionalAssessment(team_id="A", shape=side_a_shape),
        side_b=SideDirectionalAssessment(team_id="B", shape=side_b_shape),
        shape=bilateral_shape,
        model_version=model_version,
    )


def test_robust_when_decision_shape_survives_lower_center_upper_scenarios() -> None:
    scenarios = tuple(
        HistoricalDecisionScenario(
            scenario_id=name,
            decision=decision(
                side_a_shape=SideDecisionShape.UNIFORM_GAIN,
                side_b_shape=SideDecisionShape.UNIFORM_LOSS,
                bilateral_shape=BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
            ),
        )
        for name in ("lower", "center", "upper")
    )

    result = assess_historical_decision_robustness(scenarios)

    assert result.status == HistoricalDecisionRobustnessStatus.ROBUST
    assert result.scenario_ids == ("lower", "center", "upper")


def test_sensitive_when_plausible_range_changes_decision_shape() -> None:
    scenarios = (
        HistoricalDecisionScenario(
            scenario_id="lower",
            decision=decision(
                side_a_shape=SideDecisionShape.UNIFORM_GAIN,
                side_b_shape=SideDecisionShape.UNIFORM_LOSS,
                bilateral_shape=BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
            ),
        ),
        HistoricalDecisionScenario(
            scenario_id="upper",
            decision=decision(
                side_a_shape=SideDecisionShape.UNIFORM_LOSS,
                side_b_shape=SideDecisionShape.UNIFORM_GAIN,
                bilateral_shape=BilateralDecisionShape.SIDE_B_GAIN_SIDE_A_LOSS,
            ),
        ),
    )

    result = assess_historical_decision_robustness(scenarios)

    assert result.status == HistoricalDecisionRobustnessStatus.SENSITIVE


def test_incomplete_decision_evidence_is_not_called_robust() -> None:
    scenarios = (
        HistoricalDecisionScenario(
            scenario_id="only",
            decision=decision(
                side_a_shape=SideDecisionShape.INCOMPLETE,
                side_b_shape=SideDecisionShape.UNIFORM_GAIN,
                bilateral_shape=BilateralDecisionShape.MIXED_OR_INCOMPLETE,
            ),
        ),
    )

    result = assess_historical_decision_robustness(scenarios)

    assert result.status == HistoricalDecisionRobustnessStatus.INCOMPLETE


def test_rejects_scenarios_for_different_proposals() -> None:
    scenarios = (
        HistoricalDecisionScenario(
            scenario_id="a",
            decision=decision(
                proposal_id="trade-1",
                side_a_shape=SideDecisionShape.NEUTRAL,
                side_b_shape=SideDecisionShape.NEUTRAL,
                bilateral_shape=BilateralDecisionShape.NEUTRAL,
            ),
        ),
        HistoricalDecisionScenario(
            scenario_id="b",
            decision=decision(
                proposal_id="trade-2",
                side_a_shape=SideDecisionShape.NEUTRAL,
                side_b_shape=SideDecisionShape.NEUTRAL,
                bilateral_shape=BilateralDecisionShape.NEUTRAL,
            ),
        ),
    )

    with pytest.raises(ValueError, match="one proposal"):
        assess_historical_decision_robustness(scenarios)
