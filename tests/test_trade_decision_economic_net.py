import pytest

from fsffl.trade_decision.economic_net import EconomicNetStatus, calculate_bilateral_economic_net
from fsffl.trade_decision.economics import (
    BilateralTradeEconomics,
    EconomicConcept,
    ExpectedPackageValue,
    TradeLegEconomics,
)
from fsffl.value.models import ValueScale


SCALE = ValueScale(scale_id="dynasty", version="v1", unit_label="points")
OTHER_SCALE = ValueScale(scale_id="dynasty", version="v2", unit_label="points")


def _package(concept: EconomicConcept, mean: float, *, scale: ValueScale = SCALE, missing=()):
    return ExpectedPackageValue(
        concept=concept,
        mean_value=mean,
        scale=scale,
        included_asset_ids=("x",),
        missing_asset_ids=tuple(missing),
        model_versions=("m1",),
    )


def test_complete_market_and_intrinsic_nets_are_received_minus_sent() -> None:
    economics = BilateralTradeEconomics(
        proposal_id="p1",
        side_a=TradeLegEconomics(
            team_id="a",
            sent_market=_package(EconomicConcept.MARKET_PRICE, 100.0),
            received_market=_package(EconomicConcept.MARKET_PRICE, 130.0),
            sent_intrinsic=_package(EconomicConcept.INTRINSIC_VALUE, 90.0),
            received_intrinsic=_package(EconomicConcept.INTRINSIC_VALUE, 120.0),
        ),
        side_b=TradeLegEconomics(
            team_id="b",
            sent_market=_package(EconomicConcept.MARKET_PRICE, 130.0),
            received_market=_package(EconomicConcept.MARKET_PRICE, 100.0),
            sent_intrinsic=_package(EconomicConcept.INTRINSIC_VALUE, 120.0),
            received_intrinsic=_package(EconomicConcept.INTRINSIC_VALUE, 90.0),
        ),
    )

    result = calculate_bilateral_economic_net(economics)

    assert result.side_a.market.status == EconomicNetStatus.COMPLETE
    assert result.side_a.market.mean_delta == 30.0
    assert result.side_a.intrinsic.mean_delta == 30.0
    assert result.side_b.market.mean_delta == -30.0
    assert result.side_b.intrinsic.mean_delta == -30.0


def test_partial_package_evidence_never_emits_partial_net() -> None:
    economics = BilateralTradeEconomics(
        proposal_id="p1",
        side_a=TradeLegEconomics(
            team_id="a",
            sent_market=_package(EconomicConcept.MARKET_PRICE, 100.0, missing=("pick-1",)),
            received_market=_package(EconomicConcept.MARKET_PRICE, 120.0),
        ),
        side_b=TradeLegEconomics(team_id="b"),
    )

    result = calculate_bilateral_economic_net(economics)

    assert result.side_a.market.status == EconomicNetStatus.INCOMPLETE
    assert result.side_a.market.mean_delta is None
    assert result.side_a.market.missing_asset_ids == ("pick-1",)
    assert result.side_b.market.status == EconomicNetStatus.UNAVAILABLE


def test_net_fails_closed_on_incompatible_scales() -> None:
    economics = BilateralTradeEconomics(
        proposal_id="p1",
        side_a=TradeLegEconomics(
            team_id="a",
            sent_market=_package(EconomicConcept.MARKET_PRICE, 100.0, scale=SCALE),
            received_market=_package(EconomicConcept.MARKET_PRICE, 120.0, scale=OTHER_SCALE),
        ),
        side_b=TradeLegEconomics(team_id="b"),
    )

    with pytest.raises(ValueError, match="identical value scale"):
        calculate_bilateral_economic_net(economics)
