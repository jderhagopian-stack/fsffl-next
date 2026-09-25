from datetime import UTC, datetime
from types import SimpleNamespace

from fsffl.trade_decision.preliminary import (
    PreliminaryBilateralShape,
    PreliminarySideShape,
    assess_preliminary_bilateral_screen,
)
from fsffl.trade_decision.roster_economics import RosterAdjustedEconomicStatus


AS_OF = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _proposal():
    return SimpleNamespace(
        proposal_id="proposal:test",
        as_of=AS_OF,
        side_a=SimpleNamespace(team_id="me"),
        side_b=SimpleNamespace(team_id="them"),
    )


def _net(focal_delta: float, counterparty_delta: float):
    return SimpleNamespace(
        side_a=SimpleNamespace(
            team_id="me",
            status=RosterAdjustedEconomicStatus.COMPLETE,
            roster_adjusted_market_delta=focal_delta,
            mandatory_cut_market_cost=0.0,
        ),
        side_b=SimpleNamespace(
            team_id="them",
            status=RosterAdjustedEconomicStatus.COMPLETE,
            roster_adjusted_market_delta=counterparty_delta,
            mandatory_cut_market_cost=0.0,
        ),
    )


def _comparison(team_id: str, delta: float):
    return SimpleNamespace(
        team_id=team_id,
        positions=(SimpleNamespace(expected_points_delta=delta),),
    )


def test_preliminary_screen_supports_bilateral_roster_improvement_without_acceptance_claim() -> None:
    result = assess_preliminary_bilateral_screen(
        _proposal(),
        focal_team_id="me",
        roster_adjusted_market_net=_net(0.0, 0.0),
        position_strength_comparisons={
            "me": _comparison("me", 10.0),
            "them": _comparison("them", 5.0),
        },
    )

    assert result.focal.shape == PreliminarySideShape.SUPPORTED
    assert result.counterparty.shape == PreliminarySideShape.SUPPORTED
    assert result.shape == PreliminaryBilateralShape.BILATERAL_SUPPORTED
    assert result.acceptance_probability is None


def test_preliminary_screen_marks_counterparty_dominated_when_value_and_roster_both_worsen() -> None:
    result = assess_preliminary_bilateral_screen(
        _proposal(),
        focal_team_id="me",
        roster_adjusted_market_net=_net(0.0, -1_000_000.0),
        position_strength_comparisons={
            "me": _comparison("me", 4.0),
            "them": _comparison("them", -3.0),
        },
    )

    assert result.counterparty.shape == PreliminarySideShape.DOMINATED
    assert result.shape == PreliminaryBilateralShape.COUNTERPARTY_DOMINATED
    assert "material_market_value_loss_after_mandatory_cuts" in result.counterparty.reasons


def test_preliminary_screen_does_not_collapse_mixed_channels_into_a_master_score() -> None:
    result = assess_preliminary_bilateral_screen(
        _proposal(),
        focal_team_id="me",
        roster_adjusted_market_net=_net(1_000_000.0, 1_000_000.0),
        position_strength_comparisons={
            "me": _comparison("me", -2.0),
            "them": _comparison("them", 2.0),
        },
    )

    assert result.focal.shape == PreliminarySideShape.MIXED
    assert result.shape == PreliminaryBilateralShape.BILATERAL_FRICTION
