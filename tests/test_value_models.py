from datetime import UTC, datetime

import pytest

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.value import (
    AssetValueProfile,
    ForecastValueInput,
    IntrinsicDynastyValueEstimate,
    MarketPriceEstimate,
    PickValueEstimate,
    TransactionDirection,
    TransactionPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
    comparable_values,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
MARKET_SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="market units")
INTRINSIC_SCALE = ValueScale(
    scale_id="intrinsic-dynasty",
    version="v1",
    unit_label="intrinsic units",
)


def test_value_distribution_requires_ordered_quantiles() -> None:
    with pytest.raises(ValueError):
        ValueDistribution(mean=100.0, stddev=10.0, p10=110.0, p50=100.0, p90=120.0)


def test_market_and_intrinsic_values_are_separate_types_and_scales() -> None:
    market = MarketPriceEstimate(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=80.0, stddev=8.0),
        scale=MARKET_SCALE,
        as_of=NOW,
        market_context_id="sf-half-ppr",
        model_version="market-v1",
        evidence_sources=("source-a", "source-b"),
    )
    intrinsic = IntrinsicDynastyValueEstimate(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=92.0, stddev=14.0),
        scale=INTRINSIC_SCALE,
        as_of=NOW,
        model_version="intrinsic-v1",
        conversion_model_version="forecast-economics-v1",
        forecast_model_versions=("next2-v1",),
    )

    profile = AssetValueProfile(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        market_price=market,
        intrinsic_value=intrinsic,
    )

    assert profile.market_price is market
    assert profile.intrinsic_value is intrinsic
    with pytest.raises(ValueError, match="same value scale"):
        comparable_values(
            market.distribution,
            market.scale,
            intrinsic.distribution,
            intrinsic.scale,
        )


def test_forecast_input_is_immutable_and_requires_point_in_time_timestamp() -> None:
    value_input = ForecastValueInput(
        player_id="player:1",
        horizon=ForecastHorizon.SEASON,
        distribution=ForecastDistribution(mean=250.0, stddev=35.0),
        forecast_model_version="next2-v1",
        forecast_as_of=NOW,
    )

    with pytest.raises(Exception):
        value_input.distribution = ForecastDistribution(mean=999.0, stddev=0.0)

    with pytest.raises(ValueError, match="timezone-aware"):
        ForecastValueInput(
            player_id="player:1",
            horizon=ForecastHorizon.SEASON,
            distribution=ForecastDistribution(mean=250.0, stddev=35.0),
            forecast_model_version="next2-v1",
            forecast_as_of=datetime(2026, 9, 5, 12, 0),
        )


def test_pick_value_cannot_be_attached_to_player_profile() -> None:
    pick_value = PickValueEstimate(
        asset_id="pick:2027:1",
        distribution=ValueDistribution(mean=75.0, stddev=25.0, p10=40.0, p50=70.0, p90=120.0),
        scale=INTRINSIC_SCALE,
        as_of=NOW,
        draft_season=2027,
        round=1,
        model_version="pick-v1",
        class_strength_model_version="class-v1",
        slot_uncertainty_model_version="slot-v1",
    )

    with pytest.raises(ValueError, match="pick_value"):
        AssetValueProfile(
            asset_id="pick:2027:1",
            asset_kind=ValueAssetKind.PLAYER,
            pick_value=pick_value,
        )


def test_transaction_price_direction_is_not_silently_swapped() -> None:
    sell = TransactionPriceEstimate(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        direction=TransactionDirection.SELL,
        distribution=ValueDistribution(mean=85.0, stddev=7.0),
        scale=MARKET_SCALE,
        as_of=NOW,
        market_context_id="sf-half-ppr",
        model_version="transaction-v1",
        liquidity_model_version="liquidity-v1",
    )

    with pytest.raises(ValueError, match="ACQUIRE"):
        AssetValueProfile(
            asset_id="player:1",
            asset_kind=ValueAssetKind.PLAYER,
            acquisition_price=sell,
        )
