from datetime import UTC, datetime

import pytest

from fsffl.product.trade_center import (
    TradeDraft,
    TradeDraftSide,
    add_asset_to_draft,
    remove_asset_from_draft,
    submit_trade_draft,
)
from fsffl.product.trade_center_view import (
    TeamTradeBrowser,
    TradeAssetOption,
    TradeCenterBrowserView,
    asset_from_trade_option,
    owned_asset_index,
)
from fsffl.state.models import PickAsset, PlayerAsset


def _empty_draft() -> TradeDraft:
    return TradeDraft(
        draft_id="d1",
        focal_team_id="a",
        counterparty_team_id="b",
        focal_side=TradeDraftSide(team_id="a"),
        counterparty_side=TradeDraftSide(team_id="b"),
    )


def test_trade_builder_can_start_empty() -> None:
    draft = _empty_draft()
    assert not draft.ready_to_submit


def test_trade_draft_edits_are_immutable_and_do_not_evaluate() -> None:
    draft = _empty_draft()
    player = PlayerAsset(player_id="p1")
    updated = add_asset_to_draft(draft, team_id="a", asset=player)
    assert draft.focal_side.assets == ()
    assert updated.focal_side.assets == (player,)

    removed = remove_asset_from_draft(updated, team_id="a", asset=player)
    assert removed.focal_side.assets == ()


def test_trade_submission_requires_assets_from_both_teams() -> None:
    draft = add_asset_to_draft(_empty_draft(), team_id="a", asset=PlayerAsset(player_id="p1"))
    with pytest.raises(ValueError, match="at least one asset from each team"):
        submit_trade_draft(draft, as_of=datetime(2026, 9, 5, tzinfo=UTC))


def test_trade_submission_uses_next5_proposal_contract() -> None:
    draft = _empty_draft()
    draft = add_asset_to_draft(draft, team_id="a", asset=PlayerAsset(player_id="p1"))
    draft = add_asset_to_draft(draft, team_id="b", asset=PickAsset(pick_id="pick-b"))
    proposal = submit_trade_draft(
        draft,
        as_of=datetime(2026, 9, 5, tzinfo=UTC),
        proposal_id="proposal-1",
    )
    assert proposal.proposal_id == "proposal-1"
    assert proposal.side_a.team_id == "a"
    assert proposal.side_b.team_id == "b"
    assert proposal.side_a.sends == (PlayerAsset(player_id="p1"),)
    assert proposal.side_b.sends == (PickAsset(pick_id="pick-b"),)


def test_owned_asset_index_reuses_exact_canonical_asset_conversion() -> None:
    player_option = TradeAssetOption(
        asset_ref="player:p1",
        asset_kind="player",
        label="Player One",
        detail="RB",
        player_id="p1",
    )
    pick_option = TradeAssetOption(
        asset_ref="pick:pick-b",
        asset_kind="pick",
        label="2027 Round 1",
        detail="Originally B",
        pick_id="pick-b",
    )
    view = TradeCenterBrowserView(
        focal_team=TeamTradeBrowser(
            team_id="a",
            display_name="A",
            assets=(player_option,),
            faab_balance=100,
        ),
        counterparties=(
            TeamTradeBrowser(
                team_id="b",
                display_name="B",
                assets=(pick_option,),
                faab_balance=100,
            ),
        ),
        state_id="state-1",
    )

    indexed = owned_asset_index(view)

    assert indexed[("a", "player:p1")] == asset_from_trade_option(player_option)
    assert indexed[("a", "player:p1")] == PlayerAsset(player_id="p1")
    assert indexed[("b", "pick:pick-b")] == asset_from_trade_option(pick_option)
    assert indexed[("b", "pick:pick-b")] == PickAsset(pick_id="pick-b")
