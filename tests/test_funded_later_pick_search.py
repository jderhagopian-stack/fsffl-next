from dataclasses import replace
from datetime import datetime, timezone
from fsffl.state.models import PlayerAsset,PickAsset
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.opportunity.strategic_packages import StrategicPackageLane,StrategicSearchBounds
from fsffl.opportunity.guided_strategic_packages import generate_guided_strategic_packages
from fsffl.product.strategic_discovery import _representative_indices,StrategicDiscoveryRequest


def crowded():
    p=PlayerAsset(player_id='player');t=PlayerAsset(player_id='target');p2=PickAsset(pick_id='second');p3=PickAsset(pick_id='third')
    decoys=tuple(PlayerAsset(player_id=f'decoy{i}') for i in range(9))
    lane=StrategicPackageLane('root',TeamTradeInventory(team_id='a',assets=(p,*decoys,p2,p3)),TeamTradeInventory(team_id='b',assets=(t,)),required_send=p,required_receive=t)
    lanes=tuple(replace(lane,name='lane'+str(i)) for i in range(120))
    values={p:1000.,t:1050.,p2:100.,p3:50.,**{a:10000. for a in decoys}}
    return lanes,values,{p2:2,p3:3},p,t,p2,p3


def test_in_range_singleton_keeps_a_funded_second_third_alternative_in_crowded_search():
    lanes,values,rounds,p,t,p2,p3=crowded()
    seeds,diag=generate_guided_strategic_packages(lanes,as_of=datetime(2026,11,24,tzinfo=timezone.utc),
        bounds=StrategicSearchBounds(max_candidates=632,max_pair_visits=632),market_values=values,
        economic_tolerance=237.23160063271538,pick_rounds=rounds)
    assert any(set(s.seed.proposal.side_a.sends)=={p} and set(s.seed.proposal.side_b.sends)=={t} for s in seeds)
    assert any(set(s.seed.proposal.side_a.sends)=={p,p2,p3} and set(s.seed.proposal.side_b.sends)=={t} for s in seeds)
    assert diag['pair_visits']<=632


def test_position_target_requires_player_anchor_but_allows_permitted_pick_sweeteners():
    from fsffl.product.strategic_discovery import _matches_target_package
    from types import SimpleNamespace as NS
    rb=NS(asset_kind='player',detail='RB',age_years=24);wr=NS(asset_kind='player',detail='WR',age_years=24);pick=NS(asset_kind='pick',detail=None,age_years=None)
    req=StrategicDiscoveryRequest(target_position='RB')
    assert _matches_target_package([rb,pick],req)
    assert not _matches_target_package([pick],req)
    assert not _matches_target_package([wr,pick],req)
    assert not _matches_target_package([rb,pick],req.model_copy(update={'target_asset_kinds':('player',)}))
    assert not _matches_target_package([rb,pick],req.model_copy(update={'target_player_max_age':22}))


def test_existing_four_asset_turn_can_screen_funded_terms_without_erasing_singletons():
    rows=[]
    for i,size in enumerate([2,2,4,4]):
        funded=i==3
        rows.append({'point_id':str(i),'send':[{'asset_ref':'player:p'+str(i)}]+([{'asset_ref':'pick:second'},{'asset_ref':'pick:third'}] if funded else [{'asset_ref':'player:extra'+str(j)} for j in range(size-2)]),
            'receive':[{'asset_ref':'player:target'}],'counterparty_team_id':'b'+str(i),'focal_package_family':str(i),
            'hypotheses':['funded_later_pick_terms'] if funded else ['ordinary'],
            'preliminary_economic_band':'robust_or_ordinary','joint_priority_gain_hypothesis':True,
            'search_objectives':['current_competitiveness'],'priority_gain_hints':{'current_competitiveness':1.}})
    chosen=_representative_indices(rows,3)
    assert 3 in chosen and len(chosen)==3 and len(set(chosen))==3
    assert any(i in chosen for i in (0,1))
    rows[3]['preliminary_economic_band']='focal_economic_strain'
    assert 3 not in _representative_indices(rows,3)


