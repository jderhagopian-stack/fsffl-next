from datetime import UTC, datetime

from fsffl.forecast.backtest import RealizedOutcome
from fsffl.forecast.calibration import evaluate_uncertainty_calibration
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.state.models import Position, Provenance


PERIOD_START = datetime(2024, 9, 5, tzinfo=UTC)
PERIOD_END = datetime(2025, 1, 6, tzinfo=UTC)


def _observation(
    *, player_id: str, mean: float, stddev: float, p10: float, p90: float
) -> ForecastObservation:
    issued = datetime(2024, 8, 15, tzinfo=UTC)
    return ForecastObservation(
        player_id=player_id,
        position=Position.WR,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        distribution=ForecastDistribution(
            mean=mean, stddev=stddev, p10=p10, p90=p90
        ),
        source="provider:test",
        model_version="1",
        as_of=issued,
        provenance=Provenance(
            source="provider:test",
            retrieved_at=issued,
            effective_at=issued,
        ),
    )


def _outcome(player_id: str, actual: float) -> RealizedOutcome:
    finalized = datetime(2025, 1, 7, tzinfo=UTC)
    return RealizedOutcome(
        player_id=player_id,
        position=Position.WR,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        actual=actual,
        finalized_at=finalized,
        provenance=Provenance(
            source="outcomes:test",
            retrieved_at=finalized,
            effective_at=PERIOD_END,
        ),
    )


def test_uncertainty_calibration_reports_standardized_error_and_interval_coverage() -> None:
    observations = (
        _observation(player_id="p1", mean=100.0, stddev=10.0, p10=80.0, p90=120.0),
        _observation(player_id="p2", mean=100.0, stddev=10.0, p10=90.0, p90=110.0),
    )
    outcomes = (_outcome("p1", 110.0), _outcome("p2", 120.0))

    result = evaluate_uncertainty_calibration(observations, outcomes)[0]

    assert result.sample_size == 2
    assert round(result.standardized_rmse or 0.0, 6) == round((2.5) ** 0.5, 6)
    assert result.p10_p90_coverage == 0.5
