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


class LeagueMatchup(FrozenModel):
    """Canonical point-in-time fantasy-league matchup state."""

    week: Annotated[int, Field(ge=1)]
    team_a_id: str
    team_b_id: str
    team_a_points: float | None = None
    team_b_points: float | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def validate_matchup(self) -> "LeagueMatchup":
        if not self.team_a_id.strip() or not self.team_b_id.strip():
            raise ValueError("matchup team ids cannot be blank")
        if self.team_a_id == self.team_b_id:
            raise ValueError("a team cannot play itself")
        if (self.team_a_points is None) != (self.team_b_points is None):
            raise ValueError("matchup points must be present for both teams or neither")
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
    matchups: tuple[LeagueMatchup, ...] = ()
    nfl_team_byes: tuple[NflTeamBye, ...] = ()
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

        if len(team_ids) != len(self.teams):
            raise ValueError("team_id values must be unique")
        if len(player_ids) != len(self.players):
            raise ValueError("player_id values must be unique")
        if len(pick_ids) != len(self.draft_picks):
            raise ValueError("pick_id values must be unique")
        if any(team.league_id != self.league.league_id for team in self.teams):
            raise ValueError("all teams must belong to the league")
        if {state.team_id for state in self.team_states} != team_ids or len(self.team_states) != len(team_ids):
            raise ValueError("team_states must contain exactly one state for each team")
        if {state.player_id for state in self.player_states} != player_ids or len(self.player_states) != len(player_ids):
            raise ValueError("player_states must contain exactly one state for each player")
        if any(entry.player_id not in player_ids for state in self.team_states for entry in state.roster):
            raise ValueError("roster contains unknown player")
        roster_ids = [entry.player_id for state in self.team_states for entry in state.roster]
        if len(roster_ids) != len(set(roster_ids)):
            raise ValueError("a player may not be rostered by multiple teams")
        if any(pick.league_id != self.league.league_id for pick in self.draft_picks):
            raise ValueError("all draft picks must belong to the league")
        if any(pick.original_team_id not in team_ids for pick in self.draft_picks):
            raise ValueError("draft pick references unknown original team")
        if any(ownership.pick_id not in pick_ids for ownership in self.pick_ownership):
            raise ValueError("pick ownership references unknown pick")
        if any(ownership.owner_team_id not in team_ids for ownership in self.pick_ownership):
            raise ValueError("pick ownership references unknown team")
        if len({ownership.pick_id for ownership in self.pick_ownership}) != len(self.pick_ownership):
            raise ValueError("a draft pick may have only one owner")
        if any(matchup.team_a_id not in team_ids or matchup.team_b_id not in team_ids for matchup in self.matchups):
            raise ValueError("matchup references unknown team")
        matchup_keys = [
            (matchup.week, *sorted((matchup.team_a_id, matchup.team_b_id)))
            for matchup in self.matchups
        ]
        if len(matchup_keys) != len(set(matchup_keys)):
            raise ValueError("duplicate matchup in same week")
        seen_week_team: set[tuple[int, str]] = set()
        for matchup in self.matchups:
            for team_id in (matchup.team_a_id, matchup.team_b_id):
                key = (matchup.week, team_id)
                if key in seen_week_team:
                    raise ValueError("a team may appear only once per matchup week")
                seen_week_team.add(key)
        bye_keys = [(bye.season, bye.nfl_team) for bye in self.nfl_team_byes]
        if len(bye_keys) != len(set(bye_keys)):
            raise ValueError("an NFL team may have only one bye week per season")
        if any(bye.season != self.league.season for bye in self.nfl_team_byes):
            raise ValueError("NFL bye state must match league season")
        return self

    def canonical_json(self) -> str:
        from .serialization import canonical_state_json

        return canonical_state_json(self)

    @property
    def state_id(self) -> str:
        from .serialization import deterministic_state_id

        return deterministic_state_id(self)
