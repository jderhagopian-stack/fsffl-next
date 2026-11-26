"""Reported complete-path failures, independent of particular league/player IDs."""
from copy import deepcopy
from fsffl.product.progressive_discovery import ProgressiveDiscovery
from fsffl.product.strategic_discovery import StrategicDiscoveryRequest
from fsffl.opportunity.shortlist_quality import curate_shortlist
from fsffl.product.strategic_discovery_presentation import discovery_display_context
from tests.test_shortlist_quality import evaluated,inferred_tradeoff
from tests.test_progressive_discovery import read_fixture


def proof(row, wins, playoffs, title):
    from fsffl.trade_decision import live_bounded_materiality_policy
    from fsffl.trade_decision.materiality import classify_positive_delta
    from datetime import datetime,timezone
    policy=live_bounded_materiality_policy(as_of=datetime(2026,11,26,tzinfo=timezone.utc)).competitive
    team=row.get('focal_team_id','side_a')
    competitive={'expected_wins':wins,'playoff_probability':playoffs,'first_place_probability':0.,'championship_probability':title}
    material={k:classify_positive_delta(v,absolute_threshold=getattr(policy,k+'_abs')).value for k,v in competitive.items()}
    return {'status':'verified','source_state_id':'state','publication_generation_id':'generation',
        'baseline_simulation_input_fingerprint':'simulation','native_input_fingerprint':'native',
        'competitive_policy_version':'policy','simulation_count':50_000,'resilience':{team:0.},
        'competitive':{team:competitive},'material':{'side_a':{'team_id':team,**material,'largest_single_player_lineup_drop':'immaterial'}}}


def test_exhausted_screening_still_confirms_the_second_promising_package(monkeypatch):
    import fsffl.product.progressive_discovery as module
    a,b=evaluated('first'),evaluated('second',current=(1,1),three=(30,-30),career=(50,-50))
    for r in (a,b):
        r['evaluation_kind']='root'
        for side in ('side_a','side_b'):r['objective_assessment'][side]['context']['team_id']=side
    screens=[];checks=[]
    def build(*args,**kwargs):
        screens.append(True)
        return {'candidate_packages':[deepcopy(a),deepcopy(b)],'publication_generation_id':'generation',
            'diagnostics':{'unexamined_pool_count':0,'repair_sequence_attempted':False}}
    monkeypatch.setattr(module,'build_strategic_discovery',build)
    def confirm(runtime,row,read,instructions):
        checks.append(row['point_id'])
        return {'status':'not_worthwhile' if row['point_id']=='first' else 'verified'}
    runtime,_,_,_=read_fixture();service=ProgressiveDiscovery(finalist_evaluator=confirm)
    first=service.build(runtime,StrategicDiscoveryRequest())
    p=first['search_progress']
    assert checks==['first'] and p['shortlisted_choice_count']==0
    assert p['next_token'], 'The screened second offer still needs its permitted full check'
    second=service.build(runtime,StrategicDiscoveryRequest(continuation_token=p['next_token']))
    assert len(screens)==1 and checks==['first','second']
    assert second['search_progress']['screens_this_batch']==0
    assert second['publication_generation_id']=='generation'
    assert second['search_progress']['shortlisted_choice_count']==1
    assert second['search_progress']['next_token'] is None


def test_full_competitive_evidence_supersedes_larger_weekly_proxy():
    better=evaluated('stronger-season',current=(2,1));better['focal_team_id']='side_a'
    proxy=evaluated('larger-weekly',current=(5,1));proxy['focal_team_id']='side_a'
    better['screen_confirmation']=proof(better,.4,.08,.06)
    proxy['screen_confirmation']=proof(proxy,.2,.04,.02)
    curate_shortlist([better,proxy],require_current_confirmation=True)
    assert better['shortlist_quality']['status']=='shortlist'
    assert proxy['shortlist_quality']['status']=='alternative'


def test_zero_current_lineup_depth_hypothesis_can_reach_full_check():
    from tests.test_trade_transaction_strategy import assess,roles
    from tests.test_trade_objectives import metric
    from fsffl.trade_decision.objectives import TradeObjective as G
    r=evaluated('depth',current=(0,3),three=(20,-20),career=(50,-50))
    r['objective_assessment']['side_a']['context'].update(source='calculated_state_posture_hypothesis_v1',explicitly_directed=False)
    r['objective_assessment']['side_a']['transaction_strategy']=assess((G.CURRENT,),[
        metric(G.CURRENT,0),metric(G.THREE_YEAR,20),metric(G.CAREER,50),
        metric(G.RESILIENCE,0,higher_is_better=False)],roles())
    r['display_context']=discovery_display_context(r)
    curate_shortlist([r])
    assert r['shortlist_quality']['status'] in ('shortlist','strategic_tradeoff'), 'Eligible for bounded confirmation, not certified surplus'


