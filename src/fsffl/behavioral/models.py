from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from .historical_case_models import OwnerHistoricalTradeCase
from .owner_resume import OwnerFranchiseResume


class BehavioralAssetKind(StrEnum):
    PLAYER = "player"
    PICK = "pick"
    FAAB = "faab"


class BehavioralEventKind(StrEnum):
    TRADE = "trade"
    WAIVER = "waiver"
    FREE_AGENT = "free_agent"


class BehavioralAsset(FrozenModel):
    kind: BehavioralAssetKind
    asset_ref: str
    position: str | None = None
    pick_season: int | None = None
    pick_round: int | None = None
    faab_amount: Annotated[int | None, Field(ge=0)] = None

    @model_validator(mode="after")
    def validate_asset_shape(self) -> "BehavioralAsset":
        if not self.asset_ref.strip():
            raise ValueError("behavioral asset_ref cannot be blank")
        if self.kind == BehavioralAssetKind.PICK:
            if self.pick_season is None or self.pick_round is None:
                raise ValueError("pick behavioral assets require season and round")
        if self.kind == BehavioralAssetKind.FAAB and self.faab_amount is None:
            raise ValueError("FAAB behavioral assets require amount")
        return self


class OwnerBehaviorEvent(FrozenModel):
    event_id: str
    league_family_id: str
    league_external_id: str
    season: int
    owner_id: str
    roster_id: int
    occurred_at: datetime
    kind: BehavioralEventKind
    acquired: tuple[BehavioralAsset, ...] = ()
    disposed: tuple[BehavioralAsset, ...] = ()
    counterparty_owner_ids: tuple[str, ...] = ()
    source: str = "sleeper"
    source_version: str = "sleeper-behavior-v1"

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("behavioral event timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> "OwnerBehaviorEvent":
        if not self.event_id.strip() or not self.league_family_id.strip():
            raise ValueError("behavioral event identifiers cannot be blank")
        if not self.league_external_id.strip() or not self.owner_id.strip():
            raise ValueError("behavioral event league/owner identifiers cannot be blank")
        if self.roster_id < 1:
            raise ValueError("behavioral event roster_id must be positive")
        if self.owner_id in self.counterparty_owner_ids:
            raise ValueError("owner cannot be its own counterparty")
        return self


class CompletedTradeActivity(FrozenModel):
    """Trade-only counts, distinct from waiver/free-agent activity."""
    model_version: str = "completed-trade-activity-v1"
    acquired_pick_count: Annotated[int, Field(ge=0)] = 0
    disposed_pick_count: Annotated[int, Field(ge=0)] = 0
    trades_acquiring_picks: Annotated[int, Field(ge=0)] = 0
    trades_sending_picks: Annotated[int, Field(ge=0)] = 0
    acquired_positions: dict[str, int] = Field(default_factory=dict)
    disposed_positions: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_positions(self):
        if any(v < 0 for counts in (self.acquired_positions, self.disposed_positions) for v in counts.values()):
            raise ValueError("trade position counts cannot be negative")
        return self


class CompletedSeasonMove(FrozenModel):
    """Completed provider action, not a reconstructed historical State."""
    event: OwnerBehaviorEvent
    completed_at: datetime
    observed_at: datetime
    source_sha256: str

    @model_validator(mode="after")
    def valid_receipt(self):
        if self.completed_at.tzinfo is None or self.completed_at < self.event.occurred_at:
            raise ValueError("invalid completion clock")
        if self.observed_at.tzinfo is None or self.observed_at<self.completed_at:
            raise ValueError("source observation precedes completion")
        if len(self.source_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.source_sha256):
            raise ValueError("source receipt hash required")
        return self


class OwnerCurrentSeasonActivity(FrozenModel):
    league_external_id: str
    season: int
    cutoff: datetime
    observed_at: datetime
    missing_completion_count: int = Field(default=0,ge=0)
    trade_count: int = Field(ge=0)
    waiver_count: int = Field(ge=0)
    free_agent_count: int = Field(ge=0)
    picks_acquired_in_trades: int = Field(ge=0)
    picks_sent_in_trades: int = Field(ge=0)
    recent_moves: tuple[CompletedSeasonMove, ...] = ()
    trade_examples: tuple[CompletedSeasonMove, ...] = ()

    @model_validator(mode="after")
    def valid_window(self):
        if self.cutoff.tzinfo is None or self.observed_at.tzinfo is None or self.observed_at < self.cutoff:
            raise ValueError("separate observation and event cutoff required")
        if len(self.recent_moves)>12 or len(self.trade_examples)>64:
            raise ValueError("current activity is bounded")
        for move in (*self.recent_moves,*self.trade_examples):
            if move.event.league_external_id!=self.league_external_id or move.event.season!=self.season or move.completed_at>self.cutoff:
                raise ValueError("current action outside scope/cutoff")
        return self


class OwnerBehaviorProfile(FrozenModel):
    """Descriptive historical owner profile with no hidden preference weights.

    Counts and shares summarize observed behavior only. They are evidence that
    downstream Decision/Search may consume; they are not market Value or action
    authority by themselves.
    """

    league_family_id: str
    owner_id: str
    as_of: datetime
    first_observed_at: datetime | None = None
    event_count: Annotated[int, Field(ge=0)] = 0
    trade_count: Annotated[int, Field(ge=0)] = 0
    waiver_count: Annotated[int, Field(ge=0)] = 0
    free_agent_count: Annotated[int, Field(ge=0)] = 0
    acquired_player_count: Annotated[int, Field(ge=0)] = 0
    disposed_player_count: Annotated[int, Field(ge=0)] = 0
    acquired_pick_count: Annotated[int, Field(ge=0)] = 0
    disposed_pick_count: Annotated[int, Field(ge=0)] = 0
    acquired_faab: Annotated[int, Field(ge=0)] = 0
    disposed_faab: Annotated[int, Field(ge=0)] = 0
    consolidation_trade_count: Annotated[int, Field(ge=0)] = 0
    diversification_trade_count: Annotated[int, Field(ge=0)] = 0
    balanced_trade_count: Annotated[int, Field(ge=0)] = 0
    acquired_positions: dict[str, int] = Field(default_factory=dict)
    disposed_positions: dict[str, int] = Field(default_factory=dict)
    counterparty_trade_counts: dict[str, int] = Field(default_factory=dict)
    seasons_observed: tuple[int, ...] = ()
    completed_trade_activity: CompletedTradeActivity | None = None
    historical_trade_cases: tuple[OwnerHistoricalTradeCase,...] = ()
    franchise_resume: OwnerFranchiseResume | None = None
    current_season_activity: OwnerCurrentSeasonActivity | None = None
    model_version: str = "owner-behavior-profile-v1"

    @field_validator("as_of", "first_observed_at")
    @classmethod
    def require_profile_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("behavioral profile timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> "OwnerBehaviorProfile":
        activity=self.current_season_activity
        if activity is not None and (activity.cutoff!=self.as_of or any(
                m.event.owner_id!=self.owner_id or m.event.league_family_id!=self.league_family_id
                for m in (*activity.recent_moves,*activity.trade_examples))):
            raise ValueError("current actions must match profile owner/family/cutoff")
        if self.franchise_resume is not None and (self.franchise_resume.owner_id != self.owner_id
                or self.franchise_resume.league_family_id != self.league_family_id
                or self.franchise_resume.evidence_as_of > self.as_of):
            raise ValueError("franchise resume must match owner/family/cutoff")
        if any(c.owner_id != self.owner_id or c.league_family_id != self.league_family_id
                or max(c.completed_at,c.evidence_as_of) > self.as_of for c in self.historical_trade_cases):
            raise ValueError('historical cases must match owner/family/cutoff')
        if len({c.event_id for c in self.historical_trade_cases}) != len(self.historical_trade_cases):
            raise ValueError('duplicate historical owner case')
        if self.completed_trade_activity is not None and max(self.completed_trade_activity.trades_acquiring_picks,
                self.completed_trade_activity.trades_sending_picks) > self.trade_count:
            raise ValueError("trade-only pick event counts cannot exceed completed trades")
        if self.trade_count + self.waiver_count + self.free_agent_count != self.event_count:
            raise ValueError("behavioral profile event counts must reconcile")
        if self.consolidation_trade_count + self.diversification_trade_count + self.balanced_trade_count != self.trade_count:
            raise ValueError("behavioral trade-shape counts must reconcile")
        if any(value < 0 for value in self.acquired_positions.values()):
            raise ValueError("position counts cannot be negative")
        if any(value < 0 for value in self.disposed_positions.values()):
            raise ValueError("position counts cannot be negative")
        if any(value < 0 for value in self.counterparty_trade_counts.values()):
            raise ValueError("counterparty counts cannot be negative")
        return self
