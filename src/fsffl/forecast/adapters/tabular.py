from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fsffl.state.models import Position

from ..ingestion import HistoricalProjectionSnapshot
from ..models import ForecastHorizon, ForecastMetric


@dataclass(frozen=True)
class RawStatProjectionRow:
    external_id: str
    player_id: str
    position: Position
    stats: dict[ForecastMetric, float]


def snapshots_from_raw_stat_rows(
    rows: tuple[RawStatProjectionRow, ...],
    *,
    provider: str,
    period_start: datetime,
    period_end: datetime,
    issued_at: datetime,
    retrieved_at: datetime,
    source_version: str,
) -> tuple[HistoricalProjectionSnapshot, ...]:
    """Normalize provider-extracted raw stat rows into canonical season snapshots.

    Provider-specific HTML/CSV parsing remains outside the forecast core. This
    shared conversion path ensures ESPN, FantasyPros, FFToday and later sources
    all reach the benchmark through the same canonical statistical interface.
    """
    if not provider.strip():
        raise ValueError("provider cannot be empty")

    snapshots: list[HistoricalProjectionSnapshot] = []
    for row in rows:
        for metric, value in row.stats.items():
            snapshots.append(
                HistoricalProjectionSnapshot(
                    provider=provider,
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
