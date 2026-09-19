from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean, median
from typing import Mapping

from pydantic import Field

from fsffl.state.models import FrozenModel, Position

from .cardinal import NativeMarketMagnitudeObservation
from .transaction_evidence import OneForOneTradeObservation


class PositionPairCardinalBenchmark(FrozenModel):
    """Point-in-time source spacing for one position-pair trade cohort."""

    source_id: str
    native_scale_id: str
    position_a: Position
    position_b: Position
    evaluated_trades: int = Field(ge=0)
    mean_abs_relative_gap: float = Field(ge=0.0)
    median_abs_relative_gap: float = Field(ge=0.0)
    qb_relative_signed_gap: float | None = None


class PositionCardinalBenchmarkResult(FrozenModel):
    source_results: tuple[PositionPairCardinalBenchmark, ...]
    trades_seen: int = Field(ge=0)
    positioned_trades_seen: int = Field(ge=0)
    max_snapshot_age_days: int = Field(ge=0)
    market_context_id: str
    model_version: str = "next3-cardinal-position-transaction-benchmark-v1"
    authority_effect: str = "research_only"


def benchmark_cardinal_sources_by_position_against_one_for_one_trades(
    observations: tuple[NativeMarketMagnitudeObservation, ...],
    trades: tuple[OneForOneTradeObservation, ...],
    *,
    player_positions: Mapping[str, Position],
    market_context_id: str,
    max_snapshot_age_days: int = 14,
) -> PositionCardinalBenchmarkResult:
    """Benchmark market spacing against completed trades by position pair.

    Clean one-for-one completed trades are treated as approximate pairwise market
    equivalence evidence, never exact prices. For cross-position QB trades the
    signed metric is always oriented as ``QB value - non-QB value``. A persistent
    negative value therefore diagnoses QB underpricing on that source scale
    relative to the assets actually exchanged for QBs. No coefficient or Value
    authority is produced here.
    """

    if max_snapshot_age_days < 0:
        raise ValueError("max_snapshot_age_days must be non-negative")
    if not market_context_id.strip():
        raise ValueError("market_context_id cannot be blank")

    histories: dict[tuple[str, str], dict[str, list[NativeMarketMagnitudeObservation]]] = {}
    grouped: dict[tuple[str, str], list[NativeMarketMagnitudeObservation]] = defaultdict(list)
    for row in observations:
        if row.market_context_id == market_context_id:
            grouped[(row.source_id, row.native_scale_id)].append(row)
    for key, rows in grouped.items():
        by_asset: dict[str, list[NativeMarketMagnitudeObservation]] = defaultdict(list)
        for row in rows:
            by_asset[row.asset_id].append(row)
        for asset_rows in by_asset.values():
            asset_rows.sort(key=lambda item: item.observed_at)
        histories[key] = dict(by_asset)

    max_age = timedelta(days=max_snapshot_age_days)

    def latest_eligible(rows: list[NativeMarketMagnitudeObservation], completed_at):
        selected = None
        for row in rows:
            if row.observed_at > completed_at:
                break
            if completed_at - row.observed_at <= max_age:
                selected = row
        return selected

    relative_gaps: dict[tuple[str, str, Position, Position], list[float]] = defaultdict(list)
    qb_signed_gaps: dict[tuple[str, str, Position, Position], list[float]] = defaultdict(list)
    positioned = 0

    for trade in trades:
        if trade.format_context_id != market_context_id:
            continue
        position_a = player_positions.get(trade.asset_a_id)
        position_b = player_positions.get(trade.asset_b_id)
        if position_a is None or position_b is None:
            continue
        positioned += 1
        ordered_positions = tuple(sorted((position_a, position_b), key=lambda item: item.value))
        cohort_a, cohort_b = ordered_positions
        for (source_id, scale_id), by_asset in histories.items():
            rows_a = by_asset.get(trade.asset_a_id)
            rows_b = by_asset.get(trade.asset_b_id)
            if not rows_a or not rows_b:
                continue
            value_a = latest_eligible(rows_a, trade.completed_at)
            value_b = latest_eligible(rows_b, trade.completed_at)
            if value_a is None or value_b is None:
                continue
            midpoint = (abs(value_a.value) + abs(value_b.value)) / 2.0
            relative_gap = 0.0 if midpoint == 0 else abs(value_a.value - value_b.value) / midpoint
            key = (source_id, scale_id, cohort_a, cohort_b)
            relative_gaps[key].append(relative_gap)

            if position_a == Position.QB and position_b != Position.QB:
                denominator = midpoint or 1.0
                qb_signed_gaps[key].append((value_a.value - value_b.value) / denominator)
            elif position_b == Position.QB and position_a != Position.QB:
                denominator = midpoint or 1.0
                qb_signed_gaps[key].append((value_b.value - value_a.value) / denominator)

    results = []
    for key in sorted(relative_gaps, key=lambda item: (item[0], item[1], item[2].value, item[3].value)):
        source_id, scale_id, position_a, position_b = key
        gaps = relative_gaps[key]
        if not gaps:
            continue
        signed = qb_signed_gaps.get(key, [])
        results.append(
            PositionPairCardinalBenchmark(
                source_id=source_id,
                native_scale_id=scale_id,
                position_a=position_a,
                position_b=position_b,
                evaluated_trades=len(gaps),
                mean_abs_relative_gap=mean(gaps),
                median_abs_relative_gap=median(gaps),
                qb_relative_signed_gap=mean(signed) if signed else None,
            )
        )

    return PositionCardinalBenchmarkResult(
        source_results=tuple(results),
        trades_seen=sum(1 for trade in trades if trade.format_context_id == market_context_id),
        positioned_trades_seen=positioned,
        max_snapshot_age_days=max_snapshot_age_days,
        market_context_id=market_context_id,
    )
