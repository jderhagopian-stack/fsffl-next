from __future__ import annotations

from datetime import datetime

from ..ingestion import HistoricalProjectionSnapshot
from .tabular import RawStatProjectionRow, snapshots_from_raw_stat_rows

FantasyProsProjectionRow = RawStatProjectionRow


def snapshots_from_fantasypros_rows(
    rows: tuple[FantasyProsProjectionRow, ...],
    *,
    period_start: datetime,
    period_end: datetime,
    issued_at: datetime,
    retrieved_at: datetime,
    source_version: str,
) -> tuple[HistoricalProjectionSnapshot, ...]:
    return snapshots_from_raw_stat_rows(
        rows,
        provider="fantasypros",
        period_start=period_start,
        period_end=period_end,
        issued_at=issued_at,
        retrieved_at=retrieved_at,
        source_version=source_version,
    )
