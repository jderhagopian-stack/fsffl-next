from __future__ import annotations

from pydantic import model_validator

from fsffl.state.models import Asset, FaabAsset, FrozenModel

from .trade_universe import TeamTradeInventory, TradePackageSeed, TradeSearchBounds, canonical_package_id


class FrontierNeighbor(FrozenModel):
    """One structurally adjacent package point in negotiation search space.

    Adjacency means exactly one owned asset is added or removed. This object is
    search geometry only: it carries no value, utility, acceptance, or action
    authority.
    """

    origin_package_id: str
    package: TradePackageSeed
    move_kind: str
    changed_asset_key: str

    @model_validator(mode="after")
    def validate_neighbor(self) -> "FrontierNeighbor":
        if self.move_kind not in {"add", "remove"}:
            raise ValueError("frontier move_kind must be add or remove")
        if not self.origin_package_id.strip() or not self.changed_asset_key.strip():
            raise ValueError("frontier identifiers cannot be blank")
        return self


def _asset_key(asset: Asset) -> str:
    kind = getattr(asset, "kind", None)
    if kind == "player":
        return f"player:{asset.player_id}"
    if kind == "pick":
        return f"pick:{asset.pick_id}"
    if kind == "faab":
        return f"faab:{asset.amount}"
    raise TypeError("unsupported trade asset")


def _contains_multiple_faab(assets: tuple[Asset, ...]) -> bool:
    return sum(isinstance(asset, FaabAsset) for asset in assets) > 1


def expand_adjacent_packages(
    origin: TradePackageSeed,
    *,
    inventory: TeamTradeInventory,
    bounds: TradeSearchBounds,
) -> tuple[FrontierNeighbor, ...]:
    """Generate deterministic one-step package neighbors without revaluation.

    The expansion is deliberately local so price discovery can continue past a
    seed offer without exploding immediately into the full package cross-product.
    Every added asset must be in the team's canonical owned inventory. Package
    bounds and the single-FAAB-alternative rule remain enforced.
    """

    if origin.team_id != inventory.team_id:
        raise ValueError("origin package and inventory must belong to the same team")

    origin_by_key = {_asset_key(asset): asset for asset in origin.assets}
    inventory_by_key = {_asset_key(asset): asset for asset in inventory.assets}
    if not set(origin_by_key).issubset(inventory_by_key):
        raise ValueError("origin package contains an asset outside the owned inventory")

    neighbors: dict[str, FrontierNeighbor] = {}

    # Removal neighbors are useful when walking back from an overpay package.
    if len(origin.assets) > 1:
        for changed_key in sorted(origin_by_key):
            assets = tuple(
                asset for key, asset in sorted(origin_by_key.items()) if key != changed_key
            )
            package_id = canonical_package_id(origin.team_id, assets)
            neighbors[package_id] = FrontierNeighbor(
                origin_package_id=origin.canonical_id,
                package=TradePackageSeed(
                    team_id=origin.team_id,
                    assets=assets,
                    canonical_id=package_id,
                ),
                move_kind="remove",
                changed_asset_key=changed_key,
            )

    # Addition neighbors let the search continue until a bilateral boundary is found.
    if len(origin.assets) < bounds.max_assets_per_side:
        for changed_key, changed_asset in sorted(inventory_by_key.items()):
            if changed_key in origin_by_key:
                continue
            assets = tuple(origin.assets) + (changed_asset,)
            if _contains_multiple_faab(assets):
                continue
            package_id = canonical_package_id(origin.team_id, assets)
            neighbors[package_id] = FrontierNeighbor(
                origin_package_id=origin.canonical_id,
                package=TradePackageSeed(
                    team_id=origin.team_id,
                    assets=assets,
                    canonical_id=package_id,
                ),
                move_kind="add",
                changed_asset_key=changed_key,
            )

    return tuple(neighbors[key] for key in sorted(neighbors))


class BilateralFrontierPoint(FrozenModel):
    """Canonical identity for one pair of package seeds on a negotiation frontier."""

    focal_package: TradePackageSeed
    counterparty_package: TradePackageSeed
    point_id: str

    @model_validator(mode="after")
    def validate_point(self) -> "BilateralFrontierPoint":
        if self.focal_package.team_id == self.counterparty_package.team_id:
            raise ValueError("bilateral frontier requires distinct teams")
        expected = canonical_frontier_point_id(
            self.focal_package.canonical_id,
            self.counterparty_package.canonical_id,
        )
        if self.point_id != expected:
            raise ValueError("frontier point_id must be canonical")
        return self


def canonical_frontier_point_id(focal_package_id: str, counterparty_package_id: str) -> str:
    if not focal_package_id.strip() or not counterparty_package_id.strip():
        raise ValueError("frontier package ids cannot be blank")
    return f"{focal_package_id}=>{counterparty_package_id}"


def make_frontier_point(
    focal_package: TradePackageSeed,
    counterparty_package: TradePackageSeed,
) -> BilateralFrontierPoint:
    return BilateralFrontierPoint(
        focal_package=focal_package,
        counterparty_package=counterparty_package,
        point_id=canonical_frontier_point_id(
            focal_package.canonical_id,
            counterparty_package.canonical_id,
        ),
    )
