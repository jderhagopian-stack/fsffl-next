from datetime import UTC, datetime

from fsffl.forecast.adapters.fftoday import FFTodayProjectionRow, snapshots_from_fftoday_rows
from fsffl.forecast.models import ForecastMetric
from fsffl.state.models import Position


def test_fftoday_rows_expand_into_raw_stat_snapshots() -> None:
    rows = (
        FFTodayProjectionRow(
            external_id="patrick-mahomes",
            player_id="p1",
            position=Position.QB,
            stats={
                ForecastMetric.PASS_YARDS: 4720.0,
                ForecastMetric.PASS_TD: 38.0,
                ForecastMetric.INTERCEPTIONS: 12.0,
                ForecastMetric.RUSH_YARDS: 375.0,
                ForecastMetric.RUSH_TD: 3.0,
            },
        ),
    )
    issued = datetime(2023, 9, 7, tzinfo=UTC)
    snapshots = snapshots_from_fftoday_rows(
        rows,
        period_start=datetime(2023, 9, 7, tzinfo=UTC),
        period_end=datetime(2024, 1, 8, tzinfo=UTC),
        issued_at=issued,
        retrieved_at=datetime(2026, 9, 5, tzinfo=UTC),
        source_version="2023-09-07",
    )

    assert len(snapshots) == 5
    by_metric = {item.metric: item.mean for item in snapshots}
    assert by_metric[ForecastMetric.PASS_YARDS] == 4720.0
    assert by_metric[ForecastMetric.PASS_TD] == 38.0
    assert all(item.provider == "fftoday" for item in snapshots)
    assert all(item.issued_at == issued for item in snapshots)
