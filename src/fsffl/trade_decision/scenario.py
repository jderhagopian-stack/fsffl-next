from __future__ import annotations

from fsffl.state.models import (
    FaabAsset,
    LeagueState,
    PickAsset,
    PickOwnership,
    PlayerAsset,
    RosterEntry,
    RosterSlot,
    TeamState,
)

from .models import BilateralTradeProposal, TradeLeg


class AppliedTradeScenario:
    """Immutable before/after state pair for a validated bilateral proposal."""

    __slots__ = ("before", "after", "proposal")

    def __init__(self, *, before: LeagueState, after: LeagueState, proposal: BilateralTradeProposal) -> None:
        self.before = before
        self.after = after
        self.proposal = proposal


def _validate_leg_ownership(
    league_state: LeagueState,
    leg: TradeLeg,
) -> None:
    team_states = {state.team_id: state for state in league_state.team_states}
    if leg.team_id not in team_states:
        raise ValueError(f"unknown trade team: {leg.team_id}")

    team_state = team_states[leg.team_id]
    roster_ids = {entry.player_id for entry in team_state.roster}
    pick_owner = {ownership.pick_id: ownership.owner_team_id for ownership in league_state.pick_ownership}

    faab_sent = 0
    for asset in leg.sends:
        if isinstance(asset, PlayerAsset):
            if asset.player_id not in roster_ids:
                raise ValueError(f"team {leg.team_id} does not roster player {asset.player_id}")
        elif isinstance(asset, PickAsset):
            if pick_owner.get(asset.pick_id) != leg.team_id:
                raise ValueError(f"team {leg.team_id} does not own pick {asset.pick_id}")
        elif isinstance(asset, FaabAsset):
            faab_sent += asset.amount

    if faab_sent > team_state.faab_balance:
        raise ValueError(f"team {leg.team_id} cannot send more FAAB than it owns")


def _apply_leg(
    *,
    sender: TradeLeg,
    receiver: TradeLeg,
    team_state_map: dict[str, TeamState],
    pick_owner_map: dict[str, str],
) -> None:
    sender_state = team_state_map[sender.team_id]
    receiver_state = team_state_map[receiver.team_id]

    sent_player_ids = {
        asset.player_id for asset in sender.sends if isinstance(asset, PlayerAsset)
    }
    sender_roster = tuple(
        entry for entry in sender_state.roster if entry.player_id not in sent_player_ids
    )
    receiver_roster = receiver_state.roster + tuple(
        RosterEntry(player_id=player_id, slot=RosterSlot.BENCH)
        for player_id in sorted(sent_player_ids)
    )

    faab_sent = sum(asset.amount for asset in sender.sends if isinstance(asset, FaabAsset))

    team_state_map[sender.team_id] = TeamState(
        team_id=sender.team_id,
        roster=sender_roster,
        faab_balance=sender_state.faab_balance - faab_sent,
    )
    team_state_map[receiver.team_id] = TeamState(
        team_id=receiver.team_id,
        roster=receiver_roster,
        faab_balance=receiver_state.faab_balance + faab_sent,
    )

    for asset in sender.sends:
        if isinstance(asset, PickAsset):
            pick_owner_map[asset.pick_id] = receiver.team_id


def apply_bilateral_trade(
    league_state: LeagueState,
    proposal: BilateralTradeProposal,
) -> AppliedTradeScenario:
    """Apply a proposal to canonical state without mutating the source snapshot.

    This function owns transaction-state integrity only. It does not optimize
    lineups, value assets, calculate utility, infer cuts, or recommend the trade.
    Incoming players are placed on BENCH so downstream NEXT-4 can optimize the
    resulting roster independently of the sender's prior slot assignment.
    """

    if league_state.as_of > proposal.as_of:
        raise ValueError("trade proposal cannot use league state from the future")

    _validate_leg_ownership(league_state, proposal.side_a)
    _validate_leg_ownership(league_state, proposal.side_b)

    team_state_map = {state.team_id: state for state in league_state.team_states}
    pick_owner_map = {
        ownership.pick_id: ownership.owner_team_id
        for ownership in league_state.pick_ownership
    }

    # Apply both legs against ownership validated on the same before-state.
    _apply_leg(
        sender=proposal.side_a,
        receiver=proposal.side_b,
        team_state_map=team_state_map,
        pick_owner_map=pick_owner_map,
    )
    _apply_leg(
        sender=proposal.side_b,
        receiver=proposal.side_a,
        team_state_map=team_state_map,
        pick_owner_map=pick_owner_map,
    )

    after = league_state.model_copy(
        update={
            "as_of": proposal.as_of,
            "team_states": tuple(
                team_state_map[team.team_id] for team in league_state.teams
            ),
            "pick_ownership": tuple(
                PickOwnership(pick_id=pick.pick_id, owner_team_id=pick_owner_map[pick.pick_id])
                for pick in league_state.draft_picks
                if pick.pick_id in pick_owner_map
            ),
        }
    )
    # Re-validate copied state after the explicit updates.
    after = LeagueState.model_validate(after.model_dump(mode="python"))

    return AppliedTradeScenario(before=league_state, after=after, proposal=proposal)
