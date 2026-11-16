"""Read existing exact-State owner profiles; never acquire or rebuild history."""
from dataclasses import dataclass
from types import MappingProxyType
from .behavioral_runtime import cached_behavior_profile_for_team
from fsffl.trade_decision.owner_history import describe_owner_package_history


@dataclass(frozen=True)
class TradeOwnerHistoryContext:
    state: object
    source_state_id: str
    profiles: object
    player_positions: object


def cached_trade_profiles(runtime, proposal):
    return {leg.team_id:cached_behavior_profile_for_team(runtime.league_state,leg.team_id)
            for leg in (proposal.side_a,proposal.side_b)}


def prepare_trade_owner_history(runtime, proposal=None, *, profiles=None, player_positions=None):
    if profiles is None:
        if proposal is None:
            raise ValueError('A proposal or mapped profiles are required')
        profiles=cached_trade_profiles(runtime,proposal)
    positions=player_positions if player_positions is not None else (
        {p.player_id:p.position.value for p in runtime.league_state.players}
        if any(p is not None and p.completed_trade_activity is not None for p in profiles.values()) else {})
    return TradeOwnerHistoryContext(runtime.league_state,runtime.league_state.state_id,
        MappingProxyType(dict(profiles)),MappingProxyType(dict(positions)))


def build_trade_owner_history(runtime, proposal, *, profiles=None, player_positions=None, context=None):
    context=context or prepare_trade_owner_history(runtime,proposal,profiles=profiles,player_positions=player_positions)
    if context.state is not runtime.league_state or proposal.as_of != runtime.league_state.as_of:
        raise ValueError('Owner history context must match the exact request State and cutoff')
    result={}
    for leg in (proposal.side_a,proposal.side_b):
        other=context.profiles.get(next(l.team_id for l in (proposal.side_a,proposal.side_b) if l.team_id!=leg.team_id))
        result[leg.team_id]=describe_owner_package_history(proposal,team_id=leg.team_id,
            profile=context.profiles.get(leg.team_id),player_positions=context.player_positions,
            source_state_id=context.source_state_id,other_owner_id=other.owner_id if other else None)
    return result
