from datetime import UTC, datetime

import pytest

from fsffl.forecast.live_ensemble import (
    LiveForecastSourceBatch,
    LiveSourceRole,
    build_authoritative_live_ensemble,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


def _obs(source: str, mean: float) -> ForecastObservation:
    as_of = datetime(2026, 9, 5, tzinfo=UTC)
    return ForecastObservation(
        player_id="sleeper:player:1",
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.PASS_YARDS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 1, 10, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=100.0),
        source=source,
        model_version="provider-v1",
        as_of=as_of,
        provenance=Provenance(source=source, retrieved_at=as_of, effective_at=as_of),
    )


def test_live_ensemble_uses_existing_equal_weight_authority() -> None:
    ensemble, coverage = build_authoritative_live_ensemble(
        (
            LiveForecastSourceBatch(source_id="razzball", observations=(_obs("razzball", 4000.0),)),
            LiveForecastSourceBatch(source_id="fftoday", observations=(_obs("fftoday", 4200.0),)),
        )
    )
    assert len(ensemble) == 1
    assert ensemble[0].distribution.mean == pytest.approx(4100.0)
    assert ensemble[0].source == "fsffl:live_equal_weight"
    assert coverage.independent_source_ids == ("fftoday", "razzball")


def test_correlated_consensus_is_not_an_extra_vote() -> None:
    ensemble, coverage = build_authoritative_live_ensemble(
        (
            LiveForecastSourceBatch(source_id="cbs", observations=(_obs("cbs", 3900.0),)),
            LiveForecastSourceBatch(source_id="espn_mike_clay", observations=(_obs("espn_mike_clay", 4100.0),)),
            LiveForecastSourceBatch(source_id="fftoday", observations=(_obs("fftoday", 4200.0),)),
            LiveForecastSourceBatch(
                source_id="fantasypros",
                observations=(_obs("fantasypros", 4050.0),),
                role=LiveSourceRole.AGGREGATE,
                component_source_ids=("cbs", "espn_mike_clay", "fftoday"),
            ),
        )
    )
    assert ensemble[0].distribution.mean == pytest.approx((3900 + 4100 + 4200) / 3)
    assert coverage.excluded_aggregate_source_ids == ("fantasypros",)
    assert coverage.active_source_ids == ("cbs", "espn_mike_clay", "fftoday")


def test_live_ensemble_fails_closed_with_only_one_independent_source() -> None:
    with pytest.raises(ValueError, match="at least 2 independent sources"):
        build_authoritative_live_ensemble(
            (LiveForecastSourceBatch(source_id="razzball", observations=(_obs("razzball", 4000.0),)),)
        )