def test_balanced_same_target_different_timeline_terms_are_preserved_regardless_of_tuple_order():
    results=[]
    for goals in [('current_competitiveness','three_year_contribution','career_contribution'),
                  ('career_contribution','current_competitiveness','three_year_contribution')]:
        current=inferred_tradeoff('current',current=(5,-2),three=(-100,100),career=(-300,300))
        future=inferred_tradeoff('future',current=(2,-1),three=(-20,20),career=(-40,40))
        for r in (current,future):
            r['receive']=[{'asset_ref':'player:target'}]
            r['objective_assessment']['side_a']['context']['objectives']=goals
            r['display_context']=discovery_display_context(r)
        curate_shortlist([current,future])
        results.append({r['point_id']:r['shortlist_quality']['status'] for r in (current,future)})
    assert results[0]==results[1]
    assert all(s=='strategic_tradeoff' for s in results[0].values())


def test_confirmed_incomparable_incomplete_and_different_input_results_are_preserved():
    a=evaluated('a',current=(1,1));a['focal_team_id']='side_a'
    b=evaluated('b',current=(10,1));b['focal_team_id']='side_a'
    a['screen_confirmation']=proof(a,.4,.01,.06)
    b['screen_confirmation']=proof(b,.2,.08,.02)
    for change in ('incomparable','missing','different-input','preliminary'):
        left,right=deepcopy(a),deepcopy(b)
        if change=='missing':del right['screen_confirmation']['competitive']['side_a']['playoff_probability']
        if change=='different-input':right['screen_confirmation']['baseline_simulation_input_fingerprint']='other'
        if change=='preliminary':right.pop('screen_confirmation')
        curate_shortlist([left,right])
        assert all(r['shortlist_quality']['status']=='shortlist' for r in (left,right))


def test_deferred_check_does_not_loop_or_claim_completed_empty_search(monkeypatch):
    import fsffl.product.progressive_discovery as module
    r=evaluated('blocked');r['evaluation_kind']='root'
    for side in ('side_a','side_b'):r['objective_assessment'][side]['context']['team_id']=side
    calls=[]
    monkeypatch.setattr(module,'build_strategic_discovery',lambda *a,**k:{'candidate_packages':[deepcopy(r)],
        'diagnostics':{'unexamined_pool_count':0,'repair_sequence_attempted':False}})
    service=ProgressiveDiscovery(finalist_evaluator=lambda *a:calls.append(True) or {'status':'deferred','reason':'resource_headroom'})
    runtime,_,_,_=read_fixture();result=service.build(runtime,StrategicDiscoveryRequest())
    p=result['search_progress']
    assert p['confirmation_incomplete'] and p['pending_confirmation_count']==1
    assert p['stop_reason']=='confirmation_incomplete' and p['next_token'] is None
    assert p['confirmation_attempts']==1 and p['finalist_confirmations']==0
    cached=service.build(runtime,StrategicDiscoveryRequest())
    assert cached['search_progress']['cache_hit'] and len(calls)==1


def test_confirmation_limit_and_eighty_screen_limit_are_independent(monkeypatch):
    import fsffl.product.progressive_discovery as module
    rows=[]
    for i in range(10):
        r=evaluated(str(i),current=(10-i,1),three=(i,-i),career=(i,-i));r['evaluation_kind']='root'
        for side in ('side_a','side_b'):r['objective_assessment'][side]['context']['team_id']=side
        rows.append(r)
    monkeypatch.setattr(module,'build_strategic_discovery',lambda *a,**k:{'candidate_packages':deepcopy(rows),
        'diagnostics':{'unexamined_pool_count':0,'repair_sequence_attempted':False}})
    checks=[];runtime,_,_,_=read_fixture()
    service=ProgressiveDiscovery(finalist_evaluator=lambda runtime,row,*a:checks.append(row['point_id']) or {'status':'verified'})
    token=None
    for _ in range(8):
        result=service.build(runtime,StrategicDiscoveryRequest(continuation_token=token));token=result['search_progress']['next_token']
    p=result['search_progress']
    assert len(checks)==len(set(checks))==8 and p['total_screened']==10
    assert not token and p['confirmation_incomplete'] and p['pending_confirmation_count']==2


