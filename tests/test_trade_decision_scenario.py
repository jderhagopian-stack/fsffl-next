from datetime import UTC, datetime

import pytest

from fsffl.state.models import (
    DraftPick,
    FaabAsset,
    League,
    LeagueRules,
    LeagueState,
    PickAsset,
    PickOwnership,
    Player,
    PlayerAsset,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.trade_decision import BilateralTradeProposal, TradeLeg, apply_bilateral_trade

AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)
PROVENANCE = Provenance(source="trade-test", retrieved_at=AS_OF, effective_at=AS_OF)


def _state() -> LeagueState:
    return LeagueState(
        league=League(
            league_id="league:test",
            name="Trade Test",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=3, lineup=(), scoring=()),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="A", league_id="league:test", display_name="A"),
            Team(team_id="B", league_id="league:test", display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="A",
                roster=(RosterEntry(player_id="p1", slot=RosterSlot.QB),),
                faab_balance=70,
            ),
            TeamState(
                team_id="B",
                roster=(RosterEntry(player_id="p2", slot=RosterSlot.WR),),
                faab_balance=30,
            ),
        ),
        players=(
            Player(player_id="p1", full_name="P1", position=Position.QB),
            Player(player_id="p2", full_name="P2", position=Position.WR),
        ),
        player_states=(
            PlayerState(player_id="p1", as_of=AS_OF, status=PlayerStatus.ACTIVE, provenance=PROVENANCE),
            PlayerState(player_id="p2", as_of=AS_OF, status=PlayerStatus.ACTIVE, provenance=PROVENANCE),
        ),
        draft_picks=(
            DraftPick(
                pick_id="pick:A:2027:1",
                league_id="league:test",
                season=2027,
                round=1,
                original_team_id="A",
            ),
            DraftPick(
                pick_id="pick:B:2027:2",
                league_id="league:test",
                season=2027,
                round=2,
                original_team_id="B",
            ),
        ),
        pick_ownership=(
            PickOwnership(pick_id="pick:A:2027:1", owner_team_id="A"),
            PickOwnership(pick_id="pick:B:2027:2", owner_team_id="B"),
        ),
    )


def _proposal() -> BilateralTradeProposal:
    return BilateralTradeProposal(
        proposal_id="proposal:1",
        as_of=AS_OF,
        side_a=TradeLeg(
            team_id="A",
            sends=(
                PlayerAsset(player_id="p1"),
                PickAsset(pick_id="pick:A:2027:1"),
                FaabAsset(amount=10),
            ),
        ),
        side_b=TradeLeg(
            team_id="B",
            sends=(PlayerAsset(player_id="p2"), PickAsset(pick_id="pick:B:2027:2")),
        ),
    )


def test_trade_applies_immutably_and_transfers_all_supported_assets() -> None:
    before = _state()
    before_id = before.state_id

    scenario = apply_bilateral_trade(before, _proposal())

    assert before.state_id == before_id
    assert {entry.player_id for entry in before.team_states[0].roster} == {"p1"}

    states = {state.team_id: state for state in scenario.after.team_states}
    assert {entry.player_id for entry in states["A"].roster} == {"p2"}
    assert {entry.player_id for entry in states["B"].roster} == {"p1"}
    assert all(entry.slot == RosterSlot.BENCH for state in states.values() for entry in state.roster)
    assert states["A"].faab_balance == 60
    assert states["B"].faab_balance == 40

    owners = {ownership.pick_id: ownership.owner_team_id for ownership in scenario.after.pick_ownership}
    assert owners["pick:A:2027:1"] == "B"
    assert owners["pick:B:2027:2"] == "A"


def test_wrong_player_owner_fails_closed() -> None:
    proposal = BilateralTradeProposal(
        proposal_id="bad-owner",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(PlayerAsset(player_id="p2"),)),
        side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p1"),)),
    )
    with pytest.raises(ValueError, match="does not roster player"):
        apply_bilateral_trade(_state(), proposal)


def test_wrong_pick_owner_fails_closed() -> None:
    proposal = BilateralTradeProposal(
        proposal_id="bad-pick-owner",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(PickAsset(pick_id="pick:B:2027:2"),)),
        side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
    )
    with pytest.raises(ValueError, match="does not own pick"):
        apply_bilateral_trade(_state(), proposal)


def test_faab_cannot_exceed_before_state_balance() -> None:
    proposal = BilateralTradeProposal(
        proposal_id="bad-faab",
        as_of=AS_OF,
        side_a=TradeLeg(team_id="A", sends=(FaabAsset(amount=71),)),
        side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p2"),)),
    )
    with pytest.raises(ValueError, match="more FAAB"):
        apply_bilateral_trade(_state(), proposal)


def test_future_league_state_is_rejected() -> None:
    proposal = _proposal().model_copy(update={"as_of": datetime(2026, 9, 4, 16, 0, tzinfo=UTC)})
    with pytest.raises(ValueError, match="future"):
        apply_bilateral_trade(_state(), proposal)


def test_same_player_cannot_be_sent_by_both_sides() -> None:
    with pytest.raises(ValueError, match="same player"):
        BilateralTradeProposal(
            proposal_id="duplicate-player",
            as_of=AS_OF,
            side_a=TradeLeg(team_id="A", sends=(PlayerAsset(player_id="p1"),)),
            side_b=TradeLeg(team_id="B", sends=(PlayerAsset(player_id="p1"),)),
        )
