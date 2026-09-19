from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel


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
    model_version: str = "owner-behavior-profile-v1"

    @field_validator("as_of", "first_observed_at")
    @classmethod
    def require_profile_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("behavioral profile timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> "OwnerBehaviorProfile":
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
