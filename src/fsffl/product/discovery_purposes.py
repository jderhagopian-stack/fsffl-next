"""Assemble bounded search purposes from existing State, Utility and history.

These are reasons to investigate exchanges, not new values or owner policy.
"""
from math import isfinite
from fsffl.opportunity.strategic_packages import StrategicPackageLane, StrategicPurpose
from fsffl.state.models import PlayerAsset, PickAsset
from fsffl.trade_decision.objectives import TradeObjective as G

MAX_UPGRADE_TARGETS_PER_POSITION = 2  # Search coverage, not economic significance.


def matching_published_lineups(runtime):
    simulation=runtime.simulation_analytics
    if simulation is None or simulation.league_view.context.league_state_id!=runtime.league_state.state_id:return {}
    from .simulation_forecasts import current_forecast_coordinates
    try:_,horizon,cutoff=current_forecast_coordinates(runtime.league_state,runtime.forecast_evidence)
    except (ValueError,AttributeError):return {}
    return {v.team_id:v.optimized_lineup for v in simulation.team_views
        if v.optimized_lineup is not None and v.optimized_lineup.horizon==horizon and v.optimized_lineup.as_of<=cutoff}


def pair_purpose_lanes(*,state_id,focal,other,context,other_context,strengths,lineups,metrics,
                       positions,ages,roster_fit,required_send,required_receive,interests):
    lanes=[]
    current=metrics[G.CURRENT]
    def ref(a):return f'player:{a.player_id}' if isinstance(a,PlayerAsset) else f'pick:{a.pick_id}'
    def ranked(items,values):return tuple(sorted(items,key=lambda a:(a not in values,-values.get(a,0),ref(a))))
    def players(items):return tuple(a for a in items if isinstance(a,PlayerAsset))
    def picks(items):return tuple(a for a in items if isinstance(a,PickAsset))
    def add(kind,sends,receives,*,actor=None,position=None,horizon=None,interest=None,target=None,offer=None,asset_focus=None):
        if not sends or not receives:return
        if required_send is not None and required_send not in sends:return
        if required_receive is not None and required_receive not in receives:return
        if target is not None and required_receive is not None and target!=required_receive:return
        if offer is not None and required_send is not None and offer!=required_send:return
        actor=actor or focal.team_id
        purpose=StrategicPurpose(kind=kind,team_id=actor,partner_team_id=other.team_id if actor==focal.team_id else focal.team_id,
            source_state_id=state_id,position=position,horizon=horizon,asset_focus=asset_focus,
            interest_kind=interest.kind if interest else None,
            evidence_event_ids=interest.event_ids if interest else (),
            observed_trade_count=interest.trade_count if interest else None)
        name='purpose:'+kind+':'+('focal' if actor==focal.team_id else 'partner')+':'+(position or horizon or (interest.kind if interest else 'capital'))
        # An upgrade target or bench-conversion send must actually occur in every
        # generated proposal for that lane, including price-envelope construction.
        if target is not None:name+=':'+ref(target)
        if offer is not None:name+=':'+ref(offer)
        if asset_focus is not None:name+=':'+asset_focus
        lanes.append(StrategicPackageLane(name,focal.model_copy(update={'assets':tuple(sends)}),
            other.model_copy(update={'assets':tuple(receives)}),required_send=offer or required_send,
            required_receive=target or required_receive,purpose=purpose))
    # Competitive outlook orders motivations; it never excludes another owner.
    future_other=next((g for g in other_context.objectives if g in (G.THREE_YEAR,G.CAREER)),None)
    supply=(roster_fit(focal.assets,other.team_id) if G.CURRENT in other_context.objectives or future_other is None
        else ranked(focal.assets,metrics[future_other]))
    focal_lineup=lineups.get(focal.team_id)
    other_lineup=lineups.get(other.team_id)
    if focal_lineup is not None:
        assigned={a.player_id:a.expected_points for a in focal_lineup.assignments}
        # Generate affordable improvements before offering a franchise cornerstone.
        # This estimates displaced starter production only to order ingredients;
        # the full weekly/cut screen still owns the actual consequences.
        bench_by_position={p:max((current.get(a,0.) for a in players(focal.assets)
            if positions.get(a.player_id)==p and a.player_id in focal_lineup.bench_player_ids),default=0.)
            for p in set(positions.values())}
        def release_cost(a):
            if not isinstance(a,PlayerAsset):return (1,0.,ref(a))
            if a not in current:return (2,0.,ref(a))
            cost=max(0.,assigned.get(a.player_id,0.)-bench_by_position.get(positions.get(a.player_id),0.))
            return (0,cost,-current[a],ref(a))
        ordered=tuple(sorted(focal.assets,key=release_cost))
        benches=tuple(a for a in ordered if isinstance(a,PlayerAsset) and a.player_id not in assigned)
        starters=tuple(a for a in ordered if isinstance(a,PlayerAsset) and a.player_id in assigned)
        from itertools import zip_longest
        upgrade_supply=tuple(a for pair in zip_longest(benches,starters) for a in pair if a is not None)
        upgrade_supply+=tuple(a for a in ordered if not isinstance(a,PlayerAsset))
        weak=sorted((r for r in strengths.get(focal.team_id,{}).values()
            if r.starter_count>0 and r.strength_index is not None),
            key=lambda r:(r.strength_index,r.position.value))
        for strength in weak:
            floors=[a.expected_points for a in focal_lineup.assignments if a.position==strength.position]
            if not floors:continue
            candidates=[a for a in players(other.assets) if positions.get(a.player_id)==strength.position
                and a in current and current[a]>min(floors)]
            if required_receive is not None:candidates=[a for a in candidates if a==required_receive]
            for target in ranked(candidates,current)[:MAX_UPGRADE_TARGETS_PER_POSITION]:
                add('improve_lineup',upgrade_supply,roster_fit(other.assets,focal.team_id),
                    position=strength.position.value,target=target)
        # Bench membership is only a starting hypothesis. Full weekly replacement,
        # cuts and both-team objectives must still be evaluated for every package.
        if other_lineup is not None:
            floor={p:min(a.expected_points for a in other_lineup.assignments if a.position==p)
                for p in {a.position for a in other_lineup.assignments}}
            convertible=[a for a in players(focal.assets) if a.player_id in focal_lineup.bench_player_ids
                and a in current and positions.get(a.player_id) in floor
                and current[a]>floor[positions[a.player_id]]]
            for offer in ranked(convertible,current)[:2]:
                add('test_depth_conversion',tuple(convertible),picks(other.assets),offer=offer,
                    position=positions[offer.player_id].value)
    for goal in context.objectives:
        if goal not in (G.THREE_YEAR,G.CAREER):continue
        # Current ages are valid for current targets, never historical preferences.
        younger=tuple(a for a in players(other.assets) if a.player_id in ages and 0<=ages[a.player_id]<27)
        add('acquire_future_assets',supply,ranked(younger,metrics[goal]),horizon=goal.value,asset_focus='young_players')
        add('acquire_future_assets',supply,ranked(picks(other.assets),metrics[goal]),horizon=goal.value,asset_focus='picks')
    # Positive observations add avenues for either franchise, independent of its
    # inferred competitive label. No observations remove an ordinary search lane.
    for actor,inventory,partner in ((focal.team_id,focal,other),(other.team_id,other,focal)):
        for interest in interests.get(actor,()):
            candidates=picks(partner.assets) if interest.kind=='pick' else tuple(a for a in players(partner.assets)
                if positions.get(a.player_id) is not None and positions[a.player_id].value==interest.position)
            if actor==other.team_id:
                add('observed_acquisition',candidates,roster_fit(other.assets,focal.team_id),
                    actor=actor,position=interest.position,interest=interest)
            else:
                add('observed_acquisition',supply,candidates,actor=actor,position=interest.position,interest=interest)
    return tuple(lanes)


