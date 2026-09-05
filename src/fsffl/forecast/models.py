from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, Provenance


class ForecastHorizon(StrEnum):
    WEEK = "week"
    REST_OF_SEASON = "rest_of_season"
    SEASON = "season"
    MULTI_YEAR = "multi_year"


class ForecastMetric(StrEnum):
    FANTASY_POINTS = "fantasy_points"
    PASS_YARDS = "pass_yards"
    PASS_TD = "pass_td"
    INTERCEPTIONS = "interceptions"
    RUSH_YARDS = "rush_yards"
    RUSH_TD = "rush_td"
    RECEPTIONS = "receptions"
    REC_YARDS = "rec_yards"
    REC_TD = "rec_td"


class ForecastDistribution(FrozenModel):
    mean: float
    stddev: Annotated[float, Field(ge=0)]
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None

    @model_validator(mode="after")
    def validate_quantiles(self) -> "ForecastDistribution":
        supplied = [self.p10, self.p50, self.p90]
        concrete = [value for value in supplied if value is not None]
        if concrete != sorted(concrete):
            raise ValueError("forecast quantiles must be ordered p10 <= p50 <= p90")
        return self


class ForecastObservation(FrozenModel):
    player_id: str
    position: Position
    horizon: ForecastHorizon
    metric: ForecastMetric
    period_start: datetime
    period_end: datetime
    distribution: ForecastDistribution
    source: str
    model_version: str
    as_of: datetime
    provenance: Provenance

    @field_validator("period_start", "period_end", "as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("forecast timestamps must be timezone-aware")
        return value

    @field_validator("player_id", "source", "model_version")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("forecast identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_point_in_time_semantics(self) -> "ForecastObservation":
        if self.period_end <= self.period_start:
            raise ValueError("forecast period_end must be after period_start")
        if self.provenance.effective_at > self.as_of:
            raise ValueError("forecast evidence cannot postdate observation as_of")
        return self


class ForecastBundle(FrozenModel):
    player_id: str
    as_of: datetime
    observations: tuple[ForecastObservation, ...]
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_bundle_consistency(self) -> "ForecastBundle":
        for observation in self.observations:
            if observation.player_id != self.player_id:
                raise ValueError("bundle observations must match bundle player_id")
            if observation.as_of != self.as_of:
                raise ValueError("bundle observations must match bundle as_of")
        return self
