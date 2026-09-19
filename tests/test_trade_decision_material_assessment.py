from datetime import UTC, datetime, timedelta

import pytest

from fsffl.team_utility.scenario import CompetitiveOutcomeDelta, RosterResilienceDelta, TeamScenarioDelta
from fsffl.trade_decision.economic_net import (
    BilateralTradeEconomicNet,
    EconomicNetStatus,
    ExpectedEconomicNetDelta,
    TradeLegEconomicNet,
)
from fsffl.trade_decision.economics import EconomicConcept
from fsffl.trade_decision.evaluation import BilateralTradeEvaluation, TradeSideEvaluation
from fsffl.trade_decision.material_assessment import assess_bilateral_materiality
from fsffl.trade_decision.materiality import (
    CompetitiveMaterialityPolicy,
    EconomicMaterialityPolicy,
    MaterialityDirection,
)
from fsffl.value.models import ValueScale


AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
SCALE = ValueScale(scale_id="dynasty", version="v1", unit_label="points")


def _side_delta(team_id: str, wins: float, playoff: float, first: float, lineup_drop: float):
    return TeamScenarioDelta(
        team_id=team_id,
        baseline_as_of=AS_OF,
        scenario_as_of=AS_OF,
        competitive=CompetitiveOutcomeDelta(
            expected_wins=wins,
            playoff_probability=playoff,
            first_place_probability=first,
        ),
        resilience=RosterResilienceDelta(
            largest_single_player_lineup_drop=lineup_drop,
            bench_forecasted_count=0,
            unavailable_count=0,
            missing_forecast_count=0,
        ),
        calculated_state_before="competitive",
        calculated_state_after="competitive",
        model_version="test",
    )


def _economic(team_id: str, market: float, intrinsic: float):
    return TradeLegEconomicNet(
        team_id=team_id,
        market=ExpectedEconomicNetDelta(
            concept=EconomicConcept.MARKET_PRICE,
            mean_delta=market,
            scale=SCALE,
            status=EconomicNetStatus.COMPLETE,
            sent_mean=100.0,
            received_mean=100.0 + market,
            model_versions=("m1",),
        ),
        intrinsic=ExpectedEconomicNetDelta(
            concept=EconomicConcept.INTRINSIC_VALUE,
            mean_delta=intrinsic,
            scale=SCALE,
            status=EconomicNetStatus.COMPLETE,
            sent_mean=100.0,
            received_mean=100.0 + intrinsic,
            model_versions=("i1",),
        ),
    )


def _policies(evidence_through=AS_OF):
    return (
        CompetitiveMaterialityPolicy(
            expected_wins_abs=0.20,
            playoff_probability_abs=0.02,
            first_place_probability_abs=0.01,
            lineup_drop_abs=1.0,
            model_version="competitive-materiality-test-v1",
            evidence_through=evidence_through,
            provenance="synthetic test only",
        ),
        EconomicMaterialityPolicy(
            scale=SCALE,
            mean_value_abs=100.0,
            model_version="economic-materiality-test-v1",
            evidence_through=evidence_through,
            provenance="synthetic test only",
        ),
    )


def test_materiality_applies_explicit_policies_without_collapsing_channels() -> None:
    evaluation = BilateralTradeEvaluation(
        proposal_id="p1",
        side_a=TradeSideEvaluation(team_id="a", delta=_side_delta("a", 0.3, 0.01, 0.02, -1.5)),
        side_b=TradeSideEvaluation(team_id="b", delta=_side_delta("b", -0.3, -0.01, -0.02, 1.5)),
    )
    economic_net = BilateralTradeEconomicNet(
        proposal_id="p1",
        side_a=_economic("a", 150.0, -150.0),
        side_b=_economic("b", -150.0, 150.0),
    )
    competitive_policy, economic_policy = _policies()

    result = assess_bilateral_materiality(
        evaluation,
        economic_net,
        competitive_policy=competitive_policy,
        economic_policy=economic_policy,
    )

    assert result.side_a.expected_wins == MaterialityDirection.MATERIAL_GAIN
    assert result.side_a.playoff_probability == MaterialityDirection.IMMATERIAL
    assert result.side_a.first_place_probability == MaterialityDirection.MATERIAL_GAIN
    assert result.side_a.largest_single_player_lineup_drop == MaterialityDirection.MATERIAL_GAIN
    assert result.side_a.market_value == MaterialityDirection.MATERIAL_GAIN
    assert result.side_a.intrinsic_value == MaterialityDirection.MATERIAL_LOSS
    assert result.side_b.expected_wins == MaterialityDirection.MATERIAL_LOSS


def test_incomplete_economic_net_remains_unavailable() -> None:
    evaluation = BilateralTradeEvaluation(
        proposal_id="p1",
        side_a=TradeSideEvaluation(team_id="a", delta=_side_delta("a", 0.0, 0.0, 0.0, 0.0)),
        side_b=TradeSideEvaluation(team_id="b", delta=_side_delta("b", 0.0, 0.0, 0.0, 0.0)),
    )
    incomplete = ExpectedEconomicNetDelta(
        concept=EconomicConcept.MARKET_PRICE,
        status=EconomicNetStatus.INCOMPLETE,
        sent_mean=100.0,
        missing_asset_ids=("pick-1",),
    )
    unavailable = ExpectedEconomicNetDelta(
        concept=EconomicConcept.INTRINSIC_VALUE,
        status=EconomicNetStatus.UNAVAILABLE,
    )
    economic_net = BilateralTradeEconomicNet(
        proposal_id="p1",
        side_a=TradeLegEconomicNet(team_id="a", market=incomplete, intrinsic=unavailable),
        side_b=TradeLegEconomicNet(team_id="b", market=incomplete, intrinsic=unavailable),
    )
    competitive_policy, economic_policy = _policies()

    result = assess_bilateral_materiality(
        evaluation,
        economic_net,
        competitive_policy=competitive_policy,
        economic_policy=economic_policy,
    )

    assert result.side_a.market_value == MaterialityDirection.UNAVAILABLE
    assert result.side_a.intrinsic_value == MaterialityDirection.UNAVAILABLE


def test_future_materiality_policy_is_rejected() -> None:
    evaluation = BilateralTradeEvaluation(
        proposal_id="p1",
        side_a=TradeSideEvaluation(team_id="a", delta=_side_delta("a", 0.0, 0.0, 0.0, 0.0)),
        side_b=TradeSideEvaluation(team_id="b", delta=_side_delta("b", 0.0, 0.0, 0.0, 0.0)),
    )
    economic_net = BilateralTradeEconomicNet(
        proposal_id="p1",
        side_a=_economic("a", 0.0, 0.0),
        side_b=_economic("b", 0.0, 0.0),
    )
    competitive_policy, economic_policy = _policies(AS_OF + timedelta(seconds=1))

    with pytest.raises(ValueError, match="future evidence"):
        assess_bilateral_materiality(
            evaluation,
            economic_net,
            competitive_policy=competitive_policy,
            economic_policy=economic_policy,
        )
