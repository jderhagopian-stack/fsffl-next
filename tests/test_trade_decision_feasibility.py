from datetime import UTC, datetime

from fsffl.trade_decision.acceptance import (
    AcceptanceEvidenceSet,
    AcceptanceModelStatus,
    TradeAcceptanceView,
)
from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    BilateralTradeDecision,
    Direction,
    SideDecisionShape,
    SideDirectionalAssessment,
)
from fsffl.trade_decision.feasibility import (
    NegotiationFeasibilityShape,
    assess_negotiation_feasibility,
)


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _side(team_id: str, shape: SideDecisionShape) -> SideDirectionalAssessment:
    direction = {
        SideDecisionShape.UNIFORM_GAIN: Direction.IMPROVES,
        SideDecisionShape.UNIFORM_LOSS: Direction.WORSENS,
        SideDecisionShape.NEUTRAL: Direction.UNCHANGED,
        SideDecisionShape.MIXED: Direction.IMPROVES,
        SideDecisionShape.INCOMPLETE: Direction.UNAVAILABLE,
    }[shape]
    return SideDirectionalAssessment(
        team_id=team_id,
        expected_wins=direction,
        playoff_probability=direction,
        first_place_probability=direction,
        asset_portfolio_mean=direction,
        largest_single_player_lineup_drop=direction,
        bench_forecasted_count=direction,
        unavailable_count=direction,
        missing_forecast_count=direction,
        shape=shape,
    )


def test_counterparty_uniform_loss_is_explicitly_dominated() -> None:
    decision = BilateralTradeDecision(
        proposal_id="p1",
        side_a=_side("a", SideDecisionShape.UNIFORM_GAIN),
        side_b=_side("b", SideDecisionShape.UNIFORM_LOSS),
        shape=BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
    )

    result = assess_negotiation_feasibility(decision, focal_team_id="a")

    assert result.shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED
    assert result.counterparty_team_id == "b"


def test_mutual_gain_is_only_a_candidate_not_acceptance_probability() -> None:
    decision = BilateralTradeDecision(
        proposal_id="p1",
        side_a=_side("a", SideDecisionShape.UNIFORM_GAIN),
        side_b=_side("b", SideDecisionShape.UNIFORM_GAIN),
        shape=BilateralDecisionShape.MUTUAL_GAIN,
    )

    result = assess_negotiation_feasibility(decision, focal_team_id="a")

    assert result.shape == NegotiationFeasibilityShape.MUTUAL_GAIN_CANDIDATE
    assert result.acceptance is None


def test_incomplete_counterparty_evidence_stays_incomplete() -> None:
    decision = BilateralTradeDecision(
        proposal_id="p1",
        side_a=_side("a", SideDecisionShape.UNIFORM_GAIN),
        side_b=_side("b", SideDecisionShape.INCOMPLETE),
        shape=BilateralDecisionShape.MIXED_OR_INCOMPLETE,
    )

    result = assess_negotiation_feasibility(decision, focal_team_id="a")

    assert result.shape == NegotiationFeasibilityShape.INCOMPLETE


def test_acceptance_view_attaches_without_rewriting_feasibility_shape() -> None:
    decision = BilateralTradeDecision(
        proposal_id="p1",
        side_a=_side("a", SideDecisionShape.UNIFORM_GAIN),
        side_b=_side("b", SideDecisionShape.UNIFORM_LOSS),
        shape=BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS,
    )
    evidence = AcceptanceEvidenceSet(
        proposal_id="p1",
        focal_team_id="a",
        counterparty_team_id="b",
        as_of=AS_OF,
    )
    acceptance = TradeAcceptanceView(
        proposal_id="p1",
        accepting_team_id="b",
        evidence=evidence,
        status=AcceptanceModelStatus.NOT_ESTIMATED,
    )

    result = assess_negotiation_feasibility(
        decision,
        focal_team_id="a",
        acceptance=acceptance,
    )

    assert result.shape == NegotiationFeasibilityShape.COUNTERPARTY_DOMINATED
    assert result.acceptance == acceptance
