from dataclasses import replace
from types import SimpleNamespace as NS
from copy import deepcopy

import pytest
from fsffl.state.models import PlayerAsset,PickAsset
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.product.strategic_compensation import compensation_path
from fsffl.product.strategic_feedback import FeedbackVisits
from tests.test_shortlist_quality import evaluated


def fixture():
    a,b=PlayerAsset(player_id='a'),PlayerAsset(player_id='b')
    p,q=PickAsset(pick_id='p'),PickAsset(pick_id='q')
    root=evaluated(current=(.8,3),three=(-420,420),career=(-493,493))
    root.update(counterparty_team_id='b',send=[{'asset_ref':'player:a'}],receive=[{'asset_ref':'player:b'}])
    root['objective_assessment']['side_a']['context']['objectives']=['current_competitiveness','three_year_contribution','career_contribution']
    inventories={'a':TeamTradeInventory(team_id='a',assets=(a,)),
                 'b':TeamTradeInventory(team_id='b',assets=(b,p,q))}
    read=NS(pick_sources={'p':{'release_id':'fixture'},'q':{'release_id':'fixture'}},values={'three_year':{},'career':{}},pick_values={'three_year':{'p':300,'q':150},'career':{'p':350,'q':200}})
    return NS(selected_team_id='a'),root,read,inventories


def test_two_counted_owned_picks_can_repair_native_deficits_without_changing_root_values():
    runtime,root,read,inventories=fixture();before=deepcopy(root)
    visits=FeedbackVisits(8)
    path=list(compensation_path(runtime,root,read,inventories=inventories,visits=visits))
    assert len(path)==visits.used==2
    assert path[0][1]['move']=='add_native_compensation'
    assert path[1][1]['parent_point_id']==path[0][0].point_id
    assert path[1][0].counterparty_package.assets==(PlayerAsset(player_id='b'),PickAsset(pick_id='p'),PickAsset(pick_id='q'))
    assert path[1][0].focal_package.assets==(PlayerAsset(player_id='a'),)
    assert all(l['hypothesis_only'] for _,l in path) and root==before


@pytest.mark.parametrize('change',['budget','missing','protected','foreign','unscreened'])
def test_compensation_cannot_bypass_coverage_protection_ownership_or_counted_budget(change):
    runtime,root,read,inventories=fixture();visits=FeedbackVisits(0 if change=='budget' else 8)
    if change=='missing':read.pick_values['career']={}
    if change=='protected':root['objective_assessment']['side_a']['protected_players_lost']=['a']
    if change=='foreign':root['receive']=[{'asset_ref':'player:a'}]
    if change=='unscreened':root['evidence_status']='not_roster_screened'
    assert not list(compensation_path(runtime,root,read,inventories=inventories,visits=visits))
    assert visits.used==0


