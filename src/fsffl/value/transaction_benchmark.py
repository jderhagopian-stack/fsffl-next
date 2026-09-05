from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean, median

from pydantic import Field

from fsffl.state.models import FrozenModel

from .calibration import CalibrationEvidenceKind, CalibrationObservation
from .transaction_evidence import OneForOneTradeObservation


class OneForOneSourceBenchmark(FrozenModel):
    source_id: str
    evaluated_trades: int = Field(ge=0)
    mean_abs_percentile_gap: float = Field(ge=0.0)
    median_abs_percentile_gap: float = Field(ge=0.0)


class OneForOneEnsembleBenchmark(FrozenModel):
    method: str
    minimum_sources: int = Field(ge=1)
    evaluated_trades: int = Field(ge=0)
    mean_abs_percentile_gap: float = Field(ge=0.0)
    median_abs_percentile_gap: float = Field(ge=0.0)


class OneForOneTradeBenchmarkResult(FrozenModel):
    source_results: tuple[OneForOneSourceBenchmark, ...]
    ensemble_result: OneForOneEnsembleBenchmark | None
    trades_seen: int = Field(ge=0)
    max_snapshot_age_days: int = Field(ge=0)
    compatible_context_ids: tuple[str, ...]


def benchmark_market_sources_against_one_for_one_trades(
    market_observations: tuple[CalibrationObservation, ...],
    trades: tuple[OneForOneTradeObservation, ...],
    *,
    compatible_context_ids: tuple[str, ...],
    max_snapshot_age_days: int = 14,
    ensemble_minimum_sources: int = 2,
) -> OneForOneTradeBenchmarkResult:
    """Score point-in-time market sources against clean player-for-player trades.

    A completed one-for-one trade is pairwise evidence: two managers accepted an
    exchange of one player for one player. It is not a scalar transaction price.
    For each source, this benchmark selects the latest admissible snapshot at or
    before the trade and measures the absolute percentile-rank gap between the
    exchanged players. Lower is better.

    The ensemble takes the median contemporaneous percentile rank for each asset
    across eligible sources. No future snapshot is ever used.
    """

    if max_snapshot_age_days < 0:
        raise ValueError("max_snapshot_age_days must be non-negative")
    if ensemble_minimum_sources < 1:
        raise ValueError("ensemble_minimum_sources must be positive")
    if not compatible_context_ids or any(not value.strip() for value in compatible_context_ids):
        raise ValueError("compatible_context_ids must be non-empty")

    market_rows = tuple(
        row
        for row in market_observations
        if row.evidence_kind == CalibrationEvidenceKind.MARKET_VALUE
        and row.metric == "market_value"
        and row.asset_id is not None
        and row.format_context_id in compatible_context_ids
    )

    snapshots: dict[str, dict[object, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in market_rows:
        assert row.asset_id is not None
        snapshot = snapshots[row.source_id][row.observed_at]
        prior = snapshot.get(row.asset_id)
        if prior is not None and prior != row.value:
            raise ValueError("conflicting market values within source snapshot")
        snapshot[row.asset_id] = row.value

    ranked_snapshots: dict[str, list[tuple[object, dict[str, float]]]] = {}
    for source_id, by_time in snapshots.items():
        ranked_snapshots[source_id] = [
            (observed_at, _percentile_ranks(values))
            for observed_at, values in sorted(by_time.items(), key=lambda item: item[0])
        ]

    gaps_by_source: dict[str, list[float]] = defaultdict(list)
    ensemble_gaps: list[float] = []
    max_age = timedelta(days=max_snapshot_age_days)

    for trade in trades:
        per_asset_a: list[float] = []
        per_asset_b: list[float] = []

        for source_id, source_snapshots in ranked_snapshots.items():
            selected: tuple[object, dict[str, float]] | None = None
            for observed_at, ranks in source_snapshots:
                if observed_at > trade.completed_at:
                    break
                if trade.completed_at - observed_at <= max_age:
                    selected = (observed_at, ranks)
            if selected is None:
                continue

            _, ranks = selected
            rank_a = ranks.get(trade.asset_a_id)
            rank_b = ranks.get(trade.asset_b_id)
            if rank_a is None or rank_b is None:
                continue
            gaps_by_source[source_id].append(abs(rank_a - rank_b))
            per_asset_a.append(rank_a)
            per_asset_b.append(rank_b)

        if len(per_asset_a) >= ensemble_minimum_sources:
            ensemble_gaps.append(abs(median(per_asset_a) - median(per_asset_b)))

    source_results = tuple(
        OneForOneSourceBenchmark(
            source_id=source_id,
            evaluated_trades=len(gaps),
            mean_abs_percentile_gap=mean(gaps),
            median_abs_percentile_gap=median(gaps),
        )
        for source_id, gaps in sorted(gaps_by_source.items())
        if gaps
    )
    ensemble_result = (
        OneForOneEnsembleBenchmark(
            method="median_percentile",
            minimum_sources=ensemble_minimum_sources,
            evaluated_trades=len(ensemble_gaps),
            mean_abs_percentile_gap=mean(ensemble_gaps),
            median_abs_percentile_gap=median(ensemble_gaps),
        )
        if ensemble_gaps
        else None
    )

    return OneForOneTradeBenchmarkResult(
        source_results=source_results,
        ensemble_result=ensemble_result,
        trades_seen=len(trades),
        max_snapshot_age_days=max_snapshot_age_days,
        compatible_context_ids=compatible_context_ids,
    )


def _percentile_ranks(values_by_asset: dict[str, float]) -> dict[str, float]:
    """Return ascending percentile ranks with average ranks for ties."""

    ordered = sorted(values_by_asset.items(), key=lambda item: (item[1], item[0]))
    if not ordered:
        return {}
    if len(ordered) == 1:
        return {ordered[0][0]: 0.5}

    result: dict[str, float] = {}
    index = 0
    denominator = len(ordered) - 1
    while index < len(ordered):
        end = index + 1
        value = ordered[index][1]
        while end < len(ordered) and ordered[end][1] == value:
            end += 1
        average_index = (index + end - 1) / 2.0
        percentile = average_index / denominator
        for asset_id, _ in ordered[index:end]:
            result[asset_id] = percentile
        index = end
    return result
