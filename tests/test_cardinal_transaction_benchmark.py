from datetime import UTC, datetime, timedelta

import pytest

from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_transaction_benchmark import (
    benchmark_cardinal_sources_against_one_for_one_trades,
)
from fsffl.value.transaction_evidence import OneForOneTradeObservation


BASE = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _native(source: str, scale: str, asset: str, value: float, when: datetime) -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset,
        source_id=source,
        native_scale_id=scale,
        value=value,
        observed_at=when,
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def _trade(a: str, b: str, when: datetime) -> OneForOneTradeObservation:
    return OneForOneTradeObservation(
        transaction_id=f"trade:{a}:{b}:{when.date()}",
        league_id="league-1",
        completed_at=when,
        asset_a_id=a,
        asset_b_id=b,
        source_id="sleeper",
    )


def test_cardinal_benchmark_uses_point_in_time_values_and_relative_gap() -> None:
    observations = (
        _native("source-a", "a-scale", "p1", 8000, BASE),
        _native("source-a", "a-scale", "p2", 7600, BASE),
        _native("source-a", "a-scale", "p1", 9900, BASE + timedelta(days=3)),
    )
    trade = _trade("p1", "p2", BASE + timedelta(days=1))

    result = benchmark_cardinal_sources_against_one_for_one_trades(
        observations,
        (trade,),
        market_context_id=CONTEXT,
    )
    row = result.source_results[0]

    assert row.evaluated_trades == 1
    assert row.mean_abs_value_gap == 400
    assert row.mean_abs_relative_gap == pytest.approx(400 / 7800)


def test_cardinal_benchmark_rejects_stale_snapshots() -> None:
    observations = (
        _native("source-a", "a-scale", "p1", 8000, BASE),
        _native("source-a", "a-scale", "p2", 8000, BASE),
    )
    trade = _trade("p1", "p2", BASE + timedelta(days=30))

    result = benchmark_cardinal_sources_against_one_for_one_trades(
        observations,
        (trade,),
        market_context_id=CONTEXT,
        max_snapshot_age_days=14,
    )

    assert result.source_results == ()