@pytest.mark.parametrize('superflex',[False,True])
@pytest.mark.parametrize('required_offer',[False,True])
def test_actual_native_cut_lineup_screens_can_turn_a_costly_root_into_a_compensated_fit(monkeypatch,superflex,required_offer):
    from fsffl.product import strategic_discovery as module,trade_objectives
    from fsffl.product.strategic_discovery import StrategicDiscoveryRequest
    from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
    from fsffl.trade_decision.objectives import OwnerObjectiveContext
    from fsffl.opportunity.strategic_packages import StrategicSeed
    from fsffl.opportunity.trade_pairs import generate_bilateral_trade_proposals
    from fsffl.opportunity.trade_universe import TradePackageSeed,canonical_package_id
    from fsffl.value.cardinal_authority import FSFFLCardinalValueScore
    from tests.test_strategic_discovery import governed_runtime_fixture
    from tests.test_dynasty_position_room import _career_current_components
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    runtime,_=governed_runtime_fixture(team_count=2,superflex=superflex)
    state=runtime.league_state
    def points(pid):
        if pid=='t0-0':return 10.
        if pid=='t0-1':return 8.
        if pid=='t1-0':return 120.
        if pid=='t1-1':return 100.
        if pid in {f't0-{n}' for n in range(6,11)}:return 150.
        if pid=='t0-11':return 100.
        if pid in {f't1-{n}' for n in range(6,12)}:return 1.
        return 50.
    evidence=replace(runtime.forecast_evidence,league_scored_forecasts=tuple(f.model_copy(update={
        'distribution':f.distribution.model_copy(update={'mean':points(f.player_id)})}) for f in runtime.forecast_evidence.league_scored_forecasts))
    scores=tuple(FSFFLCardinalValueScore(asset_id=p.player_id,asset_kind='player',score=100,as_of=state.as_of,market_context_id='synthetic') for p in state.players)
    scores+=tuple(FSFFLCardinalValueScore(asset_id=p.pick_id,asset_kind='pick',score=20,as_of=state.as_of,market_context_id='synthetic',slot_certainty='generic_unknown_slot') for p in state.draft_picks)
    runtime=replace(runtime,forecast_evidence=evidence,value_evidence=NS(fsffl_cardinal_values=scores),publication_generation_id='synthetic')
    components={p.player_id:((100.,100.,100.) if p.player_id=='t0-11' else (1.,1.,1.)) for p in state.players}
    contract=_career_current_components(state,components,positions={p.player_id:p.position for p in state.players})
    contract=contract.model_copy(update={'estimates':tuple(r.model_copy(update={'long_horizon_raw_y4_y7_reference':800.,'terminal_raw_y8_plus_reference':200.}) for r in contract.estimates)})
    record=NS(user_id=runtime.user_id,league_state_id=state.state_id,status=IntrinsicBuildStatus.COMPLETED,contract=contract,intrinsic_input_fingerprint='fixture')
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(components),record=record,publication_validator=lambda c,r:True)
    read=replace(read,pick_values={'three_year':{'pick-t1':500.},'career':{'pick-t1':800.}},pick_sources={'pick-t1':{'release_id':'controlled','model_version':'controlled-fixture'}})
    def context(current,team_id,instructions=None):
        return OwnerObjectiveContext(team_id=team_id,source='controlled-fixture',objectives=(
            ('current_competitiveness','three_year_contribution','career_contribution') if team_id=='t0' else ('current_competitiveness',)))
    monkeypatch.setattr(module,'objective_context',context);monkeypatch.setattr(trade_objectives,'objective_context',context)
    def pkg(team,pid):
        assets=(PlayerAsset(player_id=pid),)
        return TradePackageSeed(team_id=team,assets=assets,canonical_id=canonical_package_id(team,assets))
    proposal=generate_bilateral_trade_proposals((pkg('t0','t0-11'),),(pkg('t1','t1-1'),),as_of=state.as_of).proposals[0]
    monkeypatch.setattr(module,'generate_guided_strategic_packages',lambda *args,**kw:(
        (StrategicSeed(proposal,('controlled',)),),{'pair_visits':1,'shapes':{},'hypotheses':{}}))
    before=state.model_dump(mode='json')
    result=module.build_strategic_discovery(runtime,StrategicDiscoveryRequest(evaluation_budget=3,max_candidates=3,offered_asset_ref='player:t0-11' if required_offer else None),read=read)
    rows=result['candidate_packages'];d=result['diagnostics']
    assert d['preliminary_decision_errors']==0
    assert len(rows)==2 and d['root_screen_attempts']==d['repair_screen_attempts']==1
    assert rows[0]['display_context']['group']=='priority_tradeoff'
    assert rows[0]['shortlist_quality']['status']=='needs_terms'
    assert rows[1]['display_context']['group']=='preliminary_fit'
    assert rows[1]['shortlist_quality']['status']=='shortlist'
    assert 'pick:pick-t1' in {a['asset_ref'] for a in rows[1]['receive']}
    assert all('player:t0-11' in {a['asset_ref'] for a in r['send']} for r in rows)
    assert rows[1]['preliminary_decision_screen']['focal']['starter_points_delta']>0
    assert rows[1]['preliminary_decision_screen']['counterparty']['starter_points_delta']>0
    assert all(rows[1]['horizon_asset_economics'][h]['roster_adjusted']['side_a']['roster_adjusted_intrinsic_delta']>0 for h in ('three_year','career'))
    assert d['preliminary_decision_attempts']<=3 and d['pair_visits']<=d['max_pair_visits']
    assert d['changed_state_simulation_calls']==0 and state.model_dump(mode='json')==before


def test_second_step_consumes_actual_cut_adjusted_feedback_instead_of_the_pre_cut_hint():
    runtime,root,read,inventories=fixture()
    # A first asset appears sufficient before cuts, but the completed screen
    # still reports a native deficit. A second counted child must remain possible.
    read.pick_values={'three_year':{'p':500,'q':100},'career':{'p':600,'q':100}}
    def feedback(point_id):
        r=deepcopy(root)
        r['horizon_asset_economics']={h:{'roster_adjusted':{'side_a':{'status':'complete','roster_adjusted_intrinsic_delta':-50}}} for h in ('three_year','career')}
        return r
    path=list(compensation_path(runtime,root,read,inventories=inventories,visits=FeedbackVisits(8),feedback=feedback))
    assert len(path)==2


def test_compensation_cannot_use_a_native_deficit_to_demand_an_overpriced_pick():
    runtime,root,read,inventories=fixture()
    read.pick_values={'three_year':{'p':500,'q':100},'career':{'p':600,'q':100}}
    # The large pick would close the deficit but is outside the existing Market
    # envelope. The smaller feasible ingredient stays available; no new pricing
    # coefficient or closest-price opportunity score is introduced.
    path=list(compensation_path(runtime,root,read,inventories=inventories,visits=FeedbackVisits(8),
        market_values={'a':100,'b':100,'p':1000,'q':50},economic_tolerance=100))
    assert len(path)==1
    assert PickAsset(pick_id='q') in path[0][0].counterparty_package.assets
    assert PickAsset(pick_id='p') not in path[0][0].counterparty_package.assets
