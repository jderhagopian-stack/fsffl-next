from datetime import UTC, datetime

import pytest

from fsffl.state.models import PlayerAsset
from fsffl.team_utility import (
    CalculatedCompetitiveState,
    TeamCompetitiveOutcome,
    TeamUtilityVector,
)
from fsffl.trade_decision import (
    BilateralTradeProposal,
    TradeLeg,
    evaluate_bilateral_trade_deltas,
)

AS_OF = datetime(2026, 9, 5, 17, 0, tzinfo=UTC)


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="proposal:eval",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
        side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
    )


def _vector(team_id: str, *, wins: float, playoff: float, first: float) -> TeamUtilityVector:
    return TeamUtilityVector(
        team_id=team_id,
        as_of=AS_OF,
        competitive_outcome=TeamCompetitiveOutcome(
            team_id=team_id,
            expected_wins=wins,
            wins_stddev=1.0,
            playoff_probability=playoff,
            first_place_probability=first,
            simulation_count=50000,
            simulation_model_version="sim-v1",
        ),
        calculated_competitive_state=CalculatedCompetitiveState.COMPETITIVE,
        model_version="utility-v1",
    )


def test_bilateral_evaluation_preserves_each_side_separately() -> None:
    result = evaluate_bilateral_trade_deltas(
        _proposal(),
        before_a=_vector("A", wins=8.0, playoff=0.50, first=0.10),
        after_a=_vector("A", wins=9.0, playoff=0.60, first=0.15),
        before_b=_vector("B", wins=9.0, playoff=0.65, first=0.20),
        after_b=_vector("B", wins=8.5, playoff=0.58, first=0.16),
    )

    assert result.side_a.delta.competitive is not None
    assert result.side_b.delta.competitive is not None
    assert result.side_a.delta.competitive.expected_wins == pytest.approx(1.0)
    assert result.side_b.delta.competitive.expected_wins == pytest.approx(-0.5)
    assert result.side_a.delta.competitive.playoff_probability == pytest.approx(0.10)
    assert result.side_b.delta.competitive.playoff_probability == pytest.approx(-0.07)


def test_side_mismatch_fails_closed() -> None:
    with pytest.raises(ValueError, match="side A"):
        evaluate_bilateral_trade_deltas(
            _proposal(),
            before_a=_vector("B", wins=8.0, playoff=0.50, first=0.10),
            after_a=_vector("B", wins=9.0, playoff=0.60, first=0.15),
            before_b=_vector("B", wins=9.0, playoff=0.65, first=0.20),
            after_b=_vector("B", wins=8.5, playoff=0.58, first=0.16),
        )


def test_evaluation_does_not_infer_trade_recommendation() -> None:
    result = evaluate_bilateral_trade_deltas(
        _proposal(),
        before_a=_vector("A", wins=8.0, playoff=0.50, first=0.10),
        after_a=_vector("A", wins=8.2, playoff=0.52, first=0.11),
        before_b=_vector("B", wins=8.0, playoff=0.50, first=0.10),
        after_b=_vector("B", wins=8.2, playoff=0.52, first=0.11),
    )

    payload = result.model_dump()
    assert "recommendation" not in payload
    assert "score" not in payload
    assert "grade" not in payload
