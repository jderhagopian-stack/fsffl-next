from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from .models import FrozenModel, LeagueRules, Provenance


class HistoricalDraftSlotAssignment(FrozenModel):
    """One team-to-slot assignment that was historically knowable."""

    team_id: str
    slot_in_round: Annotated[int, Field(ge=1)]

    @field_validator("team_id")
    @classmethod
    def require_team_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("historical draft-slot team_id cannot be blank")
        return value.strip()


class HistoricalDraftOrderSnapshot(FrozenModel):
    """Point-in-time State evidence that a draft order was already resolved.

    ``available_at`` is the evidence boundary: downstream historical analysis may
    use an exact slot only at or after this timestamp. The snapshot records the
    observed assignment and does not infer how the league produced that order.
    """

    league_id: str
    draft_season: Annotated[int, Field(ge=1900)]
    available_at: datetime
    assignments: tuple[HistoricalDraftSlotAssignment, ...]
    version: str
    provenance: Provenance

    @field_validator("available_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("historical draft-order snapshot timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> "HistoricalDraftOrderSnapshot":
        if not self.league_id.strip() or not self.version.strip():
            raise ValueError("historical draft-order snapshot identifiers cannot be blank")
        if not self.assignments:
            raise ValueError("historical draft-order snapshot must contain assignments")
        team_ids = [item.team_id for item in self.assignments]
        slots = [item.slot_in_round for item in self.assignments]
        if len(team_ids) != len(set(team_ids)):
            raise ValueError("historical draft-order snapshot team ids must be unique")
        if len(slots) != len(set(slots)):
            raise ValueError("historical draft-order snapshot slots must be unique")
        return self

    def exact_slot_for_team(self, team_id: str, *, league_rules: LeagueRules) -> int:
        """Return the recorded slot, validating it against configured league size."""

        matches = [item for item in self.assignments if item.team_id == team_id]
        if len(matches) != 1:
            raise ValueError("historical draft-order snapshot must assign the requested team exactly once")
        slot = matches[0].slot_in_round
        if slot > league_rules.team_count:
            raise ValueError("historical draft-order snapshot slot exceeds configured league team count")
        return slot


def resolve_historical_draft_order_snapshot(
    snapshots: tuple[HistoricalDraftOrderSnapshot, ...],
    *,
    league_id: str,
    draft_season: int,
    as_of: datetime,
) -> HistoricalDraftOrderSnapshot | None:
    """Return the latest matching draft-order snapshot knowable by ``as_of``."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    candidates = [
        item
        for item in snapshots
        if item.league_id == league_id
        and item.draft_season == draft_season
        and item.available_at <= as_of
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.available_at, item.version))
