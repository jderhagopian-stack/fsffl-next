from datetime import UTC, datetime

import pytest

from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset
from fsffl.trade_decision import (
    BilateralTradeProposal,
    EconomicConcept,
    EconomicFlow,
    TradeLeg,
    summarize_bilateral_trade_economics,
)
from fsffl.value.models import (
    AssetValueProfile,
    IntrinsicDynastyValueEstimate,
    MarketPriceEstimate,
    TransactionDirection,
    TransactionPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
)

AS_OF = datetime(2026, 9, 5, 17, 30, tzinfo=UTC)
SCALE = ValueScale(scale_id="dynasty", version="1", unit_label="points")


def _player_profile(asset_id: str, *, market: float, intrinsic: float) -> AssetValueProfile:
    return AssetValueProfile(
        asset_id=asset_id,
        asset_kind=ValueAssetKind.PLAYER,
        market_price=MarketPriceEstimate(
            asset_id=asset_id,
            asset_kind=ValueAssetKind.PLAYER,
            distribution=ValueDistribution(mean=market),
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="league",
            model_version="market-v1",
        ),
        intrinsic_value=IntrinsicDynastyValueEstimate(
            asset_id=asset_id,
            asset_kind=ValueAssetKind.PLAYER,
            distribution=ValueDistribution(mean=intrinsic),
            scale=SCALE,
            as_of=AS_OF,
            model_version="intrinsic-v1",
            conversion_model_version="conversion-v1",
        ),
        acquisition_price=TransactionPriceEstimate(
            asset_id=asset_id,
            asset_kind=ValueAssetKind.PLAYER,
            direction=TransactionDirection.ACQUIRE,
            distribution=ValueDistribution(mean=market + 1.0),
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="league",
            model_version="tx-v1",
            liquidity_model_version="liq-v1",
        ),
        sale_price=TransactionPriceEstimate(
            asset_id=asset_id,
            asset_kind=ValueAssetKind.PLAYER,
            direction=TransactionDirection.SELL,
            distribution=ValueDistribution(mean=market - 1.0),
            scale=SCALE,
            as_of=AS_OF,
            market_context_id="league",
            model_version="tx-v1",
            liquidity_model_version="liq-v1",
        ),
    )


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="econ",
        as_of=AS_OF,
        side_a=TradeLeg(
            team_id="A",
            sends=(PlayerAsset(player_id="p1"), FaabAsset(amount=5)),
        ),
        side_b=TradeLeg(
            team_id="B",
            sends=(PlayerAsset(player_id="p2"), PickAsset(pick_id="pick:x")),
        ),
    )


def test_economics_preserve_distinct_concepts_and_sum_expected_means_only() -> None:
    result = summarize_bilateral_trade_economics(
        _proposal(),
        {
            "p1": _player_profile("p1", market=10.0, intrinsic=12.0),
            "p2": _player_profile("p2", market=20.0, intrinsic=18.0),
        },
    )

    assert result.side_a.sent_market is not None
    assert result.side_a.sent_intrinsic is not None
    assert result.side_a.received_market is not None
    assert result.side_a.received_acquisition_price is not None
    assert result.side_a.sent_market.mean_value == 10.0
    assert result.side_a.sent_intrinsic.mean_value == 12.0
    assert result.side_a.received_market.mean_value == 20.0
    assert result.side_a.received_acquisition_price.mean_value == 21.0

    # Missing FAAB/pick evidence stays visible rather than becoming zero.
    missing = {(item.asset_id, item.concept, item.flow) for item in result.side_a.missing_evidence}
    assert ("faab:5", EconomicConcept.MARKET_PRICE, EconomicFlow.SENT) in missing
    assert ("pick:x", EconomicConcept.MARKET_PRICE, EconomicFlow.RECEIVED) in missing


def test_package_scale_mismatch_fails_closed() -> None:
    other_scale = ValueScale(scale_id="other", version="1", unit_label="units")
    p3 = _player_profile("p3", market=5.0, intrinsic=6.0)
    p3 = p3.model_copy(
        update={
            "market_price": p3.market_price.model_copy(update={"scale": other_scale})
        }
    )
    proposal = BilateralTradeProposal(
        proposal_id="scale-mismatch",
        as_of=AS_OF,
        side_a=TradeLeg(
            team_id="A",
            sends=(PlayerAsset(player_id="p1"), PlayerAsset(player_id="p3")),
        ),
        side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
    )

    with pytest.raises(ValueError, match="incompatible value scales"):
        summarize_bilateral_trade_economics(
            proposal,
            {
                "p1": _player_profile("p1", market=10.0, intrinsic=12.0),
                "p2": _player_profile("p2", market=20.0, intrinsic=18.0),
                "p3": p3,
            },
        )
