"""Published native evidence completes final Decision, not just its presentation."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from fsffl.trade_decision.disposition import TradeDecisionDisposition,TradeDispositionEvidence
from fsffl.trade_decision.material_assessment import BilateralMaterialAssessment
from fsffl.trade_decision.materiality import MaterialityDirection as M
from fsffl.product.trade_native_completion import finalize_published_trade_decision
from fsffl.product.trade_objectives import build_trade_objective_assessment,TradeSearchInstructions
from fsffl.trade_decision.objectives import TradeObjective as G
from fsffl.product.trade_intrinsic_evidence import build_trade_intrinsic_evidence
from tests.test_trade_intrinsic_evidence import fixture
from tests.test_trade_intrinsic_roster_economics import resolutions
from tests.test_trade_decision_disposition import _material_side


def seed(runtime,record,proposal,*,current_gain=True):
    a=_material_side('alpha').model_copy(update={'intrinsic_value':M.UNAVAILABLE,
        'playoff_probability':M.MATERIAL_GAIN if current_gain else M.IMMATERIAL})
    b=_material_side('beta').model_copy(update={'intrinsic_value':M.UNAVAILABLE})
    material=BilateralMaterialAssessment(proposal_id=proposal.proposal_id,side_a=a,side_b=b,
        competitive_policy_version='existing-policy',economic_policy_version='market-only')
    base=TradeDecisionDisposition(proposal_id=proposal.proposal_id,disposition='insufficient_evidence',
        evidence=TradeDispositionEvidence(focal_team_id='alpha',counterparty_team_id='beta',
            unavailable_metrics=('intrinsic_value',),negotiation_shape='mixed',owner_posture='default_calculated'),
        material_assessment_model_version='m',negotiation_model_version='n',strategic_context_model_version='s')
    cuts=resolutions()
    native=build_trade_intrinsic_evidence(runtime,proposal,record=record,publication_validator=lambda c,r:True,roster_resolutions=cuts)
    result={'focal_team_id':'alpha','counterparty_team_id':'beta','state_id_before':runtime.league_state.state_id,
        'state_id_after':'changed','scenario_computation':{'authoritative':True},'scenario_simulation_count':50000,
        'disposition':base.model_dump(mode='json'),'material_assessment':material.model_dump(mode='json'),
        'horizon_asset_economics':native,'roster_legality':[x.model_dump(mode='json') for x in cuts],
        'team_deltas':[{'team_id':team,'competitive':{'expected_wins':0,'playoff_probability':.03 if team=='alpha' and current_gain else 0,
            'first_place_probability':0},'resilience':{'largest_single_player_lineup_drop':0}} for team in ('alpha','beta')],
        'decision_dimensions':{'confidence':{'missing_dimensions':['long_term_franchise_value']}},
        'decision_completeness':{'final_disposition_available':False,'missing_authorities':['long_term_franchise_value']},
        'availability':{'competitive_outcomes':True,'final_trade_disposition':False}}
    result['positional_context']=[{'team_id':team,'status':'complete','source_state_id':runtime.league_state.state_id,
        'after_state_id':'changed','before_unfilled_slots':0,'after_unfilled_slots':0,'positions':[]} for team in ('alpha','beta')]
    return result


def finish(runtime,proposal,result,goals=(G.CURRENT,G.THREE_YEAR,G.CAREER)):
    result=deepcopy(result)
    try:
        result['objective_assessment']=build_trade_objective_assessment(runtime,proposal,result,TradeSearchInstructions(objectives=goals))
    except ValueError:
        result['objective_assessment']={'status':'unavailable'}
    return finalize_published_trade_decision(runtime,proposal,result)


def set_delta(result,horizon,delta):
    row=result['horizon_asset_economics'][horizon]
    for side,d in [('side_a',delta),('side_b',-delta)]:
        row[side].update(mean_delta=d,received_mean=row[side]['sent_mean']+d)
        row['roster_adjusted'][side].update(raw_trade_intrinsic_delta=d,roster_adjusted_intrinsic_delta=d)


def test_complete_native_evidence_reaches_final_decision_and_ready_contract():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal);before=deepcopy(result)
    done=finish(runtime,proposal,result)
    assert done['native_completion']['status']=='complete'
    assert done['disposition']['disposition']=='support'
    assert done['availability']['final_trade_disposition']
    assert done['decision_completeness']['missing_authorities']==()
    dims=done['decision_dimensions']['long_term_franchise_value']
    assert dims['available'] and dims['net_delta'] is None and dims['combined_value'] is None
    assert dims['horizons']['three_year']['scale']!=dims['horizons']['career']['scale']
    assert result==before


def test_flowers_shaped_current_gain_and_career_loss_is_complete_review():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    set_delta(result,'three_year',1.5157);set_delta(result,'career',-80.6994)
    done=finish(runtime,proposal,result)
    assert done['disposition']['disposition']=='review'
    assert done['availability']['final_trade_disposition']
    assert done['disposition']['evidence']['native_losses']==['career']
    assert not done['disposition']['evidence']['unavailable_metrics']
    assert 'intrinsic_value' not in done['disposition']['evidence']['material_losses']


def test_future_only_benefit_is_complete_without_current_gain_or_fake_materiality():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal,current_gain=False)
    done=finish(runtime,proposal,result,goals=(G.THREE_YEAR,G.CAREER))
    assert done['disposition']['disposition']=='review'
    assert done['availability']['final_trade_disposition']
    assert 'future_priority_benefit' in done['disposition']['evidence']['review_reasons']
    assert done['disposition']['evidence']['native_materiality_status']=='directional_only_not_calibrated'
    assert not done['disposition']['evidence']['material_gains']


@pytest.mark.parametrize('change',["generation","state","side","cut","scale","infinite_other","missing_asset"])
def test_genuine_missing_or_mismatched_native_input_stays_incomplete(change):
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    native=result['horizon_asset_economics'];row=native['career']
    if change=='generation':native['source']['publication_generation_id']='old'
    elif change=='state':native['source']['league_state_id']='old'
    elif change=='side':native['side_b_team_id']='foreign'
    elif change=='cut':row['roster_adjusted']['side_a']['cut_player_ids']=['unpriced-cut']
    elif change=='scale':row['roster_adjusted']['side_a']['scale']={**row['side_a']['scale'],'version':'other'}
    elif change=='infinite_other':row['roster_adjusted']['side_b']['roster_adjusted_intrinsic_delta']=float('inf')
    elif change=='missing_asset':row['status']='incomplete'
    done=finish(runtime,proposal,result)
    assert done['disposition']['disposition']=='insufficient_evidence'
    assert not done['availability']['final_trade_disposition']
    assert done['native_completion']['status']=='unavailable'


def test_preview_cannot_be_promoted_even_with_complete_native_data():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    result['scenario_computation']['authoritative']=False
    done=finish(runtime,proposal,result)
    assert not done['availability']['final_trade_disposition']
    assert 'native_completion' not in done


def test_actual_web_route_reads_native_once_then_finalizes(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    import fsffl.product.webapp as webapp
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    runtime,record,_=fixture();store=PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id,runtime.league_state);store.select_team(runtime.user_id,'alpha')
    store.bind_publication_generation_id(runtime.user_id,'g1');calls=[]
    def simulate(context,proposal,**kwargs):
        calls.append('simulation');result=seed(context,record,proposal)
        del result['horizon_asset_economics'];return result
    def provider(context,proposal,result):
        calls.append('native');return build_trade_intrinsic_evidence(context,proposal,record=record,
            publication_validator=lambda c,r:True,roster_resolutions=resolutions())
    monkeypatch.setattr(webapp,'build_post_trade_simulation_comparison',simulate)
    client=TestClient(create_app(runtime_store=store,trade_horizon_evidence_provider=provider))
    response=client.post('/api/trade-center/simulate',json={'counterparty_team_id':'beta',
        'focal_asset_refs':['player:a1'],'counterparty_asset_refs':['player:b1']})
    assert response.status_code==200,response.text
    result=response.json()
    assert result['native_completion']['status']=='complete'
    assert result['availability']['final_trade_disposition']
    assert calls==['simulation','native']


def _exercise_actual_flow(superflex):
    """Controlled tiny league; real scoring, confirmation, cuts, route and finalization."""
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app,_build_default_simulation
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
    from fsffl.state.models import Position,RosterSlot,LineupRequirement
    from tests.test_simulation_ros_inputs import fixture as ros_fixture,market
    from tests.test_dynasty_position_room import _career_current_components
    state,forecast=ros_fixture()
    from dataclasses import replace
    from fsffl.team_utility.simulation import _settings_derived_playoff_rules
    rules=state.league.rules.model_copy(update={'playoff_team_count':2,'playoff_start_week':15,
        'regular_season_end_week':14,'playoff_rules':_settings_derived_playoff_rules(2,15)})
    state=state.model_copy(update={'league':state.league.model_copy(update={'rules':rules})})
    forecast=replace(forecast,simulation_source_state_id=state.state_id)
    if superflex:
        from dataclasses import replace
        state=state.model_copy(update={'league':state.league.model_copy(update={'rules':state.league.rules.model_copy(update={
            'lineup':(*state.league.rules.lineup,LineupRequirement(slot=RosterSlot.SUPERFLEX,count=1))})})})
        forecast=replace(forecast,simulation_source_state_id=state.state_id)
    baseline=_build_default_simulation(state,forecast,simulation_count=50000)
    contract=_career_current_components(state,{'starter':(10.,20.,30.),'bench':(20.,30.,40.),'opp':(30.,40.,50.)},
        positions={p.player_id:Position.QB for p in state.players})
    contract=contract.model_copy(update={'estimates':tuple(r.model_copy(update={'long_horizon_raw_y4_y7_reference':800.,'terminal_raw_y8_plus_reference':200.}) for r in contract.estimates)})
    record=SimpleNamespace(user_id='local-beta-user',league_state_id=state.state_id,status=IntrinsicBuildStatus.COMPLETED,
        contract=contract,intrinsic_input_fingerprint='fixture-dependency')
    store=PrivateBetaRuntimeStore();store.set_league_state('local-beta-user',state);store.select_team('local-beta-user','a')
    store.set_forecast_evidence('local-beta-user',forecast)
    store.set_simulation_analytics('local-beta-user',baseline);store.set_value_evidence('local-beta-user',market(state));store.bind_publication_generation_id('local-beta-user','g1')
    calls=[]
    def loader(s,e):
        calls.append('simulation');return _build_default_simulation(s,e,simulation_count=50000)
    def provider(runtime,proposal,result):
        calls.append('native')
        cuts=tuple(TeamRosterLegalityResolution.model_validate(x) for x in result['roster_legality'])
        return build_trade_intrinsic_evidence(runtime,proposal,record=record,
            publication_validator=lambda c,r:True,roster_resolutions=cuts)
    client=TestClient(create_app(runtime_store=store,simulation_loader=loader,trade_horizon_evidence_provider=provider))
    body={'counterparty_team_id':'b','focal_asset_refs':['player:starter'],'counterparty_asset_refs':['player:opp']}
    analysis=client.post('/api/trade-center/analyze',json=body)
    assert analysis.status_code==200,analysis.text
    assert not analysis.json()['availability']['final_trade_disposition']
    simulation=client.post('/api/trade-center/simulate',json=body)
    assert simulation.status_code==200,simulation.text
    result=simulation.json()
    assert result['native_completion']['status']=='complete',(result['native_completion'],result['objective_assessment'],result['horizon_asset_economics'])
    assert result['availability']['final_trade_disposition'],result['decision_completeness']
    assert result['disposition']['disposition']!='insufficient_evidence'
    assert result['scenario_simulation_count']==50000
    assert calls.count('simulation')==1 and calls.count('native')==2
    assert store.get('local-beta-user').league_state.state_id==state.state_id


@pytest.mark.parametrize('superflex',[False,True])
def test_actual_analyze_confirmed_simulation_native_source_and_final_decision(superflex):
    import subprocess,sys
    # Keep real admission safeguards independent of unrelated suite allocations.
    result=subprocess.run([sys.executable,'-c',
        'import os;os.environ["FSFFL_BETA_AUTH"]="0";'
        'from tests.test_native_trade_completion import _exercise_actual_flow;'
        f'_exercise_actual_flow({superflex!r})'],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr


def test_position_costs_and_confirmed_count_are_not_ignored():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    result['positional_context'][0]['positions']=[{'position':'WR','before_forecasted_bench_ids':['depth'],
        'after_forecasted_bench_ids':[],'outgoing_bench_ids':['depth'],'outgoing_starter_ids':[]}]
    done=finish(runtime,proposal,result)
    assert done['disposition']['disposition']=='review'
    assert 'positional_depth_cost' in done['disposition']['evidence']['review_reasons']
    result['scenario_simulation_count']=100
    done=finish(runtime,proposal,result)
    assert not done['availability']['final_trade_disposition']


def test_native_uncertainty_does_not_turn_into_missing_data_and_no_value_is_combined():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal,current_gain=False)
    set_delta(result,'three_year',0);set_delta(result,'career',0)
    done=finish(runtime,proposal,result,goals=(G.CAREER,))
    assert done['disposition']['disposition']=='no_clear_advantage'
    assert done['availability']['final_trade_disposition']
    assert done['decision_dimensions']['long_term_franchise_value']['combined_value'] is None


def test_required_material_current_metric_missing_stays_incomplete_even_with_native_coverage():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    result['material_assessment']['side_a']['championship_probability']='unavailable'
    done=finish(runtime,proposal,result)
    assert done['native_completion']['status']=='complete'
    assert not done['availability']['final_trade_disposition']
    assert done['disposition']['evidence']['unavailable_metrics']==['championship_probability']
    assert done['decision_completeness']['missing_authorities']==('championship_probability',)


def test_optional_first_place_diagnostic_does_not_replace_required_current_policy():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    result['team_deltas'][0]['competitive']['first_place_probability']=None
    done=finish(runtime,proposal,result)
    assert done['availability']['final_trade_disposition']
    assert done['disposition']['disposition']!='insufficient_evidence'


def test_package_guard_and_constraints_survive_native_completion():
    from tests.test_trade_decision_disposition import _package_assessment
    from fsffl.trade_decision.package_economics import PackageEconomicResolution as R
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    package=_package_assessment(R.SINGLETON_UNDERPAID,singleton_sender='alpha').model_copy(update={'proposal_id':proposal.proposal_id})
    result['package_economics']=package.model_dump(mode='json')
    done=finish(runtime,proposal,result)
    assert done['disposition']['disposition']=='decline'


def test_previously_ready_response_cannot_survive_a_new_source_mismatch():
    runtime,record,proposal=fixture();result=finish(runtime,proposal,seed(runtime,record,proposal))
    assert result['availability']['final_trade_disposition']
    result['horizon_asset_economics']['source']['publication_generation_id']='old'
    done=finalize_published_trade_decision(runtime,proposal,result)
    assert done['disposition']['disposition']=='insufficient_evidence'
    assert not done['availability']['final_trade_disposition']
    assert not done['decision_dimensions']['long_term_franchise_value']['available']


def test_frozen_pick_reference_identity_is_preserved_and_unknown_release_rejected():
    runtime,record,proposal=fixture();result=seed(runtime,record,proposal)
    result['horizon_asset_economics']['source']['pick_sources']={'future':{'release_id':'frozen-fixture-release'}}
    for horizon in ('three_year','career'):
        row=result['horizon_asset_economics'][horizon]
        for side in ('side_a','side_b'):
            scale={**row[side]['scale'],'scale_id':row[side]['scale']['scale_id']+':frozen-prior:frozen-fixture-release'}
            row[side]['scale']=scale;row['roster_adjusted'][side]['scale']=scale
    done=finish(runtime,proposal,result)
    assert done['availability']['final_trade_disposition']
    assert 'frozen-fixture-release' in done['disposition']['evidence']['native_horizons'][0]['scale']['scale_id']
    result['horizon_asset_economics']['source']['pick_sources']['future']['release_id']='other-release'
    assert not finish(runtime,proposal,result)['availability']['final_trade_disposition']
