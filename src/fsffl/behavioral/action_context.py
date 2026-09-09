from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Protocol

from pydantic import field_validator, model_validator

from fsffl.state.history import StateSnapshotStore
from fsffl.state.models import FrozenModel, LeagueState, Position, RosterSlot

from .models import OwnerBehaviorEvent


class BehavioralPositionContext(FrozenModel):
    """Factual pre-action roster context for one position.

    This object intentionally contains no preference score or value adjustment. It
    records what the roster looked like immediately before an observed owner action
    so later context models can explain behavior without leaking current state or
    future outcomes into historical inference.
    """

    position: Position
    rostered_count: int
    active_rostered_count: int
    direct_starter_requirement: int
    league_average_rostered_count: float
    league_average_active_rostered_count: float

    @model_validator(mode="after")
    def validate_counts(self) -> "BehavioralPositionContext":
        if self.rostered_count < 0 or self.active_rostered_count < 0:
            raise ValueError("behavioral position roster counts cannot be negative")
        if self.active_rostered_count > self.rostered_count:
            raise ValueError("active roster count cannot exceed total roster count")
        if self.direct_starter_requirement < 0:
            raise ValueError("direct starter requirement cannot be negative")
        if self.league_average_rostered_count < 0 or self.league_average_active_rostered_count < 0:
            raise ValueError("league-average roster counts cannot be negative")
        return self


