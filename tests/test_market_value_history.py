from datetime import UTC, datetime, timedelta

import pytest

from fsffl.value.history import (
    MarketMovementStatus,
    MarketValueSnapshot,
    calculate_market_movement,
)
from fsffl.value.models import MarketPriceEstimate, ValueAssetKind, ValueDistribution, ValueScale


def _estimate(*, value: float, as_of: datetime, scale: ValueScale, context: str = "dynasty:12t:sf:0.5ppr") -> MarketPriceEstimate:
    return MarketPriceEstimate(
        asset_id="player:test",
        asset_kind=ValueAssetKind.PLAYER,
        distribution=ValueDistribution(mean=value),
        scale=scale,
        as_of=as_of,
        market_context_id=context,
        model_version="market-test-v1",
    )


def _snapshot(estimate: MarketPriceEstimate) -> MarketValueSnapshot:
    return MarketValueSnapshot(estimate=estimate, recorded_at=estimate.as_of + timedelta(minutes=5))


def test_30_day_market_movement_uses_nearest_real_same_scale_snapshot() -> None:
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    scale = ValueScale(scale_id="dynasty-market-percentile", version="next3-v1", unit_label="market percentile")
    current = _estimate(value=0.82, as_of=now, scale=scale)
    snapshots = (
        _snapshot(_estimate(value=0.71, as_of=now - timedelta(days=31), scale=scale)),
        _snapshot(_estimate(value=0.66, as_of=now - timedelta(days=45), scale=scale)),
    )

    movement = calculate_market_movement(current, snapshots, lookback_days=30, tolerance_days=5)

    assert movement.status == MarketMovementStatus.AVAILABLE
    assert movement.prior_as_of == now - timedelta(days=31)
    assert movement.current_value == pytest.approx(0.82)
    assert movement.prior_value == pytest.approx(0.71)
    assert movement.delta == pytest.approx(0.11)
    assert movement.scale == scale


def test_market_movement_fails_closed_without_real_snapshot_near_target() -> None:
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    scale = ValueScale(scale_id="dynasty-market-percentile", version="next3-v1", unit_label="market percentile")
    current = _estimate(value=0.82, as_of=now, scale=scale)
    snapshots = (_snapshot(_estimate(value=0.76, as_of=now - timedelta(days=10), scale=scale)),)

    movement = calculate_market_movement(current, snapshots, lookback_days=30, tolerance_days=5)

    assert movement.status == MarketMovementStatus.UNAVAILABLE
    assert movement.prior_as_of is None
    assert movement.prior_value is None
    assert movement.delta is None
    assert "No retained comparable market snapshot" in movement.unavailable_reason


def test_market_movement_never_crosses_value_scale_or_market_context() -> None:
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    current_scale = ValueScale(scale_id="dynasty-market-percentile", version="next3-v1", unit_label="market percentile")
    other_scale = ValueScale(scale_id="market-units", version="v1", unit_label="market units")
    current = _estimate(value=0.82, as_of=now, scale=current_scale)
    snapshots = (
        _snapshot(_estimate(value=7000, as_of=now - timedelta(days=30), scale=other_scale)),
        _snapshot(_estimate(value=0.71, as_of=now - timedelta(days=30), scale=current_scale, context="dynasty:10t:1qb:1ppr")),
    )

    movement = calculate_market_movement(current, snapshots, lookback_days=30, tolerance_days=1)

    assert movement.status == MarketMovementStatus.UNAVAILABLE
    assert movement.delta is None


def test_market_snapshot_rejects_recording_before_estimate_timestamp() -> None:
    now = datetime(2026, 9, 8, 12, tzinfo=UTC)
    scale = ValueScale(scale_id="dynasty-market-percentile", version="next3-v1", unit_label="market percentile")
    estimate = _estimate(value=0.82, as_of=now, scale=scale)

    with pytest.raises(ValueError, match="recorded_at cannot predate"):
        MarketValueSnapshot(estimate=estimate, recorded_at=now - timedelta(seconds=1))
