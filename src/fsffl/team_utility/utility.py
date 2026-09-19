from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.value.models import ValueDistribution, ValueScale

from .simulation import TeamCompetitiveOutcome


class CalculatedCompetitiveState(StrEnum):
    UNKNOWN = "unknown"
    REBUILDING = "rebuilding"
    DEVELOPING = "developing"
    COMPETITIVE = "competitive"
    CONTENDER = "contender"


class OwnerStrategicPosture(StrEnum):
    DEFAULT_CALCULATED = "default_calculated"
    WIN_NOW = "win_now"
    BALANCED = "balanced"
    RETOOL = "retool"
    REBUILD = "rebuild"


class RosterResilience(FrozenModel):
    """Team-specific roster consequence metrics, not market-value adjustments."""

    team_id: str
    starter_count: Annotated[int, Field(ge=0)]
    bench_forecasted_count: Annotated[int, Field(ge=0)]
    unavailable_count: Annotated[int, Field(ge=0)]
    missing_forecast_count: Annotated[int, Field(ge=0)]
    largest_single_player_lineup_drop: Annotated[float, Field(ge=0)] = 0.0
    model_version: str

    @model_validator(mode="after")
    def validate_identifiers(self) -> "RosterResilience":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("roster resilience identifiers cannot be blank")
        return self


class FranchiseAssetPortfolio(FrozenModel):
    """Economic portfolio evidence imported from NEXT-3 without reinterpretation."""

    team_id: str
    distribution: ValueDistribution
    scale: ValueScale
    value_concept: str
    value_model_versions: tuple[str, ...]

    @model_validator(mode="after")
    def validate_portfolio(self) -> "FranchiseAssetPortfolio":
        if not self.team_id.strip() or not self.value_concept.strip():
            raise ValueError("asset portfolio identifiers cannot be blank")
        if not self.value_model_versions or any(not value.strip() for value in self.value_model_versions):
            raise ValueError("asset portfolio must record value model versions")
        return self


class TeamUtilityVector(FrozenModel):
    """Non-collapsing authoritative inputs to franchise utility.

    NEXT-4 keeps competitive outcomes, asset economics and roster resilience as
    separate channels until an evidence-backed utility mapping explicitly combines
    them. Owner posture is intentionally not embedded in calculated state.
    """

    team_id: str
    as_of: datetime
    competitive_outcome: TeamCompetitiveOutcome | None = None
    calculated_competitive_state: CalculatedCompetitiveState = CalculatedCompetitiveState.UNKNOWN
    asset_portfolio: FranchiseAssetPortfolio | None = None
    roster_resilience: RosterResilience | None = None
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_vector(self) -> "TeamUtilityVector":
        if not self.team_id.strip() or not self.model_version.strip():
            raise ValueError("team utility identifiers cannot be blank")
        for component in (self.competitive_outcome, self.asset_portfolio, self.roster_resilience):
            if component is not None and component.team_id != self.team_id:
                raise ValueError("team utility components must describe the same team")
        return self


class StrategicTeamView(FrozenModel):
    """Explicit owner preference layered beside, not inside, calculated state."""

    calculated: TeamUtilityVector
    owner_posture: OwnerStrategicPosture = OwnerStrategicPosture.DEFAULT_CALCULATED
    posture_version: str = "owner-posture-v1"

    @model_validator(mode="after")
    def validate_posture(self) -> "StrategicTeamView":
        if not self.posture_version.strip():
            raise ValueError("posture_version cannot be blank")
        return self
