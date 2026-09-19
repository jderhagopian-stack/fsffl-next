from datetime import UTC, datetime

from fsffl.forecast.live_ensemble import LiveForecastSourceBatch, build_authoritative_live_ensemble
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import Position, Provenance


AS_OF = datetime(2026, 9, 5, 20, tzinfo=UTC)
START = datetime(2026, 9, 1, tzinfo=UTC)
END = datetime(2027, 3, 1, tzinfo=UTC)


def _obs(source: str, player_id: str, mean: float) -> ForecastObservation:
    effective = datetime(2026, 9, 4, 12, tzinfo=UTC)
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.PASS_YARDS,
        period_start=START,
        period_end=END,
        distribution=ForecastDistribution(mean=mean, stddev=0.0),
        source=source,
        model_version=f"{source}-v1",
        as_of=AS_OF,
        provenance=Provenance(source=source, retrieved_at=AS_OF, effective_at=effective),
    )


def test_single_source_player_group_is_not_promoted_even_when_feed_has_two_sources() -> None:
    first = LiveForecastSourceBatch(
        source_id="fftoday",
        observations=(_obs("fftoday", "p1", 4000.0), _obs("fftoday", "p2", 3500.0)),
    )
    second = LiveForecastSourceBatch(
        source_id="cbs",
        observations=(_obs("cbs", "p1", 4200.0),),
    )

    ensemble, coverage = build_authoritative_live_ensemble((first, second))

    assert [item.player_id for item in ensemble] == ["p1"]
    assert ensemble[0].distribution.mean == 4100.0
    assert coverage.excluded_undercovered_groups == 1
