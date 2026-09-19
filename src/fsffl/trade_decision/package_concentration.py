from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from pydantic import Field, model_validator

from fsffl.state.models import FaabAsset, FrozenModel, PickAsset, PlayerAsset

from .models import BilateralTradeProposal, TradeLeg


class PackageConcentrationStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class PackageConcentrationSide(FrozenModel):
    team_id: str
    asset_count: int = Field(ge=1)
    mapped_asset_count: int = Field(ge=0)
    total_market_value: float | None = Field(default=None, ge=0.0)
    largest_asset_market_value: float | None = Field(default=None, ge=0.0)
    largest_asset_id: str | None = None
    largest_asset_share: float | None = Field(default=None, ge=0.0, le=1.0)
    status: PackageConcentrationStatus

    @model_validator(mode="after")
    def validate_side(self) -> "PackageConcentrationSide":
        if not self.team_id.strip():
            raise ValueError("package concentration team id cannot be blank")
        if self.mapped_asset_count > self.asset_count:
            raise ValueError("mapped asset count cannot exceed package asset count")
        if self.status == PackageConcentrationStatus.COMPLETE:
            if self.mapped_asset_count != self.asset_count:
                raise ValueError("complete package concentration requires all assets mapped")
            if self.total_market_value is None or self.largest_asset_market_value is None or self.largest_asset_share is None:
                raise ValueError("complete package concentration requires market totals")
        return self


class BilateralPackageConcentration(FrozenModel):
    proposal_id: str
    side_a: PackageConcentrationSide
    side_b: PackageConcentrationSide
    model_version: str = "next5-package-concentration-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "BilateralPackageConcentration":
        if not self.proposal_id.strip() or not self.model_version.strip():
            raise ValueError("package concentration identifiers cannot be blank")
        if self.side_a.team_id == self.side_b.team_id:
            raise ValueError("package concentration requires two distinct teams")
        return self


def _asset_id(asset) -> str | None:
    if isinstance(asset, PlayerAsset):
        return asset.player_id
    if isinstance(asset, PickAsset):
        return asset.pick_id
    if isinstance(asset, FaabAsset):
        return None
    raise TypeError("unsupported trade asset")


def _summarize_side(leg: TradeLeg, market_values: Mapping[str, float]) -> PackageConcentrationSide:
    valued: list[tuple[str, float]] = []
    for asset in leg.sends:
        asset_id = _asset_id(asset)
        if asset_id is None:
            continue
        value = market_values.get(asset_id)
        if value is None or value < 0:
            continue
        valued.append((asset_id, float(value)))

    complete = len(valued) == len(leg.sends)
    if not complete:
        return PackageConcentrationSide(
            team_id=leg.team_id,
            asset_count=len(leg.sends),
            mapped_asset_count=len(valued),
            status=PackageConcentrationStatus.INCOMPLETE,
        )

    total = sum(value for _, value in valued)
    largest_id, largest_value = max(valued, key=lambda item: (item[1], item[0]))
    share = largest_value / total if total > 0 else 0.0
    return PackageConcentrationSide(
        team_id=leg.team_id,
        asset_count=len(leg.sends),
        mapped_asset_count=len(valued),
        total_market_value=total,
        largest_asset_market_value=largest_value,
        largest_asset_id=largest_id,
        largest_asset_share=share,
        status=PackageConcentrationStatus.COMPLETE,
    )


def summarize_package_concentration(
    proposal: BilateralTradeProposal,
    market_values: Mapping[str, float],
    *,
    model_version: str = "next5-package-concentration-v1",
) -> BilateralPackageConcentration:
    """Describe how concentrated each sent package is on one market scale.

    This is Decision evidence, not a premium and not a recommendation. It exposes
    the structural difference between one elite asset and a package of lesser
    assets so a separately governed package-economics model can consume it exactly
    once. Missing Value fails closed instead of treating an unmapped asset as zero.
    """

    if not model_version.strip():
        raise ValueError("model_version cannot be blank")
    return BilateralPackageConcentration(
        proposal_id=proposal.proposal_id,
        side_a=_summarize_side(proposal.side_a, market_values),
        side_b=_summarize_side(proposal.side_b, market_values),
        model_version=model_version,
    )
