from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.forecast.models import ForecastHorizon
from fsffl.state.models import FrozenModel, Position, RosterSlot


class LineupAssignment(FrozenModel):
    slot: RosterSlot
    slot_index: Annotated[int, Field(ge=1)]
    player_id: str
    position: Position
    expected_points: float

    @model_validator(mode="after")
    def validate_identifiers(self) -> "LineupAssignment":
        if not self.player_id.strip():
            raise ValueError("player_id cannot be blank")
        return self


class OptimizedTeamLineup(FrozenModel):
    team_id: str
    as_of: datetime
    horizon: ForecastHorizon
    assignments: tuple[LineupAssignment, ...]
    expected_points: float
    bench_player_ids: tuple[str, ...] = ()
    unavailable_player_ids: tuple[str, ...] = ()
    missing_forecast_player_ids: tuple[str, ...] = ()
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_lineup(self) -> "OptimizedTeamLineup":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("lineup identifiers cannot be blank")
        player_ids = [assignment.player_id for assignment in self.assignments]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("a player may occupy only one optimized lineup slot")
        slot_keys = [(assignment.slot, assignment.slot_index) for assignment in self.assignments]
        if len(slot_keys) != len(set(slot_keys)):
            raise ValueError("optimized lineup slots must be unique")
        return self


class MarginalLineupImpact(FrozenModel):
    team_id: str
    player_id: str
    as_of: datetime
    horizon: ForecastHorizon
    baseline_expected_points: float
    without_player_expected_points: float
    marginal_expected_points: Annotated[float, Field(ge=0)]
    replacement_player_ids: tuple[str, ...] = ()
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_impact(self) -> "MarginalLineupImpact":
        if not self.team_id.strip() or not self.player_id.strip() or not self.model_version.strip():
            raise ValueError("marginal impact identifiers cannot be blank")
        expected = self.baseline_expected_points - self.without_player_expected_points
        if abs(expected - self.marginal_expected_points) > 1e-9:
            raise ValueError("marginal_expected_points must equal baseline minus without-player points")
        return self