def purpose_catalog(lanes):
    return {(lane.counterparty.team_id,lane.name):lane.purpose.model_dump(mode='json')
        for lane in lanes if lane.purpose is not None}


def package_purposes(catalog, *, team_id, hypotheses):
    return [dict(catalog[(team_id,name)]) for name in hypotheses if (team_id,name) in catalog]


def review_purposes(row):
    """Describe the actual preliminary effects without changing any Decision."""
    for p in row.get('discovery_purposes',()):
        p['result']='unexamined'
        if row.get('evidence_status')!='pre_simulation_screened':continue
        label='side_a' if p['team_id']==row.get('focal_team_id') else 'side_b'
        screen=row.get('preliminary_decision_screen') or {}
        side=screen.get('focal' if label=='side_a' else 'counterparty') or {}
        points=side.get('starter_points_delta')
        known=isinstance(points,(int,float)) and isfinite(points)
        p['result']='not_confirmed'
        if p['kind']=='observed_acquisition':p['result']='observed_history_only'
        elif p['kind']=='improve_lineup':
            comparison=(row.get('position_strength_comparisons') or {}).get(p['team_id']) or {}
            pos=next((r for r in comparison.get('positions',()) if r['position']==p['position']),{})
            if known and points>1e-9 and pos.get('expected_points_delta',0)>0:p['result']='lineup_gain'
        elif p['kind']=='test_depth_conversion':
            if known and points>=-1e-9 and screen.get('current_points_basis')=='remaining_regular_season_weekly_mean':
                p['result']='current_lineup_preserved'
            p['surplus_confirmed']=False
        elif p['kind']=='acquire_future_assets':
            horizon={'three_year_contribution':'three_year','career_contribution':'career'}.get(p['horizon'])
            value=(((row.get('horizon_asset_economics') or {}).get(horizon) or {}).get('roster_adjusted') or {}).get(label) or {}
            delta=value.get('roster_adjusted_intrinsic_delta')
            if value.get('status')=='complete' and isinstance(delta,(int,float)) and isfinite(delta) and delta>0:
                p['result']='asset_contribution_gain'

