from __future__ import annotations

from typing import Protocol

from pydantic import field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, Provenance, ProviderRef

from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation


class HistoricalProjectionSnapshot(FrozenModel):
    """Provider-neutral historical projection snapshot.

    `issued_at` is the time the projection was demonstrably available. `retrieved_at`
    is when FSFFL obtained the archived record and may be much later. Keeping both
    timestamps prevents archive retrieval time from being mistaken for forecast time.
    """

    provider: str
    external_id: str
    player_id: str
    position: Position
    horizon: ForecastHorizon
    metric: ForecastMetric
    period_start: object
    period_end: object
    mean: float
    stddev: float = 0.0
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    issued_at: object
    retrieved_at: object
    source_version: str | None = None

    @field_validator("period_start", "period_end", "issued_at", "retrieved_at")
    @classmethod
    def require_aware_datetime(cls, value: object) -> object:
        from datetime import datetime

        if not isinstance(value, datetime):
            raise TypeError("historical projection timestamps must be datetimes")
        if value.tzinfo is None:
            raise ValueError("historical projection timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_period(self) -> "HistoricalProjectionSnapshot":
        if self.period_end <= self.period_start:
            raise ValueError("projection period_end must be after period_start")
        if self.stddev < 0:
            raise ValueError("stddev cannot be negative")
        return self

    def to_observation(self) -> ForecastObservation:
        return ForecastObservation(
            player_id=self.player_id,
            position=self.position,
            horizon=self.horizon,
            metric=self.metric,
            period_start=self.period_start,
            period_end=self.period_end,
            distribution=ForecastDistribution(
                mean=self.mean,
                stddev=self.stddev,
                p10=self.p10,
                p50=self.p50,
                p90=self.p90,
            ),
            source=self.provider,
            model_version=self.source_version or "unknown",
            as_of=self.issued_at,
            provenance=Provenance(
                source=self.provider,
                retrieved_at=self.retrieved_at,
                effective_at=self.issued_at,
                provider_ref=ProviderRef(provider=self.provider, external_id=self.external_id),
                source_version=self.source_version,
            ),
        )


class HistoricalProjectionProvider(Protocol):
    """Adapter boundary for any historical projection dataset."""

    provider_name: str

    def load_snapshots(self) -> tuple[HistoricalProjectionSnapshot, ...]: ...


def normalize_historical_snapshots(
    snapshots: tuple[HistoricalProjectionSnapshot, ...],
) -> tuple[ForecastObservation, ...]:
    """Normalize archived provider records and reject exact duplicate revisions."""

    seen: set[tuple[object, ...]] = set()
    observations: list[ForecastObservation] = []
    for snapshot in snapshots:
        key = (
            snapshot.provider,
            snapshot.external_id,
            snapshot.player_id,
            snapshot.horizon,
            snapshot.metric,
            snapshot.period_start,
            snapshot.period_end,
            snapshot.issued_at,
        )
        if key in seen:
            raise ValueError("duplicate historical projection snapshot")
        seen.add(key)
        observations.append(snapshot.to_observation())

    return tuple(
        sorted(
            observations,
            key=lambda item: (
                item.as_of,
                item.source,
                item.player_id,
                item.horizon,
                item.metric,
                item.period_start,
            ),
        )
    )
