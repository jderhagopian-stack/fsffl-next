"""Admitted bounded draft-player acquisitions for the existing roster replay."""
from dataclasses import dataclass
from datetime import datetime
from .historical_roster_replay import PlayerTransfer


@dataclass(frozen=True)
class HistoricalDraftPlayerAllocation:
    draft_id: str
    provider_league_id: str
    season: int
    not_before: datetime | None
    by: datetime
    source_observed_at: datetime
    source_sha256: str
    source_ref: str
    player_transfers: tuple[PlayerTransfer, ...]
    player_details_complete: bool = True

    def __post_init__(self):
        if not all(s.strip() for s in (self.draft_id, self.provider_league_id, self.source_ref)):
            raise ValueError('draft allocation identity and source required')
        if len(self.source_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.source_sha256):
            raise ValueError('draft allocation requires exact source SHA256')
        for at in (self.by, self.source_observed_at) + ((self.not_before,) if self.not_before is not None else ()):
            if at.tzinfo is None or at.utcoffset() is None:
                raise ValueError('draft allocation clocks must be timezone-aware')
        if self.season < 1900 or self.by > self.source_observed_at or (self.not_before is not None and self.not_before > self.by):
            raise ValueError('draft allocation bounds or source observation invalid')
        if len({p.player_id for p in self.player_transfers}) != len(self.player_transfers):
            raise ValueError('draft allocations require unique selected players')
        if any(p.from_team_id is not None or p.to_team_id is None for p in self.player_transfers):
            raise ValueError('draft selection must acquire an available player')
