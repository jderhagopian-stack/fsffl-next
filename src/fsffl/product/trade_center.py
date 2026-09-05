from __future__ import annotations

from datetime import datetime

from pydantic import field_validator, model_validator

from fsffl.state.models import Asset, FrozenModel
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg


class TradeDraftSide(FrozenModel):
    team_id: str
    assets: tuple[Asset, ...] = ()

    @model_validator(mode="after")
    def validate_side(self) -> "TradeDraftSide":
        if not self.team_id.strip():
            raise ValueError("trade draft team_id cannot be blank")
        player_ids = [asset.player_id for asset in self.assets if getattr(asset, "kind", None) == "player"]
        pick_ids = [asset.pick_id for asset in self.assets if getattr(asset, "kind", None) == "pick"]
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("trade draft cannot contain duplicate players")
        if len(pick_ids) != len(set(pick_ids)):
            raise ValueError("trade draft cannot contain duplicate picks")
        return self


class TradeDraft(FrozenModel):
    draft_id: str
    focal_team_id: str
    counterparty_team_id: str
    focal_side: TradeDraftSide
    counterparty_side: TradeDraftSide
    product_version: str = "next8-trade-draft-v1"

    @model_validator(mode="after")
    def validate_draft(self) -> "TradeDraft":
        if not self.draft_id.strip() or not self.product_version.strip():
            raise ValueError("trade draft identifiers cannot be blank")
        if self.focal_team_id == self.counterparty_team_id:
            raise ValueError("trade draft requires distinct teams")
        if self.focal_side.team_id != self.focal_team_id:
            raise ValueError("focal draft side must match focal_team_id")
        if self.counterparty_side.team_id != self.counterparty_team_id:
            raise ValueError("counterparty draft side must match counterparty_team_id")
        return self

    @property
    def ready_to_submit(self) -> bool:
        return bool(self.focal_side.assets and self.counterparty_side.assets)


def add_asset_to_draft(
    draft: TradeDraft,
    *,
    team_id: str,
    asset: Asset,
) -> TradeDraft:
    """Frontend-safe immutable draft edit; no valuation or trade interpretation."""

    if team_id == draft.focal_team_id:
        side = TradeDraftSide(team_id=team_id, assets=draft.focal_side.assets + (asset,))
        return draft.model_copy(update={"focal_side": side})
    if team_id == draft.counterparty_team_id:
        side = TradeDraftSide(team_id=team_id, assets=draft.counterparty_side.assets + (asset,))
        return draft.model_copy(update={"counterparty_side": side})
    raise ValueError("asset can only be added to one of the trade draft teams")


def remove_asset_from_draft(
    draft: TradeDraft,
    *,
    team_id: str,
    asset: Asset,
) -> TradeDraft:
    """Remove one exact asset from a draft without evaluating its significance."""

    if team_id == draft.focal_team_id:
        remaining = tuple(item for item in draft.focal_side.assets if item != asset)
        side = TradeDraftSide(team_id=team_id, assets=remaining)
        return draft.model_copy(update={"focal_side": side})
    if team_id == draft.counterparty_team_id:
        remaining = tuple(item for item in draft.counterparty_side.assets if item != asset)
        side = TradeDraftSide(team_id=team_id, assets=remaining)
        return draft.model_copy(update={"counterparty_side": side})
    raise ValueError("asset can only be removed from one of the trade draft teams")


def submit_trade_draft(
    draft: TradeDraft,
    *,
    as_of: datetime,
    proposal_id: str | None = None,
) -> BilateralTradeProposal:
    """Convert product-only draft state into the authoritative NEXT-5 proposal contract."""

    if as_of.tzinfo is None:
        raise ValueError("trade proposal as_of must be timezone-aware")
    if not draft.ready_to_submit:
        raise ValueError("trade draft requires at least one asset from each team before submission")
    return BilateralTradeProposal(
        proposal_id=proposal_id or draft.draft_id,
        as_of=as_of,
        side_a=TradeLeg(team_id=draft.focal_team_id, sends=draft.focal_side.assets),
        side_b=TradeLeg(team_id=draft.counterparty_team_id, sends=draft.counterparty_side.assets),
    )