def test_depth_conversion_real_preliminary_to_full_gate_and_negative_roster_cases(monkeypatch):
    # Controlled upstream competitive/native packets isolate routing. Ownership,
    # weekly roster optimization, role production and both Decision producers run.
    from dataclasses import replace
    from types import SimpleNamespace as NS
    from fsffl.state.models import DraftPick,PickOwnership
    from fsffl.value.cardinal_authority import FSFFLCardinalValueScore
    from fsffl.product.market_discovery_runtime import evaluate_candidate_path
    from fsffl.product.trade_objectives import build_trade_objective_assessment
    from fsffl.product.discovery_confirmation import evaluate_finalist,COMPETITIVE_METRICS
    from fsffl.team_utility.utility import CalculatedCompetitiveState
    from tests.test_strategic_feedback import controlled_root
    import fsffl.product.discovery_confirmation as full
    import fsffl.product.trade_objectives as objectives
    import fsffl.product.progressive_discovery as progressive
    runtime,_,_=controlled_root()
    state=runtime.league_state
    state=state.model_copy(update={'draft_picks':(DraftPick(pick_id='future',league_id=state.league.league_id,
        season=2027,round=1,original_team_id='b'),),'pick_ownership':(PickOwnership(pick_id='future',owner_team_id='b'),)})
    scores=tuple(FSFFLCardinalValueScore(asset_id=p.player_id,asset_kind='player',score=100.,as_of=state.as_of,market_context_id='test') for p in state.players)
    scores+= (FSFFLCardinalValueScore(asset_id='future',asset_kind='pick',score=100.,as_of=state.as_of,market_context_id='test',slot_certainty='generic_unknown_slot'),)
    forwards=tuple(f.model_copy(update={'distribution':f.distribution.model_copy(update={'mean':10.})}) if f.player_id=='opp' else f for f in runtime.forecast_evidence.simulation_forward_forecasts)
    runtime=replace(runtime,league_state=state,forecast_evidence=replace(runtime.forecast_evidence,simulation_source_state_id=state.state_id,simulation_forward_forecasts=forwards),
        simulation_analytics=None,value_evidence=NS(fsffl_cardinal_values=scores))
    monkeypatch.setattr(objectives,'calculated_competitive_state',lambda context:CalculatedCompetitiveState.CONTENDER)
    native={h:{'roster_adjusted':{s:{'status':'complete','roster_adjusted_intrinsic_delta':value}
        for s,value in [('side_a',30),('side_b',-30)]}} for h in ('three_year','career')}
    row={'point_id':'bench-future','focal_team_id':'a','counterparty_team_id':'b','send':[{'asset_ref':'player:reserve'}],
        'receive':[{'asset_ref':'pick:future'}],'preliminary_economic_band':'robust_or_ordinary','evaluation_kind':'root'}
    result=evaluate_candidate_path(runtime,row)
    result['horizon_asset_economics']=native
    row.update(evidence_status='pre_simulation_screened',preliminary_decision_screen=result['preliminary_bilateral_screen'],
        roster_legality=result['roster_legality'],horizon_asset_economics=native,roster_adjusted_market_net=result['roster_adjusted_market_net'],
        objective_assessment=build_trade_objective_assessment(runtime,full._proposal_from_row(runtime,row,prefix='test'),result))
    strategy=row['objective_assessment']['side_a']['transaction_strategy']
    assert strategy['depth_conversion_investigation_eligible'] and not strategy['depth_conversion_candidate']
    assert row['preliminary_decision_screen']['focal']['starter_points_delta']==0
    assert row['preliminary_decision_screen']['counterparty']['starter_points_delta']>0
    row['display_context']=discovery_display_context(row)
    assert row['display_context']['group']=='depth_conversion_hypothesis'
    material={'competitive_policy_version':'existing-policy',**{s:{'team_id':team,**{k:'immaterial' for k in COMPETITIVE_METRICS}}
        for s,team in [('side_a','a'),('side_b','b')]}}
    material['side_b']['championship_probability']='material_gain'
    packet={**result,'scenario_computation':{'authoritative':True,'cache_hit':False,'execution_mode':'full_recompute'},
        'scenario_simulation_count':50_000,'material_assessment':material,
        'team_deltas':[{'team_id':team,'competitive':{k:0. if team=='a' else .1 for k in COMPETITIVE_METRICS},
            'resilience':{'largest_single_player_lineup_drop':0.}} for team in ('a','b')]}
    runtime=replace(runtime,publication_generation_id='generation',simulation_analytics=NS(simulation_result=NS(simulation_count=50_000,simulation_input_fingerprint='simulation')))
    read=NS(source={'input_fingerprint':'native','publication_generation_id':runtime.publication_generation_id},
        user_id=runtime.user_id,selected_team_id=runtime.selected_team_id,state_ref=lambda:state,as_of=state.as_of)
    monkeypatch.setattr(full,'build_post_trade_simulation_comparison',lambda *a,**k:packet)
    monkeypatch.setattr(full,'bind_trade_intrinsic_values',lambda *a,**k:native)
    from fsffl.product import resource_coordinator
    monkeypatch.setattr(resource_coordinator,'current_rss_bytes',lambda:100)
    monkeypatch.setattr(progressive,'build_strategic_discovery',lambda *a,**k:{'candidate_packages':[deepcopy(row)],
        'diagnostics':{'unexamined_pool_count':0,'repair_sequence_attempted':False}})
    def check(*args):return evaluate_finalist(*args,simulation_loader=lambda *a:None,memory_budget_bytes=429496729,reclaim=lambda label:None)
    service=ProgressiveDiscovery(finalist_evaluator=check)
    positive=service.build(runtime,StrategicDiscoveryRequest(),read=read)
    assert positive['search_progress']['shortlisted_choice_count']==1
    proof=positive['confirmation_updates']['bench-future']
    assert proof['status']=='verified' and proof['roster_supported_future_team_ids']==['a']
    # Each full result can veto the SAME previously admitted hypothesis.
    clean=deepcopy(packet)
    for damage in ('resilience','coverage','starter_role','competitive_loss','future_loss'):
        packet=deepcopy(clean)
        if damage=='resilience':packet['team_deltas'][0]['resilience']['largest_single_player_lineup_drop']=10.
        elif damage=='coverage':packet['positional_context'][0]['after_unfilled_slots']=1
        elif damage=='starter_role':
            packet['positional_context'][0]['positions'][0]['outgoing_starter_ids']=['reserve']
        elif damage=='competitive_loss':packet['material_assessment']['side_a']['championship_probability']='material_loss'
        else:native['three_year']['roster_adjusted']['side_a']['roster_adjusted_intrinsic_delta']=-10
        failed=ProgressiveDiscovery(finalist_evaluator=check).build(runtime,StrategicDiscoveryRequest(),read=read)
        assert failed['search_progress']['shortlisted_choice_count']==0, damage
        assert failed['confirmation_updates']['bench-future']['status']!='verified', damage
        native['three_year']['roster_adjusted']['side_a']['roster_adjusted_intrinsic_delta']=30
    # Explicit Current-only instructions cannot admit the inferred exception.
    explicit=deepcopy(row);explicit['objective_assessment']['side_a']['context']['explicitly_directed']=True
    explicit['display_context']=discovery_display_context(explicit)
    curate_shortlist([explicit])
    assert explicit['shortlist_quality']['status']=='review'


