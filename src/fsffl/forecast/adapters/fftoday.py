from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fsffl.state.models import Position

from ..ingestion import HistoricalProjectionSnapshot
from ..models import ForecastHorizon, ForecastMetric


@dataclass(frozen=True)
class FFTodayProjectionRow:
    external_id: str
    player_id: str
    position: Position
    stats: dict[ForecastMetric, float]


def snapshots_from_fftoday_rows(
    rows: tuple[FFTodayProjectionRow, ...],
    *,
    period_start: datetime,
    period_end: datetime,
    issued_at: datetime,
    retrieved_at: datetime,
    source_version: str,
) -> tuple[HistoricalProjectionSnapshot, ...]:
    """Normalize an extracted FFToday historical table into canonical snapshots.

    Acquisition/parsing is intentionally kept outside the core model so archived
    HTML or retained tables can be supplied without creating a live-provider
    dependency. Each football statistic becomes an independent canonical metric;
    FFToday's fantasy-point column is not required for league-agnostic scoring.
    """

    snapshots: list[HistoricalProjectionSnapshot] = []
    for row in rows:
        for metric, value in row.stats.items():
            snapshots.append(
                HistoricalProjectionSnapshot(
                    provider="fftoday",
                    external_id=row.external_id,
                    player_id=row.player_id,
                    position=row.position,
                    horizon=ForecastHorizon.SEASON,
                    metric=metric,
                    period_start=period_start,
                    period_end=period_end,
                    mean=float(value),
                    issued_at=issued_at,
                    retrieved_at=retrieved_at,
                    source_version=source_version,
                )
            )

    return tuple(snapshots)
