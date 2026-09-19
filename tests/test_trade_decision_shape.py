from datetime import UTC, datetime

from fsffl.team_utility.scenario import (
    AssetPortfolioDelta,
    CompetitiveOutcomeDelta,
    RosterResilienceDelta,
    TeamScenarioDelta,
)
from fsffl.trade_decision.decision import (
    BilateralDecisionShape,
    Direction,
    SideDecisionShape,
    classify_bilateral_trade_decision,
)
from fsffl.trade_decision.evaluation import BilateralTradeEvaluation, TradeSideEvaluation


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)


def _delta(
    team_id: str,
    *,
    wins: float | None = None,
    playoff: float | None = None,
    first: float | None = None,
    value: float | None = None,
    lineup_drop: float | None = None,
    bench: int | None = None,
    unavailable: int | None = None,
    missing: int | None = None,
) -> TeamScenarioDelta:
    competitive = None
    if any(item is not None for item in (wins, playoff, first)):
        competitive = CompetitiveOutcomeDelta(
            expected_wins=wins,
            playoff_probability=playoff,
            first_place_probability=first,
        )
    portfolio = None
    if value is not None:
        portfolio = AssetPortfolioDelta(mean_value=value, stddev_value=0.0)
    resilience = None
    if any(item is not None for item in (lineup_drop, bench, unavailable, missing)):
        resilience = RosterResilienceDelta(
            largest_single_player_lineup_drop=lineup_drop,
            bench_forecasted_count=bench,
            unavailable_count=unavailable,
            missing_forecast_count=missing,
        )
    return TeamScenarioDelta(
        team_id=team_id,
        baseline_as_of=AS_OF,
        scenario_as_of=AS_OF,
        competitive=competitive,
        asset_portfolio=portfolio,
        resilience=resilience,
        calculated_state_before="competitive",
        calculated_state_after="competitive",
        model_version="test",
    )


def _evaluation(a: TeamScenarioDelta, b: TeamScenarioDelta) -> BilateralTradeEvaluation:
    return BilateralTradeEvaluation(
        proposal_id="trade-1",
        side_a=TradeSideEvaluation(team_id="a", delta=a),
        side_b=TradeSideEvaluation(team_id="b", delta=b),
    )


def test_mutual_gain_requires_complete_no_worsening_evidence() -> None:
    result = classify_bilateral_trade_decision(
        _evaluation(
            _delta(
                "a",
                wins=0.4,
                playoff=0.03,
                first=0.01,
                value=50.0,
                lineup_drop=-1.0,
                bench=1,
                unavailable=0,
                missing=0,
            ),
            _delta(
                "b",
                wins=0.2,
                playoff=0.02,
                first=0.01,
                value=25.0,
                lineup_drop=-0.5,
                bench=1,
                unavailable=0,
                missing=0,
            ),
        )
    )

    assert result.side_a.shape == SideDecisionShape.UNIFORM_GAIN
    assert result.side_b.shape == SideDecisionShape.UNIFORM_GAIN
    assert result.shape == BilateralDecisionShape.MUTUAL_GAIN


def test_mixed_short_and_long_term_tradeoffs_stay_mixed() -> None:
    result = classify_bilateral_trade_decision(
        _evaluation(
            _delta(
                "a",
                wins=0.6,
                playoff=0.05,
                first=0.02,
                value=-300.0,
                lineup_drop=1.0,
                bench=-1,
                unavailable=0,
                missing=0,
            ),
            _delta(
                "b",
                wins=-0.5,
                playoff=-0.04,
                first=-0.02,
                value=300.0,
                lineup_drop=-1.0,
                bench=1,
                unavailable=0,
                missing=0,
            ),
        )
    )

    assert result.side_a.shape == SideDecisionShape.MIXED
    assert result.side_b.shape == SideDecisionShape.MIXED
    assert result.shape == BilateralDecisionShape.MIXED_OR_INCOMPLETE


def test_missing_channels_do_not_masquerade_as_mutual_gain() -> None:
    result = classify_bilateral_trade_decision(
        _evaluation(
            _delta("a", wins=0.5),
            _delta("b", wins=0.4),
        )
    )

    assert result.side_a.expected_wins == Direction.IMPROVES
    assert result.side_a.shape == SideDecisionShape.INCOMPLETE
    assert result.side_b.shape == SideDecisionShape.INCOMPLETE
    assert result.shape == BilateralDecisionShape.MIXED_OR_INCOMPLETE


def test_resilience_metrics_use_correct_directionality() -> None:
    result = classify_bilateral_trade_decision(
        _evaluation(
            _delta(
                "a",
                wins=0.0,
                playoff=0.0,
                first=0.0,
                value=0.0,
                lineup_drop=-2.0,
                bench=2,
                unavailable=-1,
                missing=-1,
            ),
            _delta(
                "b",
                wins=0.0,
                playoff=0.0,
                first=0.0,
                value=0.0,
                lineup_drop=2.0,
                bench=-2,
                unavailable=1,
                missing=1,
            ),
        )
    )

    assert result.side_a.largest_single_player_lineup_drop == Direction.IMPROVES
    assert result.side_a.bench_forecasted_count == Direction.IMPROVES
    assert result.side_a.unavailable_count == Direction.IMPROVES
    assert result.side_a.missing_forecast_count == Direction.IMPROVES
    assert result.side_a.shape == SideDecisionShape.UNIFORM_GAIN
    assert result.side_b.shape == SideDecisionShape.UNIFORM_LOSS
    assert result.shape == BilateralDecisionShape.SIDE_A_GAIN_SIDE_B_LOSS