def test_existing_decision_indifference_prefers_less_future_sacrifice():
    from fsffl.trade_decision import live_bounded_materiality_policy
    from datetime import datetime,timezone
    policy=live_bounded_materiality_policy(as_of=datetime(2026,11,26,tzinfo=timezone.utc))
    dear=evaluated('dear',current=(6,1),three=(-45,45),career=(-270,270),market=-31)
    cheaper=evaluated('cheaper',current=(5,1),three=(-15,15),career=(-167,167),market=-159)
    for r,wins,title in [(dear,.11846,.05804),(cheaper,.10916,.05518)]:
        r['focal_team_id']='side_a';r['screen_confirmation']=proof(r,wins,.00002,title)
        r['screen_confirmation']['competitive_policy_version']=policy.competitive.model_version
    curate_shortlist([dear,cheaper],market_tolerance=policy.economic.mean_value_abs,competitive_policy=policy.competitive)
    assert dear['shortlist_quality']['status']=='alternative'
    assert cheaper['shortlist_quality']['status']=='shortlist'
    # A genuinely different competitive benefit is not priced in Career units.
    dear['screen_confirmation']['competitive']['side_a']['championship_probability']=.09
    curate_shortlist([dear,cheaper],market_tolerance=policy.economic.mean_value_abs,competitive_policy=policy.competitive)
    assert all(r['shortlist_quality']['status']=='shortlist' for r in (dear,cheaper))


