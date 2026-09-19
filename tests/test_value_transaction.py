from datetime import UTC, datetime

import pytest

from fsffl.value import (
    MarketPriceEstimate,
    TransactionDirection,
    TransactionPriceMapping,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
    estimate_transaction_price,
)


NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
SCALE = ValueScale(scale_id="market-index", version="v1", unit_label="market units")


def market_price(*, as_of=NOW, context="sf-half-ppr") -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id="player:1",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(
            mean=100.0,
            stddev=8.0,
            p10=88.0,
            p50=100.0,
            p90=112.0,
        ),
        scale=SCALE,
        as_of=as_of,
        market_context_id=context,
        model_version="market-v1",
        evidence_sources=("a", "b", "c"),
    )


def test_transaction_price_uses_explicit_directional_calibration() -> None:
    mapping = TransactionPriceMapping(
        acquire_offset=6.0,
        sell_offset=-4.0,
        model_version="liquidity-v1",
        evidence_through_season=2025,
        sample_size=250,
        market_context_id="sf-half-ppr",
    )

    acquire = estimate_transaction_price(
        market_price(),
        mapping,
        direction=TransactionDirection.ACQUIRE,
        as_of=NOW,
        model_version="transaction-v1",
    )
    sell = estimate_transaction_price(
        market_price(),
        mapping,
        direction=TransactionDirection.SELL,
        as_of=NOW,
        model_version="transaction-v1",
    )

    assert acquire.distribution.mean == 106.0
    assert acquire.distribution.p10 == 94.0
    assert sell.distribution.mean == 96.0
    assert sell.distribution.p90 == 108.0
    assert acquire.liquidity_model_version == "liquidity-v1"


def test_residual_transaction_uncertainty_is_propagated_without_fake_quantiles() -> None:
    mapping = TransactionPriceMapping(
        acquire_offset=5.0,
        sell_offset=-5.0,
        residual_stddev=6.0,
        model_version="liquidity-v1",
        evidence_through_season=2025,
        sample_size=250,
    )

    estimate = estimate_transaction_price(
        market_price(),
        mapping,
        direction=TransactionDirection.ACQUIRE,
        as_of=NOW,
        model_version="transaction-v1",
    )

    assert estimate.distribution.stddev == 10.0
    assert estimate.distribution.p10 is None
    assert estimate.distribution.p50 is None
    assert estimate.distribution.p90 is None


def test_transaction_price_rejects_future_market_evidence() -> None:
    future = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
    mapping = TransactionPriceMapping(
        acquire_offset=1.0,
        sell_offset=-1.0,
        model_version="liquidity-v1",
        evidence_through_season=2025,
        sample_size=10,
    )

    with pytest.raises(ValueError, match="after as_of"):
        estimate_transaction_price(
            market_price(as_of=future),
            mapping,
            direction=TransactionDirection.ACQUIRE,
            as_of=NOW,
            model_version="transaction-v1",
        )


def test_transaction_price_rejects_wrong_market_context() -> None:
    mapping = TransactionPriceMapping(
        acquire_offset=1.0,
        sell_offset=-1.0,
        model_version="liquidity-v1",
        evidence_through_season=2025,
        sample_size=10,
        market_context_id="1qb-full-ppr",
    )

    with pytest.raises(ValueError, match="different market context"):
        estimate_transaction_price(
            market_price(),
            mapping,
            direction=TransactionDirection.SELL,
            as_of=NOW,
            model_version="transaction-v1",
        )