def test_funded_terms_work_in_both_trade_directions():
    lanes,values,rounds,p,t,p2,p3=crowded()
    reverse=replace(lanes[0],focal=lanes[0].counterparty,counterparty=lanes[0].focal,required_send=t,required_receive=p)
    seeds,_=generate_guided_strategic_packages((reverse,),as_of=datetime(2026,11,24,tzinfo=timezone.utc),bounds=StrategicSearchBounds(max_candidates=100,max_pair_visits=100),market_values=values,economic_tolerance=237.23160063271538,pick_rounds=rounds)
    assert any(set(s.seed.proposal.side_b.sends)=={p,p2,p3} for s in seeds)


def test_no_funded_label_without_round_or_price_evidence_or_outside_envelope():
    lanes,values,rounds,p,t,p2,p3=crowded()
    for evidence,prices in [({},values),(rounds,{**values,p2:float('nan')}),(rounds,{**values,p2:10000.})]:
        seeds,_=generate_guided_strategic_packages(lanes,as_of=datetime(2026,11,24,tzinfo=timezone.utc),bounds=StrategicSearchBounds(max_candidates=632,max_pair_visits=632),market_values=prices,economic_tolerance=237.23160063271538,pick_rounds=evidence)
        assert not any('funded_later_pick_terms' in s.hypotheses for s in seeds)


def test_position_sweeteners_use_bounded_anchor_lanes_without_replacing_ordinary_coverage():
    from tests.test_strategic_discovery import governed_runtime_fixture
    from fsffl.product.strategic_discovery import build_discovery_lanes
    runtime,_=governed_runtime_fixture(team_count=4)
    req=StrategicDiscoveryRequest(target_position='WR')
    lanes,*_=build_discovery_lanes(runtime,req,None)
    terms=[l for l in lanes if l.name.startswith('position_target_terms:')]
    assert terms and len(terms)<=2*3
    assert all(l.incoming_asset_limit==3 for l in terms)
    positions={p.player_id:p.position.value for p in runtime.league_state.players}
    assert all(isinstance(l.required_receive,PlayerAsset) and positions[l.required_receive.player_id]=='WR' for l in terms)
    assert all(any(isinstance(a,PickAsset) for a in l.counterparty.assets) for l in terms)
    assert all(all(isinstance(a,PlayerAsset) for a in l.counterparty.assets) for l in lanes if l not in terms)
    player_only=StrategicDiscoveryRequest(target_position='WR',target_asset_kinds=('player',))
    assert not any(l.name.startswith('position_target_terms:') for l in build_discovery_lanes(runtime,player_only,None)[0])


def test_position_term_incoming_bound_is_honored_by_guided_and_exploration_lanes():
    p=PlayerAsset(player_id='premium');rb=PlayerAsset(player_id='rb')
    picks=tuple(PickAsset(pick_id='pick'+str(i)) for i in range(8))
    lane=StrategicPackageLane('anchored',TeamTradeInventory(team_id='a',assets=(p,)),TeamTradeInventory(team_id='b',assets=(rb,*picks)),required_receive=rb,incoming_asset_limit=3)
    values={p:1000.,rb:100.,**{a:100. for a in picks}}
    seeds,diag=generate_guided_strategic_packages((lane,),as_of=datetime(2026,11,24,tzinfo=timezone.utc),bounds=StrategicSearchBounds(max_candidates=632,max_pair_visits=632),market_values=values,economic_tolerance=237.23160063271538,pick_rounds={a:2 for a in picks})
    assert seeds and all(len(s.seed.proposal.side_b.sends)<=3 for s in seeds)
    assert all(rb in s.seed.proposal.side_b.sends for s in seeds)
    assert diag['pair_visits']<=632
