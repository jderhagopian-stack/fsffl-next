from datetime import UTC, datetime

from fsffl.opportunity.shopping import ShopRequest, build_shop_universe
from fsffl.opportunity.trade_universe import TradeSearchBounds
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
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
PROV = Provenance(
    source="test",
    retrieved_at=AS_OF,
    effective_at=AS_OF,
    provider_ref=ProviderRef(provider="test", external_id="x"),
)


def _state() -> LeagueState:
    league = League(
        league_id="l1",
        name="L",
        season=2026,
        rules=LeagueRules(team_count=3, roster_size=2, lineup=(), scoring=()),
    )
    teams = tuple(
        Team(team_id=tid, league_id="l1", display_name=tid.upper())
        for tid in ("a", "b", "c")
    )
    players = tuple(
        Player(player_id=pid, full_name=pid.upper(), position=Position.WR)
        for pid in ("a1", "b1", "b2", "c1")
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=(RosterEntry(player_id="a1", slot=RosterSlot.BENCH),)),
            TeamState(team_id="b", roster=(RosterEntry(player_id="b1", slot=RosterSlot.BENCH), RosterEntry(player_id="b2", slot=RosterSlot.BENCH))),
            TeamState(team_id="c", roster=(RosterEntry(player_id="c1", slot=RosterSlot.BENCH),)),
        ),
        players=players,
        player_states=tuple(
            PlayerState(player_id=player.player_id, as_of=AS_OF, provenance=PROV)
            for player in players
        ),
    )


def test_shop_universe_enumerates_other_teams_without_inferring_demand() -> None:
    result = build_shop_universe(
        _state(),
        request=ShopRequest(focal_team_id="a", asset=PlayerAsset(player_id="a1")),
        bounds=TradeSearchBounds(max_assets_per_side=1, include_picks=False),
    )

    assert result.focal_package.canonical_id == "a|player:a1"
    assert [item.counterparty_team_id for item in result.counterparties] == ["b", "c"]
    assert result.total_return_packages == 3
    assert {
        package.canonical_id
        for item in result.counterparties
        for package in item.return_packages
    } == {"b|player:b1", "b|player:b2", "c|player:c1"}


def test_shop_universe_rejects_asset_not_owned_by_focal_team() -> None:
    try:
        build_shop_universe(
            _state(),
            request=ShopRequest(focal_team_id="a", asset=PlayerAsset(player_id="b1")),
            bounds=TradeSearchBounds(max_assets_per_side=1, include_picks=False),
        )
    except ValueError as exc:
        assert "owned by focal team" in str(exc)
    else:
        raise AssertionError("expected shop ownership rejection")