def test_inferred_balanced_permutation_preserves_generation_and_published_inputs(monkeypatch):
    from dataclasses import replace
    from fsffl.product import strategic_discovery as module
    from fsffl.trade_decision.objectives import TradeObjective as G
    from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
    from tests.test_strategic_discovery import governed_runtime_fixture
    runtime,record=governed_runtime_fixture(team_count=3)
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(p.player_id for p in runtime.league_state.players),
        record=record,publication_validator=lambda c,r:True)
    original=module.objective_context;before={h:dict(v) for h,v in read.values.items()};state=runtime.league_state
    forecast=runtime.forecast_evidence;baseline=runtime.simulation_analytics
    samples=[]
    for order in [(G.CURRENT,G.THREE_YEAR,G.CAREER),(G.CAREER,G.CURRENT,G.THREE_YEAR)]:
        monkeypatch.setattr(module,'objective_context',lambda r,t,instructions=None:original(r,t,instructions).model_copy(update={'objectives':order}))
        result=module.build_strategic_discovery(runtime,StrategicDiscoveryRequest(max_candidates=16),read=read)
        samples.append([(r['point_id'],r.get('evaluation_kind'),r['display_context']['group']) for r in result['candidate_packages']])
        assert result['diagnostics']['generation_pair_visits']<=640
    assert samples[0]==samples[1]
    assert read.values==before and runtime.league_state is state
    assert runtime.forecast_evidence is forecast and runtime.simulation_analytics is baseline


def test_confirmation_only_continues_even_after_eighty_screens(monkeypatch):
    import fsffl.product.progressive_discovery as module
    a,b=evaluated('first'),evaluated('second',current=(1,1),three=(30,-30),career=(50,-50))
    for r in (a,b):
        r['evaluation_kind']='root'
        for side in ('side_a','side_b'):r['objective_assessment'][side]['context']['team_id']=side
    calls=[]
    monkeypatch.setattr(module,'build_strategic_discovery',lambda *a,**k:calls.append(1) or {'candidate_packages':deepcopy([a_row,b_row]),
        'diagnostics':{'unexamined_pool_count':0,'repair_sequence_attempted':False}})
    a_row,b_row=a,b
    runtime,_,_,_=read_fixture()
    service=ProgressiveDiscovery(finalist_evaluator=lambda runtime,row,*args:{'status':'not_worthwhile' if row['point_id']=='first' else 'verified'})
    request=StrategicDiscoveryRequest();first=service.build(runtime,request)
    scope=service._scope(runtime,request,None);payload=service._decode(first['search_progress']['next_token'],scope)
    payload['screened']+=['screened-'+str(i) for i in range(78)]
    second=service.build(runtime,request.model_copy(update={'continuation_token':service._encode(payload)}))
    assert second['search_progress']['total_screened']==80
    assert second['search_progress']['screens_this_batch']==0 and len(calls)==1
    assert second['search_progress']['shortlisted_choice_count']==1


def test_pairwise_indifference_cannot_erase_a_decision_material_loss_boundary():
    from datetime import datetime,timezone
    from fsffl.trade_decision import live_bounded_materiality_policy
    policy=live_bounded_materiality_policy(as_of=datetime(2026,11,26,tzinfo=timezone.utc))
    less_cost=evaluated('less-current-cost',current=(-3,1),three=(30,-30),career=(50,-50))
    more_future=evaluated('more-future',current=(-6,1),three=(60,-60),career=(100,-100))
    for r,wins in [(less_cost,-.196),(more_future,-.288)]:
        r['objective_assessment']['side_a']['context'].update(objectives=['career_contribution'],explicitly_directed=True,team_id='side_a')
        r['focal_team_id']='side_a';r['display_context']=discovery_display_context(r)
        r['screen_confirmation']=proof(r,wins,0.,0.)
        r['screen_confirmation']['competitive_policy_version']=policy.competitive.model_version
    curate_shortlist([less_cost,more_future],market_tolerance=policy.economic.mean_value_abs,competitive_policy=policy.competitive)
    assert all(r['shortlist_quality']['status']=='shortlist' for r in (less_cost,more_future))
