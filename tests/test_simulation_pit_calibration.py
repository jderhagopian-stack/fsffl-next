from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.team_utility.simulation_validation import (
    ContinuousCalibrationObservation,
    PITCalibrationTarget,
    PITSimulationCheckpoint,
    ProbabilityCalibrationObservation,
    score_continuous_calibration,
    score_probability_calibration,
)


CUTOFF = datetime(2026, 9, 10, 23, 0, tzinfo=UTC)


def _checkpoint(**updates) -> PITSimulationCheckpoint:
    payload = {
        "checkpoint_id": "fsffl-preseason-2026",
        "league_id": "sleeper:league",
        "season": 2026,
        "cutoff": CUTOFF,
        "state_id": "state-1",
        "state_as_of": CUTOFF - timedelta(minutes=5),
        "forecast_id": "forecast-1",
        "forecast_effective_at": CUTOFF - timedelta(hours=2),
        "forecast_retrieved_at": CUTOFF - timedelta(minutes=10),
    }
    payload.update(updates)
    return PITSimulationCheckpoint(**payload)


@pytest.mark.parametrize(
    ("field", "message"),
    (
        ("state_as_of", "State snapshot postdates"),
        ("forecast_effective_at", "Forecast effective time postdates"),
        ("forecast_retrieved_at", "Forecast retrieval postdates"),
    ),
)
def test_checkpoint_rejects_future_input_evidence(field: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _checkpoint(**{field: CUTOFF + timedelta(seconds=1)})


def test_probability_calibration_scores_only_post_cutoff_realizations() -> None:
    checkpoint = _checkpoint()
    observations = (
        ProbabilityCalibrationObservation(
            checkpoint_id=checkpoint.checkpoint_id,
            target=PITCalibrationTarget.PLAYOFF_PROBABILITY,
            entity_id="team-a",
            predicted_probability=0.75,
            actual=1,
            realized_at=CUTOFF + timedelta(days=100),
        ),
        ProbabilityCalibrationObservation(
            checkpoint_id=checkpoint.checkpoint_id,
            target=PITCalibrationTarget.PLAYOFF_PROBABILITY,
            entity_id="team-b",
            predicted_probability=0.25,
            actual=0,
            realized_at=CUTOFF + timedelta(days=100),
        ),
    )

    summary = score_probability_calibration((checkpoint,), observations)[0]

    assert summary.sample_size == 2
    assert summary.checkpoint_count == 1
    assert summary.mean_predicted_probability == pytest.approx(0.5)
    assert summary.observed_rate == pytest.approx(0.5)
    assert summary.calibration_bias == pytest.approx(0.0)
    assert summary.brier_score == pytest.approx(0.0625)

    with pytest.raises(ValueError, match="must postdate PIT cutoff"):
        score_probability_calibration(
            (checkpoint,),
            (
                observations[0].model_copy(
                    update={"realized_at": CUTOFF}
                ),
            ),
        )


def test_continuous_calibration_reports_error_without_reconstructing_forecasts() -> None:
    checkpoint = _checkpoint()
    observations = (
        ContinuousCalibrationObservation(
            checkpoint_id=checkpoint.checkpoint_id,
            target=PITCalibrationTarget.EXPECTED_WINS,
            entity_id="team-a",
            predicted=9.0,
            actual=10.0,
            realized_at=CUTOFF + timedelta(days=100),
        ),
        ContinuousCalibrationObservation(
            checkpoint_id=checkpoint.checkpoint_id,
            target=PITCalibrationTarget.EXPECTED_WINS,
            entity_id="team-b",
            predicted=7.0,
            actual=6.0,
            realized_at=CUTOFF + timedelta(days=100),
        ),
    )

    summary = score_continuous_calibration((checkpoint,), observations)[0]

    assert summary.sample_size == 2
    assert summary.mean_error == pytest.approx(0.0)
    assert summary.mean_absolute_error == pytest.approx(1.0)
    assert summary.root_mean_squared_error == pytest.approx(1.0)


def test_duplicate_checkpoint_entity_target_is_rejected() -> None:
    checkpoint = _checkpoint()
    row = ProbabilityCalibrationObservation(
        checkpoint_id=checkpoint.checkpoint_id,
        target=PITCalibrationTarget.CHAMPIONSHIP_PROBABILITY,
        entity_id="team-a",
        predicted_probability=0.2,
        actual=0,
        realized_at=CUTOFF + timedelta(days=120),
    )

    with pytest.raises(ValueError, match="duplicate probability"):
        score_probability_calibration((checkpoint,), (row, row))


def test_unknown_checkpoint_is_rejected() -> None:
    checkpoint = _checkpoint()
    row = ContinuousCalibrationObservation(
        checkpoint_id="missing",
        target=PITCalibrationTarget.TEAM_SCORE,
        entity_id="team-a-week-1",
        predicted=120.0,
        actual=115.0,
        realized_at=CUTOFF + timedelta(days=1),
    )

    with pytest.raises(ValueError, match="unknown checkpoint"):
        score_continuous_calibration((checkpoint,), (row,))
