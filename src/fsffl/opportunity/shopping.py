from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import Asset, FrozenModel, LeagueState

from .trade_universe import (
    TradePackageSeed,
    TradeSearchBounds,
    build_team_trade_inventory,
    canonical_package_id,
    enumerate_counterparties,
    enumerate_trade_packages,
)


class ShopRequest(FrozenModel):
    focal_team_id: str
    asset: Asset

    @model_validator(mode="after")
    def validate_request(self) -> "ShopRequest":
        if not self.focal_team_id.strip():
            raise ValueError("shop focal_team_id cannot be blank")
        return self


class ShopCounterpartyUniverse(FrozenModel):
    counterparty_team_id: str
    return_packages: tuple[TradePackageSeed, ...]


class ShopUniverse(FrozenModel):
    focal_team_id: str
    focal_package: TradePackageSeed
    counterparties: tuple[ShopCounterpartyUniverse, ...]
    total_return_packages: int
    search_model_version: str = "next6-shop-universe-v1"

    @model_validator(mode="after")
    def validate_universe(self) -> "ShopUniverse":
        if not self.focal_team_id.strip() or not self.search_model_version.strip():
            raise ValueError("shop universe identifiers cannot be blank")
        if self.focal_package.team_id != self.focal_team_id:
            raise ValueError("shop focal package must belong to focal team")
        if any(item.counterparty_team_id == self.focal_team_id for item in self.counterparties):
            raise ValueError("shop universe cannot include focal team as counterparty")
        observed = sum(len(item.return_packages) for item in self.counterparties)
        if observed != self.total_return_packages:
            raise ValueError("shop total_return_packages must match generated packages")
        return self


def build_shop_universe(
    league_state: LeagueState,
    *,
    request: ShopRequest,
    bounds: TradeSearchBounds,
    search_model_version: str = "next6-shop-universe-v1",
) -> ShopUniverse:
    """Build structural counterparties/packages for shopping one owned asset.

    No desirability, demand, acceptance, or price is inferred here. Every generated
    return package is simply a legal-owned package worth evaluating downstream.
    """

    if not search_model_version.strip():
        raise ValueError("search_model_version cannot be blank")

    focal_inventory = build_team_trade_inventory(
        league_state,
        team_id=request.focal_team_id,
        bounds=bounds,
    )
    if request.asset not in focal_inventory.assets:
        raise ValueError("shopped asset must be owned by focal team and allowed by search bounds")

    focal_assets = (request.asset,)
    focal_package = TradePackageSeed(
        team_id=request.focal_team_id,
        assets=focal_assets,
        canonical_id=canonical_package_id(request.focal_team_id, focal_assets),
    )

    counterparties: list[ShopCounterpartyUniverse] = []
    for team_id in enumerate_counterparties(league_state, focal_team_id=request.focal_team_id):
        inventory = build_team_trade_inventory(league_state, team_id=team_id, bounds=bounds)
        packages = enumerate_trade_packages(inventory, bounds=bounds)
        counterparties.append(
            ShopCounterpartyUniverse(
                counterparty_team_id=team_id,
                return_packages=packages,
            )
        )

    return ShopUniverse(
        focal_team_id=request.focal_team_id,
        focal_package=focal_package,
        counterparties=tuple(counterparties),
        total_return_packages=sum(len(item.return_packages) for item in counterparties),
        search_model_version=search_model_version,
    )
