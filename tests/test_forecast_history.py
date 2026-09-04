from datetime import UTC, datetime, timedelta

from fsffl.forecast.history import InMemoryForecastStore
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


def _observation(*, as_of: datetime, mean: float) -> ForecastObservation:
    start = datetime(2026, 9, 10, tzinfo=UTC)
    end = datetime(2027, 1, 5, tzinfo=UTC)
    return ForecastObservation(
        player_id="player-1",
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=start,
        period_end=end,
        distribution=ForecastDistribution(mean=mean, stddev=20.0),
        source="provider:test",
        model_version="1",
        as_of=as_of,
        provenance=Provenance(source="provider:test"),
    )


def test_store_uses_latest_snapshot_available_by_cutoff() -> None:
    first_time = datetime(2026, 8, 1, tzinfo=UTC)
    second_time = datetime(2026, 8, 15, tzinfo=UTC)
    store = InMemoryForecastStore()
    store.save((_observation(as_of=first_time, mean=200.0), _observation(as_of=second_time, mean=220.0)))

    result = store.latest(
        player_id="player-1",
        source="provider:test",
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 10, tzinfo=UTC),
        period_end=datetime(2027, 1, 5, tzinfo=UTC),
        as_of=first_time + timedelta(days=7),
    )

    assert result is not None
    assert result.distribution.mean == 200.0


def test_store_never_substitutes_future_snapshot() -> None:
    forecast_time = datetime(2026, 8, 15, tzinfo=UTC)
    store = InMemoryForecastStore()
    store.save((_observation(as_of=forecast_time, mean=220.0),))

    result = store.latest(
        player_id="player-1",
        source="provider:test",
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 10, tzinfo=UTC),
        period_end=datetime(2027, 1, 5, tzinfo=UTC),
        as_of=forecast_time - timedelta(seconds=1),
    )

    assert result is None
