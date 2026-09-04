from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
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
    lineup: tuple[LineupRequirement, ...]
    scoring: tuple[ScoringRule, ...]


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


class RosterEntry(FrozenModel):
    player_id: str
    slot: RosterSlot


class TeamState(FrozenModel):
    team_id: str
    roster: tuple[RosterEntry, ...]
    faab_balance: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def unique_player_entries(self) -> "TeamState":
        ids = [entry.player_id for entry in self.roster]
        if len(ids) != len(set(ids)):
            raise ValueError("a player may appear only once on a team roster")
        return self


class TransactionSide(FrozenModel):
    team_id: str
    assets: tuple[Asset, ...]


class Transaction(FrozenModel):
    transaction_id: str
    effective_at: datetime
    sides: tuple[TransactionSide, ...]
    provenance: Provenance

    @field_validator("effective_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("effective_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def at_least_two_sides(self) -> "Transaction":
        if len(self.sides) < 2:
            raise ValueError("transactions require at least two team sides")
        return self


class LeagueState(FrozenModel):
    schema_version: str = "1"
    league: League
    as_of: datetime
    teams: tuple[Team, ...]
    team_states: tuple[TeamState, ...]
    players: tuple[Player, ...]
    player_states: tuple[PlayerState, ...]
    draft_picks: tuple[DraftPick, ...] = ()
    pick_ownership: tuple[PickOwnership, ...] = ()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("as_of")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_references(self) -> "LeagueState":
        team_ids = {team.team_id for team in self.teams}
        player_ids = {player.player_id for player in self.players}
        pick_ids = {pick.pick_id for pick in self.draft_picks}

        if any(team.league_id != self.league.league_id for team in self.teams):
            raise ValueError("all teams must belong to the league")
        if {state.team_id for state in self.team_states} != team_ids:
            raise ValueError("team_states must contain exactly one state for each team")
        if {state.player_id for state in self.player_states} != player_ids:
            raise ValueError("player_states must contain exactly one state for each player")
        if any(entry.player_id not in player_ids for state in self.team_states for entry in state.roster):
            raise ValueError("roster contains unknown player")
        roster_ids = [entry.player_id for state in self.team_states for entry in state.roster]
        if len(roster_ids) != len(set(roster_ids)):
            raise ValueError("a player may not be rostered by multiple teams")
        if any(ownership.pick_id not in pick_ids for ownership in self.pick_ownership):
            raise ValueError("pick ownership references unknown pick")
        if any(ownership.owner_team_id not in team_ids for ownership in self.pick_ownership):
            raise ValueError("pick ownership references unknown team")
        if len({ownership.pick_id for ownership in self.pick_ownership}) != len(self.pick_ownership):
            raise ValueError("a draft pick may have only one owner")
        return self

    def canonical_json(self) -> str:
        return self.model_dump_json(exclude_none=False, by_alias=True)

    @property
    def state_id(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()
