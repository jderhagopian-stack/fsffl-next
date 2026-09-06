from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean, median

from pydantic import Field

from fsffl.state.models import FrozenModel

from .cardinal import NativeMarketMagnitudeObservation
from .transaction_evidence import OneForOneTradeObservation


class CardinalOneForOneSourceBenchmark(FrozenModel):
    source_id: str
    native_scale_id: str
    evaluated_trades: int = Field(ge=0)
    mean_abs_value_gap: float = Field(ge=0.0)
    median_abs_value_gap: float = Field(ge=0.0)
    mean_abs_relative_gap: float = Field(ge=0.0)
    median_abs_relative_gap: float = Field(ge=0.0)


class CardinalOneForOneBenchmarkResult(FrozenModel):
    source_results: tuple[CardinalOneForOneSourceBenchmark, ...]
    trades_seen: int = Field(ge=0)
    max_snapshot_age_days: int = Field(ge=0)
    market_context_id: str


def benchmark_cardinal_sources_against_one_for_one_trades(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
    trades: tuple[OneForOneTradeObservation, ...],
    *,
    market_context_id: str,
    max_snapshot_age_days: int = 14,
) -> CardinalOneForOneBenchmarkResult:
    """Evaluate provider-native cardinal spacing against clean 1-for-1 trades.

    A completed 1-for-1 trade is pairwise revealed-preference evidence, not an
    exact scalar clearing price. For each source this benchmark selects the latest
    admissible point-in-time values at or before the completed trade and measures
    the absolute cardinal gap between the exchanged assets. It also reports a
    scale-free relative gap using the pair midpoint as denominator, so sources
    with different native units can be compared without pretending their raw
    units are interchangeable.

    This is challenger evidence only. It does not promote a source or define the
    FSFFL Value Score by itself.
    """

    if max_snapshot_age_days < 0:
        raise ValueError("max_snapshot_age_days must be non-negative")
    if not market_context_id.strip():
        raise ValueError("market_context_id cannot be blank")

    grouped: dict[tuple[str, str], list[NativeMarketMagnitudeObservation]] = defaultdict(list)
    for row in observations:
        if row.market_context_id != market_context_id:
            continue
        grouped[(row.source_id, row.native_scale_id)].append(row)

    histories: dict[tuple[str, str], dict[str, list[NativeMarketMagnitudeObservation]]] = {}
    for key, rows in grouped.items():
        by_asset: dict[str, list[NativeMarketMagnitudeObservation]] = defaultdict(list)
        for row in rows:
            by_asset[row.asset_id].append(row)
        for asset_rows in by_asset.values():
            asset_rows.sort(key=lambda item: item.observed_at)
        histories[key] = dict(by_asset)

    max_age = timedelta(days=max_snapshot_age_days)
    absolute_by_source: dict[tuple[str, str], list[float]] = defaultdict(list)
    relative_by_source: dict[tuple[str, str], list[float]] = defaultdict(list)

    def latest_eligible(
        rows: list[NativeMarketMagnitudeObservation], completed_at
    ) -> NativeMarketMagnitudeObservation | None:
        selected = None
        for row in rows:
            if row.observed_at > completed_at:
                break
            if completed_at - row.observed_at <= max_age:
                selected = row
        return selected

    for trade in trades:
        for key, by_asset in histories.items():
            rows_a = by_asset.get(trade.asset_a_id)
            rows_b = by_asset.get(trade.asset_b_id)
            if not rows_a or not rows_b:
                continue
            value_a = latest_eligible(rows_a, trade.completed_at)
            value_b = latest_eligible(rows_b, trade.completed_at)
            if value_a is None or value_b is None:
                continue
            gap = abs(value_a.value - value_b.value)
            midpoint = (abs(value_a.value) + abs(value_b.value)) / 2.0
            relative_gap = 0.0 if midpoint == 0 else gap / midpoint
            absolute_by_source[key].append(gap)
            relative_by_source[key].append(relative_gap)

    results = tuple(
        CardinalOneForOneSourceBenchmark(
            source_id=source_id,
            native_scale_id=scale_id,
            evaluated_trades=len(absolute_by_source[(source_id, scale_id)]),
            mean_abs_value_gap=mean(absolute_by_source[(source_id, scale_id)]),
            median_abs_value_gap=median(absolute_by_source[(source_id, scale_id)]),
            mean_abs_relative_gap=mean(relative_by_source[(source_id, scale_id)]),
            median_abs_relative_gap=median(relative_by_source[(source_id, scale_id)]),
        )
        for source_id, scale_id in sorted(absolute_by_source)
        if absolute_by_source[(source_id, scale_id)]
    )

    return CardinalOneForOneBenchmarkResult(
        source_results=results,
        trades_seen=len(trades),
        max_snapshot_age_days=max_snapshot_age_days,
        market_context_id=market_context_id,
    )
