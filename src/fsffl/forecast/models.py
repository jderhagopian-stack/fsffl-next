from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator

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
