from datetime import UTC, datetime, timedelta

from fsffl.state.models import Position
from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_position_benchmark import (
    benchmark_cardinal_sources_by_position_against_one_for_one_trades,
)
from fsffl.value.transaction_evidence import OneForOneTradeObservation


BASE = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _value(source: str, scale: str, asset: str, value: float, day: int = 0) -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset,
        source_id=source,
        native_scale_id=scale,
        value=value,
        observed_at=BASE + timedelta(days=day),
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RESEARCH_ONLY,
    )


def _trade(transaction_id: str, asset_a: str, asset_b: str, day: int) -> OneForOneTradeObservation:
    return OneForOneTradeObservation(
        transaction_id=transaction_id,
        league_id="league",
        format_context_id=CONTEXT,
        completed_at=BASE + timedelta(days=day),
        roster_a_id=1,
        roster_b_id=2,
        asset_a_id=asset_a,
        asset_b_id=asset_b,
    )


def test_qb_cross_position_signed_gap_detects_source_underpricing() -> None:
    observations = (
        _value("source-low-qb", "low-scale", "qb1", 5000),
        _value("source-low-qb", "low-scale", "wr1", 8000),
        _value("source-balanced", "balanced-scale", "qb1", 7600),
        _value("source-balanced", "balanced-scale", "wr1", 7500),
    )
    result = benchmark_cardinal_sources_by_position_against_one_for_one_trades(
        observations,
        (_trade("t1", "qb1", "wr1", 2),),
        player_positions={"qb1": Position.QB, "wr1": Position.WR},
        market_context_id=CONTEXT,
    )

    by_source = {row.source_id: row for row in result.source_results}
    assert by_source["source-low-qb"].qb_relative_signed_gap is not None
    assert by_source["source-low-qb"].qb_relative_signed_gap < 0
    assert abs(by_source["source-balanced"].qb_relative_signed_gap) < abs(
        by_source["source-low-qb"].qb_relative_signed_gap
    )
    assert by_source["source-balanced"].mean_abs_relative_gap < by_source["source-low-qb"].mean_abs_relative_gap
    assert result.authority_effect == "research_only"


def test_qb_orientation_is_stable_regardless_of_trade_asset_order() -> None:
    observations = (
        _value("source", "scale", "qb1", 6000),
        _value("source", "scale", "rb1", 8000),
    )
    result = benchmark_cardinal_sources_by_position_against_one_for_one_trades(
        observations,
        (
            _trade("t1", "qb1", "rb1", 2),
            _trade("t2", "rb1", "qb1", 3),
        ),
        player_positions={"qb1": Position.QB, "rb1": Position.RB},
        market_context_id=CONTEXT,
    )

    row = result.source_results[0]
    assert row.evaluated_trades == 2
    assert row.qb_relative_signed_gap is not None
    assert row.qb_relative_signed_gap < 0


def test_benchmark_rejects_future_or_stale_market_snapshots() -> None:
    observations = (
        _value("source", "scale", "qb1", 6000, day=5),
        _value("source", "scale", "wr1", 6000, day=5),
    )
    result = benchmark_cardinal_sources_by_position_against_one_for_one_trades(
        observations,
        (_trade("t1", "qb1", "wr1", 2),),
        player_positions={"qb1": Position.QB, "wr1": Position.WR},
        market_context_id=CONTEXT,
    )
    assert result.source_results == ()
