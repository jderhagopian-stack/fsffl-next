from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_NFL_TEAM_ALIASES = {
    "JAC": "JAX",
    "LA": "LAR",
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LAR",
    "WSH": "WAS",
}


def canonical_nfl_team(value: str) -> str:
    """Return the canonical NFL team abbreviation used across point-in-time State."""

    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("nfl_team cannot be blank")
    return _NFL_TEAM_ALIASES.get(normalized, normalized)


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


DraftOrderParameterValue = str | int | float | bool


class DraftOrderPolicyParameter(FrozenModel):
    """One explicit, serializable input to a league draft-order policy."""

    name: str
    value: DraftOrderParameterValue

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("draft-order policy parameter name cannot be blank")
        return value.strip()


class DraftOrderPolicyEvidence(FrozenModel):
    """Point-in-time governed evidence for one league's draft-order rule."""

    league_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    effective_at: datetime
    available_at: datetime
    policy_id: str
    version: str
    mechanism: str
    description: str
    parameters: tuple[DraftOrderPolicyParameter, ...] = ()
    provenance: Provenance

    @field_validator("effective_at", "available_at")
    @classmethod
    def require_policy_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("draft-order policy timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> "DraftOrderPolicyEvidence":
        for value in (
            self.league_id,
            self.policy_id,
            self.version,
            self.mechanism,
            self.description,
        ):
            if not value.strip():
                raise ValueError(
                    "draft-order policy identifiers and description cannot be blank"
                )
        names = [item.name for item in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("draft-order policy parameter names must be unique")
        return self


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


class PlayoffParticipantRef(FrozenModel):
    """Canonical bracket input: an original seed or a prior game's winner."""

    seed_number: Annotated[int, Field(ge=1)] | None = None
    winner_of_matchup_id: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> "PlayoffParticipantRef":
        if (self.seed_number is None) == (self.winner_of_matchup_id is None):
            raise ValueError("playoff participant must identify exactly one seed or prior winner")
        if self.winner_of_matchup_id is not None and not self.winner_of_matchup_id.strip():
            raise ValueError("winner_of_matchup_id cannot be blank")
        return self


class PlayoffMatchupRule(FrozenModel):
    matchup_id: str
    round_number: Annotated[int, Field(ge=1)]
    week: Annotated[int, Field(ge=1, le=22)]
    participant_a: PlayoffParticipantRef
    participant_b: PlayoffParticipantRef


class LeaguePlayoffRules(FrozenModel):
    """Provider-neutral, point-in-time postseason structure for one league.

    The contract can retain rules that the current kernel does not yet execute.
    Such rules remain explicit but produce no bracket/championship estimate until
    the Simulation engine supports every material behavior named here.
    """

    playoff_team_count: Annotated[int, Field(ge=2)]
    playoff_start_week: Annotated[int, Field(ge=1, le=22)]
    round_count: Annotated[int, Field(ge=1)]
    round_weeks: tuple[Annotated[int, Field(ge=1, le=22)], ...]
    bye_count: Annotated[int, Field(ge=0)]
    bye_seeds: tuple[Annotated[int, Field(ge=1)], ...]
    seeding_policy: str | None = None
    standings_tiebreak_policy: str | None = None
    reseeding_policy: str | None = None
    bracket_authority: Literal["provider_observed_exact", "settings_derived_standard"] = "provider_observed_exact"
    bracket_derivation_policy: str | None = None
    matchups: tuple[PlayoffMatchupRule, ...] = ()
    championship_round_number: Annotated[int, Field(ge=1)]
    championship_week: Annotated[int, Field(ge=1, le=22)]
    championship_matchup_id: str
    playoff_scoring_policy: str | None = None
    matchup_tiebreak_policy: str | None = None

    def effective_matchups(self) -> tuple[PlayoffMatchupRule, ...]:
        """Return the observed graph or compile an explicitly governed standard."""
        if self.matchups:
            return self.matchups
        if self.bracket_authority != "settings_derived_standard" or self.bracket_derivation_policy != "seeded_standard_fixed_v1":
            return ()
        if len(self.round_weeks) != self.round_count or not self.round_weeks:
            return ()
        def seed(n: int) -> PlayoffParticipantRef:
            return PlayoffParticipantRef(seed_number=n)
        def winner(key: str) -> PlayoffParticipantRef:
            return PlayoffParticipantRef(winner_of_matchup_id=key)
        def game(key: str, rnd: int, a: PlayoffParticipantRef, b: PlayoffParticipantRef) -> PlayoffMatchupRule:
            return PlayoffMatchupRule(matchup_id=key, round_number=rnd, week=self.round_weeks[rnd - 1], participant_a=a, participant_b=b)
        # Standard fixed seeded conventions. League size, weeks and bye seeds remain governed inputs.
        if self.playoff_team_count == 2 and not self.bye_seeds and self.round_count == 1:
            return (game(self.championship_matchup_id, 1, seed(1), seed(2)),)
        if self.playoff_team_count == 4 and not self.bye_seeds and self.round_count == 2:
            return (game("semi-a", 1, seed(1), seed(4)), game("semi-b", 1, seed(2), seed(3)), game(self.championship_matchup_id, 2, winner("semi-a"), winner("semi-b")))
        if self.playoff_team_count == 6 and set(self.bye_seeds) == {1, 2} and self.round_count == 3:
            return (game("qf-a", 1, seed(3), seed(6)), game("qf-b", 1, seed(4), seed(5)), game("sf-a", 2, seed(1), winner("qf-b")), game("sf-b", 2, seed(2), winner("qf-a")), game(self.championship_matchup_id, 3, winner("sf-a"), winner("sf-b")))
        if self.playoff_team_count == 8 and not self.bye_seeds and self.round_count == 3:
            return (game("qf-a", 1, seed(1), seed(8)), game("qf-b", 1, seed(4), seed(5)), game("qf-c", 1, seed(2), seed(7)), game("qf-d", 1, seed(3), seed(6)), game("sf-a", 2, winner("qf-a"), winner("qf-b")), game("sf-b", 2, winner("qf-c"), winner("qf-d")), game(self.championship_matchup_id, 3, winner("sf-a"), winner("sf-b")))
        return ()

    def canonical_execution_matchups(self) -> tuple[PlayoffMatchupRule, ...]:
        """Order games and sides structurally, independent of provider matchup IDs."""
        matchups = self.effective_matchups()
        by_id = {row.matchup_id: row for row in matchups}
        participant_cache: dict[tuple[str, int | str], tuple] = {}
        matchup_cache: dict[str, tuple] = {}

        def participant_key(reference: PlayoffParticipantRef) -> tuple:
            if reference.seed_number is not None:
                return (0, reference.seed_number)
            matchup_id = reference.winner_of_matchup_id
            if matchup_id not in participant_cache:
                participant_cache[matchup_id] = (1, matchup_key(by_id[matchup_id]))
            return participant_cache[matchup_id]

        def matchup_key(matchup: PlayoffMatchupRule) -> tuple:
            if matchup.matchup_id not in matchup_cache:
                sides = sorted((participant_key(matchup.participant_a), participant_key(matchup.participant_b)))
                matchup_cache[matchup.matchup_id] = (matchup.round_number, sides[0], sides[1])
            return matchup_cache[matchup.matchup_id]

        ordered = sorted(matchups, key=matchup_key)
        return tuple(
            row.model_copy(update={
                "participant_a": left,
                "participant_b": right,
            })
            for row in ordered
            for left, right in [sorted(
                (row.participant_a, row.participant_b), key=participant_key
            )]
        )

    @model_validator(mode="after")
    def validate_structure(self) -> "LeaguePlayoffRules":
        if self.bracket_authority == "provider_observed_exact" and self.bracket_derivation_policy is not None:
            raise ValueError("observed brackets cannot declare a derived bracket policy")
        if self.bracket_authority == "settings_derived_standard" and (self.matchups or self.bracket_derivation_policy is None):
            raise ValueError("settings-derived brackets require a derivation policy and no observed matchup graph")
        if len(self.round_weeks) != self.round_count:
            raise ValueError("round_weeks must map every configured playoff round")
        if tuple(sorted(set(self.round_weeks))) != self.round_weeks:
            raise ValueError("round_weeks must be strictly increasing")
        if self.round_weeks[0] != self.playoff_start_week:
            raise ValueError("first playoff round week must equal playoff_start_week")
        if self.bye_count != len(self.bye_seeds):
            raise ValueError("bye_count must equal the number of bye_seeds")
        if len(set(self.bye_seeds)) != len(self.bye_seeds):
            raise ValueError("bye_seeds must be unique")
        if any(seed > self.playoff_team_count for seed in self.bye_seeds):
            raise ValueError("bye seed exceeds playoff_team_count")
        matchups = self.effective_matchups()
        if not matchups:
            return self
        matchup_ids = [row.matchup_id for row in matchups]
        if len(set(matchup_ids)) != len(matchup_ids):
            raise ValueError("playoff matchup ids must be unique")
        if any(not value.strip() for value in matchup_ids):
            raise ValueError("playoff matchup ids cannot be blank")
        by_id = {row.matchup_id: row for row in matchups}
        if sum(row.round_number == self.round_count for row in matchups) != 1:
            raise ValueError("final playoff round must contain exactly one championship matchup")
        opening_seeds = [
            participant.seed_number
            for row in matchups
            if row.round_number == 1
            for participant in (row.participant_a, row.participant_b)
            if participant.seed_number is not None
        ]
        if len(set(opening_seeds)) != len(opening_seeds):
            raise ValueError("an opening-round seed may appear only once")
        if set(opening_seeds) & set(self.bye_seeds):
            raise ValueError("a bye seed cannot also play in round one")
        if set(opening_seeds) | set(self.bye_seeds) != set(
            range(1, self.playoff_team_count + 1)
        ):
            raise ValueError("opening matchups and bye_seeds must cover every playoff seed")
        for matchup in matchups:
            if matchup.round_number > self.round_count:
                raise ValueError("playoff matchup round exceeds round_count")
            if matchup.week != self.round_weeks[matchup.round_number - 1]:
                raise ValueError("playoff matchup week conflicts with round_weeks")
            for participant in (matchup.participant_a, matchup.participant_b):
                if participant.seed_number is not None and participant.seed_number > self.playoff_team_count:
                    raise ValueError("bracket seed exceeds playoff_team_count")
                if matchup.round_number > 1 and participant.seed_number is not None:
                    if participant.seed_number not in self.bye_seeds:
                        raise ValueError("later-round seed entrants must be configured bye seeds")
                    if matchup.round_number != 2:
                        raise ValueError("bye seeds must enter in the first playoff round")
                if participant.winner_of_matchup_id is not None:
                    source = by_id.get(participant.winner_of_matchup_id)
                    if source is None or source.round_number != matchup.round_number - 1:
                        raise ValueError("bracket winner reference must name the immediately prior round")
        for round_number in range(1, self.round_count):
            sources = [row for row in matchups if row.round_number == round_number]
            consumers = [
                participant.winner_of_matchup_id
                for row in matchups
                if row.round_number == round_number + 1
                for participant in (row.participant_a, row.participant_b)
                if participant.winner_of_matchup_id is not None
            ]
            source_ids = {row.matchup_id for row in sources}
            if set(consumers) != source_ids or len(consumers) != len(source_ids):
                raise ValueError("every non-final matchup winner must advance exactly once")
        bye_consumers = [
            participant.seed_number
            for row in matchups
            if row.round_number > 1
            for participant in (row.participant_a, row.participant_b)
            if participant.seed_number is not None
        ]
        if set(bye_consumers) != set(self.bye_seeds) or len(bye_consumers) != len(self.bye_seeds):
            raise ValueError("every configured bye seed must enter the bracket exactly once")
        championship = by_id.get(self.championship_matchup_id)
        if (
            championship is None
            or championship.round_number != self.championship_round_number
            or championship.week != self.championship_week
        ):
            raise ValueError("championship matchup, round and week must identify one configured game")
        if self.championship_round_number != self.round_count:
            raise ValueError("championship must be scheduled in the final configured round")
        return self

    def qualification_unavailability_reason(self) -> str | None:
        """Return why league playoff qualification cannot be simulated safely."""

        required = {
            "seeding_policy": "overall_standings",
            "standings_tiebreak_policy": "wins_then_points_for_then_team_id_v1",
        }
        missing = sorted(name for name in required if getattr(self, name) is None)
        if missing:
            return "playoff_rules_incomplete:" + ",".join(missing)
        unsupported = sorted(
            name for name, value in required.items() if getattr(self, name) != value
        )
        if unsupported:
            return "playoff_rules_unsupported:" + ",".join(unsupported)
        return None

    def simulation_unavailability_reason(self) -> str | None:
        """Return why bracket/title output must fail closed for this structure."""

        qualification_unavailability = self.qualification_unavailability_reason()
        if qualification_unavailability is not None:
            return qualification_unavailability
        if not self.effective_matchups():
            return "playoff_rules_unsupported:bracket_structure"
        required = {
            "reseeding_policy": "fixed_bracket",
            "playoff_scoring_policy": "same_as_league_regular_season",
            "matchup_tiebreak_policy": "higher_original_seed",
        }
        missing = sorted(name for name in required if getattr(self, name) is None)
        if missing:
            return "playoff_rules_incomplete:" + ",".join(missing)
        unsupported = sorted(
            name for name, value in required.items() if getattr(self, name) != value
        )
        if unsupported:
            return "playoff_rules_unsupported:" + ",".join(unsupported)
        return None

    def championship_probability_provenance(self) -> str | None:
        return None if self.simulation_unavailability_reason() is not None else self.bracket_authority


class LeagueRules(FrozenModel):
    team_count: Annotated[int, Field(ge=2)]
    roster_size: Annotated[int, Field(ge=1)]
    taxi_size: Annotated[int, Field(ge=0)] = 0
    ir_size: Annotated[int, Field(ge=0)] = 0
    rookie_draft_rounds: Annotated[int, Field(ge=0)] = 0
    playoff_team_count: Annotated[int, Field(ge=1)] | None = None
    fantasy_regular_season_end_week: Annotated[int, Field(ge=1, le=18)] | None = None
    playoff_start_week: Annotated[int, Field(ge=1, le=22)] | None = None
    playoff_rules: LeaguePlayoffRules | None = None
    lineup: tuple[LineupRequirement, ...]
    scoring: tuple[ScoringRule, ...]

    @model_validator(mode="after")
    def validate_playoff_count(self) -> "LeagueRules":
        if self.playoff_team_count is not None and self.playoff_team_count > self.team_count:
            raise ValueError("playoff_team_count cannot exceed team_count")
        if (
            self.fantasy_regular_season_end_week is not None
            and self.playoff_start_week is not None
            and self.fantasy_regular_season_end_week + 1 != self.playoff_start_week
        ):
            raise ValueError("playoff_start_week must immediately follow the regular-season end")
        if (
            self.playoff_rules is not None
            and self.playoff_rules.playoff_team_count > self.team_count
        ):
            raise ValueError("playoff rules team count cannot exceed league team_count")
        if (
            self.playoff_rules is not None
            and self.playoff_team_count is not None
            and self.playoff_rules.playoff_team_count != self.playoff_team_count
        ):
            raise ValueError("playoff rules team count conflicts with LeagueRules")
        if self.playoff_rules is not None:
            if (
                self.playoff_start_week is not None
                and self.playoff_rules.playoff_start_week != self.playoff_start_week
            ):
                raise ValueError("playoff rules start week conflicts with LeagueRules")
            if (
                self.fantasy_regular_season_end_week is not None
                and self.playoff_rules.playoff_start_week
                != self.fantasy_regular_season_end_week + 1
            ):
                raise ValueError("playoff rules start week must follow the regular-season end")
        if self.playoff_rules is not None and self.playoff_team_count is None:
            raise ValueError("playoff_team_count is required when playoff rules are configured")
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


class WeeklyAvailabilityStatus(StrEnum):
    """Exact week-specific player availability fact carried by canonical State."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class PlayerWeekAvailability(FrozenModel):
    """Provider-neutral exact availability fact for one player/fantasy week.

    Absence of a row means availability is not known exactly. Probabilistic
    missed-game evidence belongs to Forecast/Simulation, not canonical State.
    """

    player_id: str
    week: Annotated[int, Field(ge=1, le=18)]
    status: WeeklyAvailabilityStatus
    provenance: Provenance

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("player_id cannot be blank")
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
        return canonical_nfl_team(value)


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
    max_points_for: Annotated[float, Field(ge=0)] | None = None
    max_points_for_provenance: Provenance | None = None

    @model_validator(mode="after")
    def unique_player_entries(self) -> "TeamState":
        ids = [entry.player_id for entry in self.roster]
        if len(ids) != len(set(ids)):
            raise ValueError("a player may appear only once on a team roster")
        if (self.max_points_for is None) != (self.max_points_for_provenance is None):
            raise ValueError(
                "max_points_for and max_points_for_provenance must be present together"
            )
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
    completed_through_week: Annotated[int, Field(ge=0, le=18)] | None = None
    nfl_team_byes: tuple[NflTeamBye, ...] = ()
    player_week_availability: tuple[PlayerWeekAvailability, ...] = ()
    draft_order_policies: tuple[DraftOrderPolicyEvidence, ...] = ()
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
        availability_keys = [
            (item.week, item.player_id) for item in self.player_week_availability
        ]
        if len(availability_keys) != len(set(availability_keys)):
            raise ValueError("player availability may have only one fact per player/week")
        if any(
            item.player_id not in player_ids for item in self.player_week_availability
        ):
            raise ValueError("player availability references unknown player")
        if any(
            item.league_id != self.league.league_id
            for item in self.draft_order_policies
        ):
            raise ValueError("draft-order policy evidence must belong to the league")
        policy_keys = [
            (
                item.draft_season,
                item.policy_id,
                item.version,
                item.effective_at,
                item.available_at,
            )
            for item in self.draft_order_policies
        ]
        if len(policy_keys) != len(set(policy_keys)):
            raise ValueError("duplicate draft-order policy evidence")
        return self

    def canonical_json(self) -> str:
        from .serialization import canonical_state_json

        return canonical_state_json(self)

    @property
    def state_id(self) -> str:
        from .serialization import deterministic_state_id

        return deterministic_state_id(self)