class BehavioralActionContext(FrozenModel):
    """Point-in-time context reconstructed strictly before an observed action."""

    event_id: str
    owner_id: str
    team_id: str
    league_id: str
    occurred_at: datetime
    snapshot_as_of: datetime
    snapshot_state_id: str
    snapshot_age_seconds: float
    roster_size: int
    active_roster_size: int
    faab_balance: int
    owned_pick_count: int
    flex_slot_count: int
    superflex_slot_count: int
    positions: tuple[BehavioralPositionContext, ...]
    source_state_schema_version: str
    model_version: str = "behavioral-action-context-v1"

    @field_validator("occurred_at", "snapshot_as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral action context timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_context(self) -> "BehavioralActionContext":
        if any(
            not value.strip()
            for value in (
                self.event_id,
                self.owner_id,
                self.team_id,
                self.league_id,
                self.snapshot_state_id,
                self.source_state_schema_version,
                self.model_version,
            )
        ):
            raise ValueError("behavioral action context identifiers cannot be blank")
        if self.snapshot_as_of >= self.occurred_at:
            raise ValueError("behavioral action context requires a strictly pre-action snapshot")
        expected_age = (self.occurred_at - self.snapshot_as_of).total_seconds()
        if expected_age <= 0 or abs(expected_age - self.snapshot_age_seconds) > 1e-6:
            raise ValueError("behavioral action context snapshot age must reconcile")
        if self.roster_size < 0 or self.active_roster_size < 0 or self.faab_balance < 0 or self.owned_pick_count < 0:
            raise ValueError("behavioral action context counts cannot be negative")
        if self.active_roster_size > self.roster_size:
            raise ValueError("active roster size cannot exceed roster size")
        if self.flex_slot_count < 0 or self.superflex_slot_count < 0:
            raise ValueError("behavioral action context lineup counts cannot be negative")
        positions = [row.position for row in self.positions]
        if len(positions) != len(set(positions)):
            raise ValueError("behavioral action context positions must be unique")
        return self


class BehavioralActionContextResult(FrozenModel):
    context: BehavioralActionContext | None = None
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def exactly_one_result(self) -> "BehavioralActionContextResult":
        if (self.context is None) == (self.unavailable_reason is None):
            raise ValueError("behavioral action context result requires context or unavailable_reason")
        if self.unavailable_reason is not None and not self.unavailable_reason.strip():
            raise ValueError("behavioral action context unavailable_reason cannot be blank")
        return self


_ACTIVE_EXCLUDED_SLOTS = {RosterSlot.TAXI, RosterSlot.IR}
_CONTEXT_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def _team_position_counts(state: LeagueState, team_id: str, *, active_only: bool) -> Counter[Position]:
    players = {player.player_id: player for player in state.players}
    team_state = next(item for item in state.team_states if item.team_id == team_id)
    counts: Counter[Position] = Counter()
    for entry in team_state.roster:
        if active_only and entry.slot in _ACTIVE_EXCLUDED_SLOTS:
            continue
        player = players.get(entry.player_id)
        if player is not None:
            counts[player.position] += 1
    return counts


def _direct_starter_requirements(state: LeagueState) -> Counter[Position]:
    slot_to_position = {
        RosterSlot.QB: Position.QB,
        RosterSlot.RB: Position.RB,
        RosterSlot.WR: Position.WR,
        RosterSlot.TE: Position.TE,
        RosterSlot.K: Position.K,
        RosterSlot.DST: Position.DST,
    }
    requirements: Counter[Position] = Counter()
    for requirement in state.league.rules.lineup:
        position = slot_to_position.get(requirement.slot)
        if position is not None:
            requirements[position] += requirement.count
    return requirements


def reconstruct_behavioral_action_context(
    event: OwnerBehaviorEvent,
    *,
    league_id: str,
    team_id: str,
    snapshots: StateSnapshotStore,
) -> BehavioralActionContextResult:
    """Reconstruct strictly pre-action context from canonical LeagueState snapshots.

    The snapshot store may return a state at the action timestamp, which can already
    contain the completed transaction. Such a snapshot is rejected rather than
    silently used as pre-action evidence. Missing historical coverage is surfaced as
    unavailable evidence, never converted to a neutral context assumption.
    """

    if not league_id.strip() or not team_id.strip():
        raise ValueError("behavioral action context league/team identifiers cannot be blank")
    if event.occurred_at.tzinfo is None:
        raise ValueError("behavioral event timestamp must be timezone-aware")

    state = snapshots.latest_at_or_before(league_id, event.occurred_at)
    if state is None:
        return BehavioralActionContextResult(
            unavailable_reason="no league-state snapshot exists at or before the observed action"
        )
    if state.as_of >= event.occurred_at:
        return BehavioralActionContextResult(
            unavailable_reason="latest historical snapshot is not strictly pre-action"
        )
    if state.league.league_id != league_id:
        return BehavioralActionContextResult(unavailable_reason="snapshot league identity mismatch")

    team_ids = {team.team_id for team in state.teams}
    if team_id not in team_ids:
        return BehavioralActionContextResult(unavailable_reason="team is absent from historical snapshot")

    team_state = next(item for item in state.team_states if item.team_id == team_id)
    total_by_team = {
        candidate: _team_position_counts(state, candidate, active_only=False)
        for candidate in sorted(team_ids)
    }
    active_by_team = {
        candidate: _team_position_counts(state, candidate, active_only=True)
        for candidate in sorted(team_ids)
    }
    direct_requirements = _direct_starter_requirements(state)
    team_count = len(team_ids)

    rows: list[BehavioralPositionContext] = []
    for position in _CONTEXT_POSITIONS:
        league_total = sum(total_by_team[candidate][position] for candidate in team_ids)
        league_active = sum(active_by_team[candidate][position] for candidate in team_ids)
        rows.append(
            BehavioralPositionContext(
                position=position,
                rostered_count=total_by_team[team_id][position],
                active_rostered_count=active_by_team[team_id][position],
                direct_starter_requirement=direct_requirements[position],
                league_average_rostered_count=league_total / team_count,
                league_average_active_rostered_count=league_active / team_count,
            )
        )

    flex_slots = sum(
        item.count for item in state.league.rules.lineup if item.slot == RosterSlot.FLEX
    )
    superflex_slots = sum(
        item.count for item in state.league.rules.lineup if item.slot == RosterSlot.SUPERFLEX
    )
    owned_pick_count = sum(
        1 for ownership in state.pick_ownership if ownership.owner_team_id == team_id
    )
    active_roster_size = sum(
        1 for entry in team_state.roster if entry.slot not in _ACTIVE_EXCLUDED_SLOTS
    )

    return BehavioralActionContextResult(
        context=BehavioralActionContext(
            event_id=event.event_id,
            owner_id=event.owner_id,
            team_id=team_id,
            league_id=league_id,
            occurred_at=event.occurred_at,
            snapshot_as_of=state.as_of,
            snapshot_state_id=state.state_id,
            snapshot_age_seconds=(event.occurred_at - state.as_of).total_seconds(),
            roster_size=len(team_state.roster),
            active_roster_size=active_roster_size,
            faab_balance=team_state.faab_balance,
            owned_pick_count=owned_pick_count,
            flex_slot_count=flex_slots,
            superflex_slot_count=superflex_slots,
            positions=tuple(rows),
            source_state_schema_version=state.schema_version,
        )
    )
