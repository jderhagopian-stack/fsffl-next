from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import sqrt
from typing import Annotated

from pydantic import Field

from fsffl.state.models import FrozenModel

from .calibration import CalibrationEvidenceKind, CalibrationObservation, CalibrationPanel


class MarketSourceBenchmarkResult(FrozenModel):
    source_id: str
    sample_size: Annotated[int, Field(ge=1)]
    mean_absolute_error: Annotated[float, Field(ge=0)]
    root_mean_squared_error: Annotated[float, Field(ge=0)]
    mean_signed_error: float
    evidence_through: datetime


def benchmark_market_sources_against_transactions(
    panel: CalibrationPanel,
    *,
    transaction_metric: str = "transaction_price",
    market_metric: str = "market_value",
) -> tuple[MarketSourceBenchmarkResult, ...]:
    """Chronologically score market sources against later completed transactions.

    For each completed transaction, the benchmark selects the latest admissible
    market observation from each source for the same asset and format context at
    or before the transaction timestamp. Future market snapshots are never used.
    This is intentionally source-level diagnostic evidence, not promotion logic.
    """

    markets = [
        row
        for row in panel.observations
        if row.evidence_kind == CalibrationEvidenceKind.MARKET_VALUE
        and row.metric == market_metric
        and row.asset_id is not None
    ]
    transactions = [
        row
        for row in panel.observations
        if row.evidence_kind == CalibrationEvidenceKind.COMPLETED_TRANSACTION
        and row.metric == transaction_metric
        and row.asset_id is not None
    ]
    if not transactions:
        raise ValueError("benchmark requires completed transaction evidence")

    history: dict[tuple[str, str | None, str], list[CalibrationObservation]] = defaultdict(list)
    for row in markets:
        history[(row.asset_id, row.format_context_id, row.source_id)].append(row)
    for rows in history.values():
        rows.sort(key=lambda row: row.observed_at)

    errors: dict[str, list[tuple[float, datetime]]] = defaultdict(list)
    for trade in sorted(transactions, key=lambda row: row.observed_at):
        source_ids = {
            source_id
            for asset_id, format_context_id, source_id in history
            if asset_id == trade.asset_id and format_context_id == trade.format_context_id
        }
        for source_id in source_ids:
            candidates = history[(trade.asset_id, trade.format_context_id, source_id)]
            eligible = [row for row in candidates if row.observed_at <= trade.observed_at]
            if not eligible:
                continue
            prediction = eligible[-1]
            errors[source_id].append((prediction.value - trade.value, trade.observed_at))

    if not errors:
        raise ValueError("benchmark found no chronological market/transaction matches")

    results: list[MarketSourceBenchmarkResult] = []
    for source_id, source_errors in sorted(errors.items()):
        values = [error for error, _ in source_errors]
        results.append(
            MarketSourceBenchmarkResult(
                source_id=source_id,
                sample_size=len(values),
                mean_absolute_error=sum(abs(value) for value in values) / len(values),
                root_mean_squared_error=sqrt(
                    sum(value * value for value in values) / len(values)
                ),
                mean_signed_error=sum(values) / len(values),
                evidence_through=max(timestamp for _, timestamp in source_errors),
            )
        )
    return tuple(results)
