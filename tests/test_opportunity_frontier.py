from fsffl.opportunity.frontier import (
    canonical_frontier_point_id,
    expand_adjacent_packages,
    make_frontier_point,
)
from fsffl.opportunity.trade_universe import (
    TeamTradeInventory,
    TradePackageSeed,
    TradeSearchBounds,
    canonical_package_id,
)
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset


def _seed(team_id: str, *assets):
    assets = tuple(assets)
    return TradePackageSeed(
        team_id=team_id,
        assets=assets,
        canonical_id=canonical_package_id(team_id, assets),
    )


def test_frontier_adds_and_removes_one_asset_deterministically() -> None:
    p1 = PlayerAsset(player_id="p1")
    p2 = PlayerAsset(player_id="p2")
    pick = PickAsset(pick_id="2027-a-1")
    inventory = TeamTradeInventory(team_id="a", assets=(p1, p2, pick))
    origin = _seed("a", p1, p2)

    neighbors = expand_adjacent_packages(
        origin,
        inventory=inventory,
        bounds=TradeSearchBounds(max_assets_per_side=3),
    )

    ids = [item.package.canonical_id for item in neighbors]
    assert ids == sorted(ids)
    assert canonical_package_id("a", (p1,)) in ids
    assert canonical_package_id("a", (p2,)) in ids
    assert canonical_package_id("a", (p1, p2, pick)) in ids
    assert all(abs(len(item.package.assets) - len(origin.assets)) == 1 for item in neighbors)


def test_frontier_refuses_origin_asset_outside_inventory() -> None:
    inventory = TeamTradeInventory(team_id="a", assets=(PlayerAsset(player_id="p1"),))
    origin = _seed("a", PlayerAsset(player_id="not-owned"))

    try:
        expand_adjacent_packages(
            origin,
            inventory=inventory,
            bounds=TradeSearchBounds(max_assets_per_side=2),
        )
    except ValueError as exc:
        assert "outside the owned inventory" in str(exc)
    else:
        raise AssertionError("expected ownership validation failure")


def test_frontier_respects_package_size_bound() -> None:
    p1 = PlayerAsset(player_id="p1")
    p2 = PlayerAsset(player_id="p2")
    inventory = TeamTradeInventory(team_id="a", assets=(p1, p2))
    origin = _seed("a", p1)

    neighbors = expand_adjacent_packages(
        origin,
        inventory=inventory,
        bounds=TradeSearchBounds(max_assets_per_side=1),
    )

    assert neighbors == ()


def test_frontier_never_combines_multiple_faab_alternatives() -> None:
    p1 = PlayerAsset(player_id="p1")
    faab5 = FaabAsset(amount=5)
    faab10 = FaabAsset(amount=10)
    inventory = TeamTradeInventory(team_id="a", assets=(p1, faab5, faab10))
    origin = _seed("a", faab5)

    neighbors = expand_adjacent_packages(
        origin,
        inventory=inventory,
        bounds=TradeSearchBounds(
            max_assets_per_side=2,
            include_faab=True,
            max_faab_options_per_team=2,
        ),
    )

    assert canonical_package_id("a", (faab5, faab10)) not in {
        item.package.canonical_id for item in neighbors
    }
    assert canonical_package_id("a", (faab5, p1)) in {
        item.package.canonical_id for item in neighbors
    }


def test_bilateral_frontier_point_identity_is_ordered_by_trade_side() -> None:
    focal = _seed("a", PlayerAsset(player_id="p1"))
    counterparty = _seed("b", PickAsset(pick_id="2027-b-1"))
    point = make_frontier_point(focal, counterparty)

    assert point.point_id == canonical_frontier_point_id(
        focal.canonical_id,
        counterparty.canonical_id,
    )
    assert point.point_id != canonical_frontier_point_id(
        counterparty.canonical_id,
        focal.canonical_id,
    )
