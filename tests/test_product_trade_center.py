from datetime import UTC, datetime

import pytest

from fsffl.product.trade_center import (
    TradeDraft,
    TradeDraftSide,
    add_asset_to_draft,
    remove_asset_from_draft,
    submit_trade_draft,
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
