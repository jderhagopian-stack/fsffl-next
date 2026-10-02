from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from math import sqrt

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


class PITCalibrationTarget(StrEnum):
    EXPECTED_WINS = "expected_wins"
    EXPECTED_FINISH = "expected_finish"
    PLAYOFF_PROBABILITY = "playoff_probability"
    CHAMPIONSHIP_PROBABILITY = "championship_probability"
    BYE_PROBABILITY = "bye_probability"
    FIRST_PLACE_PROBABILITY = "first_place_probability"
    PICK_SLOT_PROBABILITY = "pick_slot_probability"
    TEAM_SCORE = "team_score"


class PITSimulationCheckpoint(FrozenModel):
    """Leakage-safe Simulation calibration input identity.

    A checkpoint is eligible only when both canonical State and Forecast evidence
    were knowable no later than the declared cutoff. Realized outcomes are attached
    separately and may only be scored after the cutoff.
    """

    checkpoint_id: str
    league_id: str
    season: int = Field(ge=2000)
    cutoff: datetime
    state_id: str
    state_as_of: datetime
    forecast_id: str
    forecast_effective_at: datetime
    forecast_retrieved_at: datetime
    evidence_class: str = "authentic_timestamped"

    @field_validator(
        "cutoff",
        "state_as_of",
        "forecast_effective_at",
        "forecast_retrieved_at",
    )
    @classmethod
    def require_aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("PIT calibration timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator(
        "checkpoint_id",
        "league_id",
        "state_id",
        "forecast_id",
        "evidence_class",
    )
    @classmethod
    def require_nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("PIT calibration identifiers cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_no_future_inputs(self) -> "PITSimulationCheckpoint":
        if self.state_as_of > self.cutoff:
            raise ValueError("PIT State snapshot postdates calibration cutoff")
        if self.forecast_effective_at > self.cutoff:
            raise ValueError("PIT Forecast effective time postdates calibration cutoff")
        if self.forecast_retrieved_at > self.cutoff:
            raise ValueError("PIT Forecast retrieval postdates calibration cutoff")
        if self.forecast_effective_at > self.forecast_retrieved_at:
            raise ValueError("Forecast effective time cannot postdate retrieval")
        return self


class ProbabilityCalibrationObservation(FrozenModel):
    checkpoint_id: str
    target: PITCalibrationTarget
    entity_id: str
    predicted_probability: float = Field(ge=0.0, le=1.0)
    actual: int = Field(ge=0, le=1)
    realized_at: datetime

    @field_validator("realized_at")
    @classmethod
    def require_aware_realized_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("realized_at must be timezone-aware")
        return value.astimezone(UTC)


class ContinuousCalibrationObservation(FrozenModel):
    checkpoint_id: str
    target: PITCalibrationTarget
    entity_id: str
    predicted: float
    actual: float
    realized_at: datetime

    @field_validator("realized_at")
    @classmethod
    def require_aware_realized_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("realized_at must be timezone-aware")
        return value.astimezone(UTC)


class ProbabilityCalibrationSummary(FrozenModel):
    target: PITCalibrationTarget
    sample_size: int = Field(ge=1)
    checkpoint_count: int = Field(ge=1)
    mean_predicted_probability: float = Field(ge=0.0, le=1.0)
    observed_rate: float = Field(ge=0.0, le=1.0)
    calibration_bias: float
    brier_score: float = Field(ge=0.0, le=1.0)


class ContinuousCalibrationSummary(FrozenModel):
    target: PITCalibrationTarget
    sample_size: int = Field(ge=1)
    checkpoint_count: int = Field(ge=1)
    mean_error: float
    mean_absolute_error: float = Field(ge=0.0)
    root_mean_squared_error: float = Field(ge=0.0)


def _checkpoint_map(
    checkpoints: tuple[PITSimulationCheckpoint, ...],
) -> dict[str, PITSimulationCheckpoint]:
    mapped = {item.checkpoint_id: item for item in checkpoints}
    if len(mapped) != len(checkpoints):
        raise ValueError("duplicate PIT calibration checkpoint id")
    return mapped


def _validate_observation_time(
    checkpoint: PITSimulationCheckpoint,
    *,
    realized_at: datetime,
) -> None:
    if realized_at <= checkpoint.cutoff:
        raise ValueError("realized calibration outcome must postdate PIT cutoff")


def score_probability_calibration(
    checkpoints: tuple[PITSimulationCheckpoint, ...],
    observations: tuple[ProbabilityCalibrationObservation, ...],
) -> tuple[ProbabilityCalibrationSummary, ...]:
    mapped = _checkpoint_map(checkpoints)
    grouped: dict[PITCalibrationTarget, list[ProbabilityCalibrationObservation]] = {}
    seen: set[tuple[str, PITCalibrationTarget, str]] = set()
    for row in observations:
        checkpoint = mapped.get(row.checkpoint_id)
        if checkpoint is None:
            raise ValueError("calibration observation references unknown checkpoint")
        _validate_observation_time(checkpoint, realized_at=row.realized_at)
        key = (row.checkpoint_id, row.target, row.entity_id)
        if key in seen:
            raise ValueError("duplicate probability calibration observation")
        seen.add(key)
        grouped.setdefault(row.target, []).append(row)

    summaries: list[ProbabilityCalibrationSummary] = []
    for target, rows in grouped.items():
        n = len(rows)
        predicted = sum(row.predicted_probability for row in rows) / n
        observed = sum(row.actual for row in rows) / n
        brier = sum(
            (row.predicted_probability - row.actual) ** 2 for row in rows
        ) / n
        summaries.append(
            ProbabilityCalibrationSummary(
                target=target,
                sample_size=n,
                checkpoint_count=len({row.checkpoint_id for row in rows}),
                mean_predicted_probability=predicted,
                observed_rate=observed,
                calibration_bias=predicted - observed,
                brier_score=brier,
            )
        )
    return tuple(sorted(summaries, key=lambda item: item.target.value))


def score_continuous_calibration(
    checkpoints: tuple[PITSimulationCheckpoint, ...],
    observations: tuple[ContinuousCalibrationObservation, ...],
) -> tuple[ContinuousCalibrationSummary, ...]:
    mapped = _checkpoint_map(checkpoints)
    grouped: dict[PITCalibrationTarget, list[ContinuousCalibrationObservation]] = {}
    seen: set[tuple[str, PITCalibrationTarget, str]] = set()
    for row in observations:
        checkpoint = mapped.get(row.checkpoint_id)
        if checkpoint is None:
            raise ValueError("calibration observation references unknown checkpoint")
        _validate_observation_time(checkpoint, realized_at=row.realized_at)
        key = (row.checkpoint_id, row.target, row.entity_id)
        if key in seen:
            raise ValueError("duplicate continuous calibration observation")
        seen.add(key)
        grouped.setdefault(row.target, []).append(row)

    summaries: list[ContinuousCalibrationSummary] = []
    for target, rows in grouped.items():
        errors = [row.predicted - row.actual for row in rows]
        n = len(errors)
        summaries.append(
            ContinuousCalibrationSummary(
                target=target,
                sample_size=n,
                checkpoint_count=len({row.checkpoint_id for row in rows}),
                mean_error=sum(errors) / n,
                mean_absolute_error=sum(abs(value) for value in errors) / n,
                root_mean_squared_error=sqrt(
                    sum(value * value for value in errors) / n
                ),
            )
        )
    return tuple(sorted(summaries, key=lambda item: item.target.value))
