from __future__ import annotations

from datetime import datetime

from pydantic import field_validator, model_validator

from fsffl.state.models import Asset, FaabAsset, FrozenModel, PickAsset, PlayerAsset


class TradeLeg(FrozenModel):
    team_id: str
    sends: tuple[Asset, ...]

    @model_validator(mode="after")
    def validate_leg(self) -> "TradeLeg":
        if not self.team_id.strip():
            raise ValueError("team_id cannot be blank")
        if not self.sends:
            raise ValueError("each trade leg must send at least one asset")

        seen: set[tuple[str, str]] = set()
        for asset in self.sends:
            if isinstance(asset, PlayerAsset):
                key = ("player", asset.player_id)
            elif isinstance(asset, PickAsset):
                key = ("pick", asset.pick_id)
            elif isinstance(asset, FaabAsset):
                key = ("faab", str(asset.amount))
            else:  # pragma: no cover - discriminator should make this unreachable
                raise TypeError("unsupported trade asset")
            if key in seen and key[0] != "faab":
                raise ValueError("a player or pick may appear only once on a trade leg")
            seen.add(key)
        return self


class BilateralTradeProposal(FrozenModel):
    proposal_id: str
    as_of: datetime
    side_a: TradeLeg
    side_b: TradeLeg
    model_version: str = "next5-trade-proposal-v1"

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_proposal(self) -> "BilateralTradeProposal":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("proposal identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("a bilateral trade requires two distinct teams")

        seen_players: set[str] = set()
        seen_picks: set[str] = set()
        for leg in (self.side_a, self.side_b):
            for asset in leg.sends:
                if isinstance(asset, PlayerAsset):
                    if asset.player_id in seen_players:
                        raise ValueError("the same player cannot be sent by both sides")
                    seen_players.add(asset.player_id)
                elif isinstance(asset, PickAsset):
                    if asset.pick_id in seen_picks:
                        raise ValueError("the same pick cannot be sent by both sides")
                    seen_picks.add(asset.pick_id)
        return self
