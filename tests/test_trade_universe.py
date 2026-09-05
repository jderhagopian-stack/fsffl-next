from datetime import UTC, datetime

from fsffl.opportunity.trade_universe import (
    TradeSearchBounds,
    build_team_trade_inventory,
    canonical_package_id,
    enumerate_counterparties,
    enumerate_trade_packages,
)
from fsffl.state.models import (
    DraftPick,
    FaabAsset,
    League,
    LeagueRules,
    LeagueState,
    PickOwnership,
    Player,
    PlayerAsset,
    PlayerState,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)

AS_OF = datetime(2026, 9, 5, tzinfo=UTC)
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF, provider_ref=ProviderRef(provider="test", external_id="x"))


def _state() -> LeagueState:
    league = League(
        league_id="l1",
        name="L",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=3,
            lineup=(),
            scoring=(),
        ),
    )
    teams = (
        Team(team_id="a", league_id="l1", display_name="A"),
        Team(team_id="b", league_id="l1", display_name="B"),
    )
    players = (
        Player(player_id="p1", full_name="P1", position=Position.QB),
        Player(player_id="p2", full_name="P2", position=Position.RB),
        Player(player_id="p3", full_name="P3", position=Position.WR),
    )
    player_states = tuple(PlayerState(player_id=p.player_id, as_of=AS_OF, provenance=PROV) for p in players)
    draft_picks = (DraftPick(pick_id="pick-a", league_id="l1", season=2027, round=1, original_team_id="a"),)
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.BENCH), RosterEntry(player_id="p2", slot=RosterSlot.BENCH)), faab_balance=12),
            TeamState(team_id="b", roster=(RosterEntry(player_id="p3", slot=RosterSlot.BENCH),), faab_balance=0),
        ),
        players=players,
        player_states=player_states,
        draft_picks=draft_picks,
        pick_ownership=(PickOwnership(pick_id="pick-a", owner_team_id="a"),),
    )


def test_counterparties_exclude_focal_team() -> None:
    assert enumerate_counterparties(_state(), focal_team_id="a") == ("b",)


def test_inventory_contains_only_owned_assets() -> None:
    inventory = build_team_trade_inventory(
        _state(),
        team_id="a",
        bounds=TradeSearchBounds(include_faab=False),
    )
    keys = {canonical_package_id("a", (asset,)) for asset in inventory.assets}
    assert "a|player:p1" in keys
    assert "a|player:p2" in keys
    assert "a|pick:pick-a" in keys
    assert "a|player:p3" not in keys


def test_package_identity_is_order_independent() -> None:
    left = canonical_package_id("a", (PlayerAsset(player_id="p1"), PlayerAsset(player_id="p2")))
    right = canonical_package_id("a", (PlayerAsset(player_id="p2"), PlayerAsset(player_id="p1")))
    assert left == right


def test_faab_options_are_bounded_and_not_combined_with_each_other() -> None:
    bounds = TradeSearchBounds(
        max_assets_per_side=2,
        include_players=False,
        include_picks=False,
        include_faab=True,
        faab_increment=5,
        max_faab_options_per_team=3,
    )
    inventory = build_team_trade_inventory(_state(), team_id="a", bounds=bounds)
    assert tuple(asset.amount for asset in inventory.assets if isinstance(asset, FaabAsset)) == (5, 10, 12)
    packages = enumerate_trade_packages(inventory, bounds=bounds)
    assert len(packages) == 3
    assert all(len(package.assets) == 1 for package in packages)


def test_package_generation_respects_explicit_bound() -> None:
    bounds = TradeSearchBounds(max_assets_per_side=1, include_faab=False)
    inventory = build_team_trade_inventory(_state(), team_id="a", bounds=bounds)
    packages = enumerate_trade_packages(inventory, bounds=bounds)
    assert packages
    assert all(len(package.assets) == 1 for package in packages)
