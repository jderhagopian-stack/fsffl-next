from datetime import UTC, datetime

from fsffl.forecast.adapters import (
    ESPNProjectionRow,
    FantasyProsProjectionRow,
    snapshots_from_espn_rows,
    snapshots_from_fantasypros_rows,
)
from fsffl.forecast.models import ForecastMetric
from fsffl.state.models import Position


PERIOD_START = datetime(2025, 9, 4, tzinfo=UTC)
PERIOD_END = datetime(2026, 1, 5, tzinfo=UTC)
ISSUED = datetime(2025, 8, 20, tzinfo=UTC)
RETRIEVED = datetime(2026, 9, 5, tzinfo=UTC)


def _stats():
    return {
        ForecastMetric.PASS_YARDS: 4400.0,
        ForecastMetric.PASS_TD: 34.0,
        ForecastMetric.INTERCEPTIONS: 11.0,
        ForecastMetric.RUSH_YARDS: 350.0,
        ForecastMetric.RUSH_TD: 4.0,
    }


def test_espn_rows_use_shared_canonical_stat_path() -> None:
    rows = (
        ESPNProjectionRow(
            external_id="espn-1",
            player_id="p1",
            position=Position.QB,
            stats=_stats(),
        ),
    )
    snapshots = snapshots_from_espn_rows(
        rows,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        issued_at=ISSUED,
        retrieved_at=RETRIEVED,
        source_version="2025-preseason",
    )
    assert len(snapshots) == 5
    assert {item.provider for item in snapshots} == {"espn_mike_clay"}
    assert {item.metric for item in snapshots} == set(_stats())


def test_fantasypros_rows_use_shared_canonical_stat_path() -> None:
    rows = (
        FantasyProsProjectionRow(
            external_id="fp-1",
            player_id="p1",
            position=Position.QB,
            stats=_stats(),
        ),
    )
    snapshots = snapshots_from_fantasypros_rows(
        rows,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        issued_at=ISSUED,
        retrieved_at=RETRIEVED,
        source_version="2025-preseason",
    )
    assert len(snapshots) == 5
    assert {item.provider for item in snapshots} == {"fantasypros"}
    assert all(item.issued_at == ISSUED for item in snapshots)
