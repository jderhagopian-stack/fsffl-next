from __future__ import annotations

from itertools import combinations
from typing import Annotated

from pydantic import Field, model_validator

from fsffl.state.models import Asset, FaabAsset, FrozenModel, LeagueState, PickAsset, PlayerAsset


class TradeSearchBounds(FrozenModel):
    max_assets_per_side: Annotated[int, Field(ge=1, le=6)] = 2
    include_players: bool = True
    include_picks: bool = True
    include_faab: bool = False
    faab_increment: Annotated[int, Field(gt=0)] = 5
    max_faab_options_per_team: Annotated[int, Field(ge=0, le=20)] = 0

    @model_validator(mode="after")
    def validate_bounds(self) -> "TradeSearchBounds":
        if not (self.include_players or self.include_picks or self.include_faab):
            raise ValueError("trade search must include at least one asset type")
        if self.include_faab and self.max_faab_options_per_team == 0:
            raise ValueError("FAAB search requires at least one bounded option")
        return self


class TeamTradeInventory(FrozenModel):
    team_id: str
    assets: tuple[Asset, ...]


class TradePackageSeed(FrozenModel):
    team_id: str
    assets: tuple[Asset, ...]
    canonical_id: str

    @model_validator(mode="after")
    def validate_package(self) -> "TradePackageSeed":
        if not self.team_id.strip() or not self.canonical_id.strip():
            raise ValueError("trade package identifiers cannot be blank")
        if not self.assets:
            raise ValueError("trade package cannot be empty")
        return self


def _asset_key(asset: Asset) -> tuple[str, str]:
    if isinstance(asset, PlayerAsset):
        return ("player", asset.player_id)
    if isinstance(asset, PickAsset):
        return ("pick", asset.pick_id)
    if isinstance(asset, FaabAsset):
        return ("faab", str(asset.amount))
    raise TypeError("unsupported trade asset")


def canonical_package_id(team_id: str, assets: tuple[Asset, ...]) -> str:
    keys = sorted(f"{kind}:{identifier}" for kind, identifier in map(_asset_key, assets))
    return f"{team_id}|" + "+".join(keys)


def build_team_trade_inventory(
    league_state: LeagueState,
    *,
    team_id: str,
    bounds: TradeSearchBounds,
) -> TeamTradeInventory:
    state_by_team = {state.team_id: state for state in league_state.team_states}
    if team_id not in state_by_team:
        raise ValueError("unknown team_id")
    team_state = state_by_team[team_id]

    assets: list[Asset] = []
    if bounds.include_players:
        assets.extend(PlayerAsset(player_id=entry.player_id) for entry in team_state.roster)
    if bounds.include_picks:
        assets.extend(
            PickAsset(pick_id=ownership.pick_id)
            for ownership in league_state.pick_ownership
            if ownership.owner_team_id == team_id
        )
    if bounds.include_faab and team_state.faab_balance > 0:
        options: list[int] = []
        amount = bounds.faab_increment
        while amount <= team_state.faab_balance and len(options) < bounds.max_faab_options_per_team:
            options.append(amount)
            amount += bounds.faab_increment
        if team_state.faab_balance not in options and len(options) < bounds.max_faab_options_per_team:
            options.append(team_state.faab_balance)
        assets.extend(FaabAsset(amount=amount) for amount in options)

    return TeamTradeInventory(team_id=team_id, assets=tuple(assets))


def enumerate_trade_packages(
    inventory: TeamTradeInventory,
    *,
    bounds: TradeSearchBounds,
) -> tuple[TradePackageSeed, ...]:
    """Enumerate bounded legal-owned asset packages without valuation or ranking.

    Multiple FAAB amounts in one package are excluded because they represent
    alternative parameterizations of the same asset class rather than distinct
    simultaneously held assets.
    """

    packages: dict[str, TradePackageSeed] = {}
    max_size = min(bounds.max_assets_per_side, len(inventory.assets))
    for size in range(1, max_size + 1):
        for combo in combinations(inventory.assets, size):
            if sum(isinstance(asset, FaabAsset) for asset in combo) > 1:
                continue
            canonical_id = canonical_package_id(inventory.team_id, combo)
            packages[canonical_id] = TradePackageSeed(
                team_id=inventory.team_id,
                assets=combo,
                canonical_id=canonical_id,
            )
    return tuple(packages[key] for key in sorted(packages))


def enumerate_counterparties(
    league_state: LeagueState,
    *,
    focal_team_id: str,
) -> tuple[str, ...]:
    team_ids = {team.team_id for team in league_state.teams}
    if focal_team_id not in team_ids:
        raise ValueError("unknown focal team")
    return tuple(sorted(team_id for team_id in team_ids if team_id != focal_team_id))
