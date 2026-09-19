from datetime import UTC, datetime

import pytest

from fsffl.trade_decision.economic_net import (
    BilateralTradeEconomicNet,
    EconomicNetStatus,
    ExpectedEconomicNetDelta,
    TradeLegEconomicNet,
)
from fsffl.trade_decision.economics import EconomicConcept
from fsffl.trade_decision.historical_economic_robustness import (
    HistoricalEconomicRobustnessStatus,
    HistoricalEconomicScenario,
    assess_historical_economic_robustness,
)
from fsffl.trade_decision.materiality import EconomicMaterialityPolicy, MaterialityDirection
from fsffl.value.models import ValueScale


SCALE = ValueScale(scale_id="dynasty", version="1", unit_label="units")
AS_OF = datetime(2026, 7, 11, tzinfo=UTC)
POLICY = EconomicMaterialityPolicy(
    scale=SCALE,
    mean_value_abs=100.0,
    model_version="materiality-v1",
    evidence_through=datetime(2026, 7, 1, tzinfo=UTC),
    provenance="historical threshold evidence",
)


def delta(concept: EconomicConcept, mean: float | None) -> ExpectedEconomicNetDelta:
    if mean is None:
        return ExpectedEconomicNetDelta(concept=concept, status=EconomicNetStatus.UNAVAILABLE)
    return ExpectedEconomicNetDelta(
        concept=concept,
        mean_delta=mean,
        scale=SCALE,
        status=EconomicNetStatus.COMPLETE,
        sent_mean=1000,
        received_mean=1000 + mean,
        model_versions=("value-v1",),
    )


def net(proposal_id: str, a: float | None, b: float | None) -> BilateralTradeEconomicNet:
    return BilateralTradeEconomicNet(
        proposal_id=proposal_id,
        side_a=TradeLegEconomicNet(
            team_id="A",
            market=delta(EconomicConcept.MARKET_PRICE, a),
            intrinsic=delta(EconomicConcept.INTRINSIC_VALUE, a),
        ),
        side_b=TradeLegEconomicNet(
            team_id="B",
            market=delta(EconomicConcept.MARKET_PRICE, b),
            intrinsic=delta(EconomicConcept.INTRINSIC_VALUE, b),
        ),
        model_version="net-v1",
    )


def scenario(name: str, a: float | None, b: float | None) -> HistoricalEconomicScenario:
    return HistoricalEconomicScenario(
        scenario_id=name,
        scenario_as_of=AS_OF,
        economic_net=net("trade", a, b),
    )


def test_additive_and_concentration_scenarios_are_robust_when_materiality_does_not_change():
    result = assess_historical_economic_robustness(
        (
            scenario("additive", 400, -400),
            scenario("concentration", 250, -250),
        ),
        policy=POLICY,
    )
    assert result.status == HistoricalEconomicRobustnessStatus.ROBUST
    assert result.scenario_shapes[0].side_a_intrinsic == MaterialityDirection.MATERIAL_GAIN
    assert result.scenario_shapes[1].side_a_intrinsic == MaterialityDirection.MATERIAL_GAIN


def test_package_treatment_is_sensitive_when_it_crosses_materiality_boundary():
    result = assess_historical_economic_robustness(
        (
            scenario("additive", 400, -400),
            scenario("concentration", 50, -50),
        ),
        policy=POLICY,
    )
    assert result.status == HistoricalEconomicRobustnessStatus.SENSITIVE
    assert result.scenario_shapes[1].side_a_intrinsic == MaterialityDirection.IMMATERIAL


def test_missing_economic_concept_yields_incomplete_not_false_robustness():
    result = assess_historical_economic_robustness(
        (
            scenario("additive", 400, -400),
            scenario("missing", None, None),
        ),
        policy=POLICY,
    )
    assert result.status == HistoricalEconomicRobustnessStatus.INCOMPLETE


def test_materiality_policy_cannot_postdate_historical_scenario():
    future_policy = POLICY.model_copy(update={"evidence_through": datetime(2026, 7, 12, tzinfo=UTC)})
    with pytest.raises(ValueError, match="unavailable"):
        assess_historical_economic_robustness((scenario("additive", 400, -400),), policy=future_policy)


def test_scenarios_must_describe_same_proposal():
    other = HistoricalEconomicScenario(
        scenario_id="other",
        scenario_as_of=AS_OF,
        economic_net=net("different-trade", 300, -300),
    )
    with pytest.raises(ValueError, match="one proposal"):
        assess_historical_economic_robustness((scenario("base", 400, -400), other), policy=POLICY)
