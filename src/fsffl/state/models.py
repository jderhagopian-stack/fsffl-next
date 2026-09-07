from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProviderRef(FrozenModel):
    provider: str
    external_id: str


class Provenance(FrozenModel):
    source: str
    retrieved_at: datetime
    effective_at: datetime
    provider_ref: ProviderRef | None = None
    source_version: str | None = None

    @field_validator("retrieved_at", "effective_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class Position(StrEnum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    K = "K"
    DST = "DST"


class RosterSlot(StrEnum):
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    FLEX = "FLEX"
    SUPERFLEX = "SUPERFLEX"
    K = "K"
    DST = "DST"
    BENCH = "BENCH"
    TAXI = "TAXI"
    IR = "IR"


class ScoringRule(FrozenModel):
    stat: str
    points: float


class LineupRequirement(FrozenModel):
    slot: RosterSlot
    count: Annotated[int, Field(ge=0)]


class LeagueRules(FrozenModel):
    team_count: Annotated[int, Field(ge=2)]
    roster_size: Annotated[int, Field(ge=1)]
    taxi_size: Annotated[int, Field(ge=0)] = 0
    ir_size: Annotated[int, Field(ge=0)] = 0
    rookie_draft_rounds: Annotated[int, Field(ge=0)] = 0
    playoff_team_count: Annotated[int, Field(ge=1)] | None = None
    fantasy_regular_season_end_week: Annotated[int, Field(ge=1, le=18)] | None = None
    lineup: tuple[LineupRequirement, ...]
    scoring: tuple[ScoringRule, ...]

    @model_validator(mode="after")
    def validate_playoff_count(self) -> "LeagueRules":
        if self.playoff_team_count is not None and self.playoff_team_count > self.team_count:
            raise ValueError("playoff_team_count cannot exceed team_count")
        return self


class League(FrozenModel):
    league_id: str
    name: str
    season: int
    rules: LeagueRules
    provider_refs: tuple[ProviderRef, ...] = ()


class Team(FrozenModel):
    team_id: str
    league_id: str
    display_name: str
    provider_refs: tuple[ProviderRef, ...] = ()


class Player(FrozenModel):
    player_id: str
    full_name: str
    position: Position
    nfl_team: str | None = None
    provider_refs: tuple[ProviderRef, ...] = ()


class PlayerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INJURED = "injured"
    PUP = "pup"
    SUSPENDED = "suspended"
    FREE_AGENT = "free_agent"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class PlayerState(FrozenModel):
    player_id: str
    as_of: datetime
    age_years: float | None = Field(default=None, ge=0)
    nfl_team: str | None = None
    status: PlayerStatus = PlayerStatus.UNKNOWN
    provenance: Provenance

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class NflTeamBye(FrozenModel):
    """Canonical scheduled NFL bye-week fact for one team and season."""

    season: Annotated[int, Field(ge=2000)]
    nfl_team: str
    week: Annotated[int, Field(ge=1, le=18)]
    provenance: Provenance

    @field_validator("nfl_team")
    @classmethod
    def normalize_team(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("nfl_team cannot be blank")
        return normalized


class DraftPick(FrozenModel):
    pick_id: str
    league_id: str
    season: int
    round: Annotated[int, Field(ge=1)]
    original_team_id: str


class PickOwnership(FrozenModel):
    pick_id: str
    owner_team_id: str


class PlayerAsset(FrozenModel):
    kind: Literal["player"] = "player"
    player_id: str


class PickAsset(FrozenModel):
    kind: Literal["pick"] = "pick"
    pick_id: str


class FaabAsset(FrozenModel):
    kind: Literal["faab"] = "faab"
    amount: Annotated[int, Field(gt=0)]


Asset = Annotated[PlayerAsset | PickAsset | FaabAsset, Field(discriminator="kind")]
