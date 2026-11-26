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

    team_state_map[sender.team_id] = sender_state.model_copy(update={
        "roster": sender_roster, "faab_balance": sender_state.faab_balance - faab_sent,
    })
    team_state_map[receiver.team_id] = receiver_state.model_copy(update={
        "roster": receiver_roster, "faab_balance": receiver_state.faab_balance + faab_sent,
    })

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


def apply_bilateral_trade_with_ir_placements(league_state, proposal):
    """Plan legal incoming NFL-IR placements before any lineup/cut evaluation.

    Raw ownership application remains available independently. Only incoming
    players with explicit, knowable NFL IR evidence can fill a vacant IR slot,
    and only to resolve active overflow. No taxi promotion/demotion, medical
    inference, starter optimization or Value-dependent choice occurs here.
    """
    scenario = apply_bilateral_trade(league_state, proposal)
    state = scenario.after
    rules = state.league.rules
    latest = {}
    for fact in state.player_states:
        if fact.as_of > league_state.as_of or fact.provenance.effective_at > league_state.as_of or fact.provenance.retrieved_at > league_state.as_of:
            continue
        if fact.player_id not in latest or fact.as_of > latest[fact.player_id].as_of:
            latest[fact.player_id] = fact
    incoming = {leg.team_id: {a.player_id for a in other.sends if isinstance(a, PlayerAsset)}
                for leg, other in ((proposal.side_a, proposal.side_b), (proposal.side_b, proposal.side_a))}
    teams = []
    for team in state.team_states:
        active = [r for r in team.roster if r.slot not in (RosterSlot.IR, RosterSlot.TAXI)]
        needed = max(0, len(active) - rules.roster_size)
        free = max(0, rules.ir_size - sum(r.slot == RosterSlot.IR for r in team.roster))
        candidates = sorted(r.player_id for r in active
            if r.player_id in incoming.get(team.team_id, ())
            and r.player_id in latest and latest[r.player_id].nfl_injured_reserve is True)
        moved = set(candidates[:min(needed, free)])
        teams.append(team.model_copy(update={'roster': tuple(
            r.model_copy(update={'slot': RosterSlot.IR}) if r.player_id in moved else r for r in team.roster)}))
    after = state.model_copy(update={'team_states': tuple(teams)})
    return AppliedTradeScenario(before=league_state, after=LeagueState.model_validate(after.model_dump(mode='python')), proposal=proposal)
