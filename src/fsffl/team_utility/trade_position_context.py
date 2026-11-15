"""Describe existing optimized lineups; do not infer surplus from roster counts."""
from fsffl.state.models import PlayerAsset, PickAsset


def summarize_trade_position_context(before_state, after_state, before, after, leg, received_assets=()):
    if before.team_id != after.team_id or before.team_id != leg.team_id:
        raise ValueError('Position context must describe the same team')
    if before.horizon != after.horizon or before.as_of != after.as_of:
        raise ValueError('Position context requires matching forecast coordinates')
    if before_state.league.league_id != after_state.league.league_id:
        raise ValueError('Position context requires the same league')
    players = {p.player_id: p for p in before_state.players}
    before_assign = {a.player_id: a for a in before.assignments}
    after_assign = {a.player_id: a for a in after.assignments}
    outgoing = tuple(a.player_id for a in leg.sends if isinstance(a, PlayerAsset))
    removed = set(before_assign) - set(after_assign)
    added = set(after_assign) - set(before_assign)
    roster_before = {r.player_id for t in before_state.team_states if t.team_id == leg.team_id for r in t.roster}
    roster_after = {r.player_id for t in after_state.team_states if t.team_id == leg.team_id for r in t.roster}
    affected = set(outgoing) | (roster_before ^ roster_after)
    positions = sorted({players[pid].position.value for pid in affected if pid in players})
    def group(ids, position):
        return tuple(sorted(pid for pid in ids if pid in players and players[pid].position.value == position))
    rows = []
    for position in positions:
        rows.append({'position': position,
            'incoming_player_ids': group(roster_after - roster_before, position),
            'removed_nontrade_player_ids': group(roster_before - roster_after - set(outgoing), position),
            'before_starter_ids': group(before_assign, position),
            'after_starter_ids': group(after_assign, position),
            'before_forecasted_bench_ids': group(before.bench_player_ids, position),
            'after_forecasted_bench_ids': group(after.bench_player_ids, position),
            'outgoing_starter_ids': tuple(pid for pid in outgoing if pid in before_assign and players[pid].position.value == position),
            'outgoing_bench_ids': tuple(pid for pid in outgoing if pid in before.bench_player_ids and players[pid].position.value == position),
            'outgoing_unavailable_ids': tuple(pid for pid in outgoing if pid in before.unavailable_player_ids and players[pid].position.value == position),
            'outgoing_missing_forecast_ids': tuple(pid for pid in outgoing if pid in before.missing_forecast_player_ids and players[pid].position.value == position)})
    return {'team_id':leg.team_id, 'status':'complete', 'basis':'optimized_horizon_lineup',
        'source_state_id':before_state.state_id,'after_state_id':after_state.state_id,
        'horizon':before.horizon.value, 'as_of':before.as_of.isoformat(),
        'before_expected_points':before.expected_points,'after_expected_points':after.expected_points,
        'expected_points_delta':after.expected_points-before.expected_points,
        'departing_lineup_ids':tuple(sorted(removed)), 'entering_lineup_ids':tuple(sorted(added)),
        'before_unfilled_slots':len(before.unfilled_slots),'after_unfilled_slots':len(after.unfilled_slots),
        'positions':rows, 'received_pick_ids':tuple(a.pick_id for a in received_assets if isinstance(a, PickAsset)),
        'surplus_confirmed':False,
        'interpretation':'Projected roles only; weekly availability, resilience and competitive effects remain separate',
        'model_version':'next4-trade-position-context-v1'}
