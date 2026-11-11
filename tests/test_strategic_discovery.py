from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from fsffl.product.strategic_discovery import StrategicDiscoveryRequest, build_strategic_discovery, _ranks
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values, bind_trade_intrinsic_values
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.webapp import create_app
from fsffl.state.models import PlayerAsset
from tests.test_trade_intrinsic_evidence import fixture, build


def read_fixture():
    runtime,record,proposal=fixture()
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset({'a1','a2','a3','a4','b1'}),
        record=record,publication_validator=lambda c,r:True)
    return runtime,record,proposal,read


def test_project_once_bind_many_parity_identity_and_immutability():
    runtime,record,proposal,read=read_fixture()
    before=record.contract.model_dump(mode='json')
    assert bind_trade_intrinsic_values(runtime,proposal,read)==build(runtime,record,proposal)
    for changed in (replace(runtime,user_id='other'),replace(runtime,selected_team_id='beta'),
                    replace(runtime,publication_generation_id='other')):
        assert bind_trade_intrinsic_values(changed,proposal,read)['status']=='unavailable'
        result=build_strategic_discovery(changed,StrategicDiscoveryRequest(evaluation_budget=0),read=read)
        assert result['diagnostics']['raw_source'] is None
    assert record.contract.model_dump(mode='json')==before
    with pytest.raises(TypeError): read.values['career']['a1']=0


def test_protection_targets_handoff_shapes_and_source_zero_unknown():
    runtime,record,proposal,read=read_fixture()
    request=StrategicDiscoveryRequest(search_instructions={'objectives':['career_contribution'],'protected_player_ids':['a1']},
        target_asset_ref='player:b1',max_candidates=20,evaluation_budget=2)
    result=build_strategic_discovery(runtime,request,read=read)
    rows=result['candidate_packages']
    assert rows
    assert all('player:a1' not in row['trade_center_request']['focal_asset_refs'] for row in rows)
    assert all('player:b1' in row['trade_center_request']['counterparty_asset_refs'] for row in rows)
    assert all(row['trade_center_request']['search_instructions']==request.search_instructions.model_dump(mode='json') for row in rows)
    assert all(row['action_authority']=='diagnostic_only' for row in rows)
    assert result['diagnostics']['preliminary_decision_attempts']<=2
    assert result['diagnostics']['preliminary_decision_errors']==0
    assert result['diagnostics']['changed_state_simulation_calls']==0
    assert any(row['raw_horizon_trade_deltas']['career']['side_a'] is None for row in rows)


def test_rank_disagreement_has_shared_cohort_ties_not_identifier_bias():
    a,b,c=(PlayerAsset(player_id=x) for x in ('a','b','c'))
    assert _ranks({a:10,b:10,c:5})=={a:1,b:1,c:3}


def client_fixture(monkeypatch,provider=None,coordinator=None):
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    runtime,record,proposal,read=read_fixture()
    store=PrivateBetaRuntimeStore();store.set_league_state(runtime.user_id,runtime.league_state)
    store.select_team(runtime.user_id,'alpha');store.bind_publication_generation_id(runtime.user_id,'g1')
    calls=[]
    def provide(context,player_ids):
        calls.append(player_ids)
        if provider is not None:return provider(context,player_ids)
        return read_published_trade_horizon_values(context,player_ids=player_ids,record=record,publication_validator=lambda c,r:True)
    return TestClient(create_app(runtime_store=store,discovery_horizon_provider=provide,heavy_work_coordinator=coordinator)),runtime,store,calls


def test_actual_api_one_source_read_budgets_constraints_no_writes(monkeypatch):
    client,runtime,store,calls=client_fixture(monkeypatch)
    before=runtime.league_state.model_dump(mode='json')
    body={'max_candidates':8,'evaluation_budget':2,'search_instructions':{'objectives':['three_year_contribution']}}
    response=client.post('/api/opportunities/strategic-discover',json=body)
    assert response.status_code==200,response.text
    result=response.json()
    assert len(calls)==1
    assert result['diagnostics']['preliminary_decision_attempts']==2
    assert result['diagnostics']['preliminary_decision_errors']==0
    assert result['candidate_packages']
    assert store.get(runtime.user_id).league_state.model_dump(mode='json')==before
    for invalid in ({'max_candidates':81},{'evaluation_budget':9},{'counterparty_team_id':'alpha'},
                    {'target_asset_ref':'player:a1'}, {'counterparty_team_id':'unknown'},
                    {'search_instructions':{'objectives':[]}},
                    {'search_instructions':{'objectives':['career_contribution'],'protected_player_ids':['b1']}}):
        assert client.post('/api/opportunities/strategic-discover',json=invalid).status_code==422
    assert len(calls)==1


def test_raw_source_failure_keeps_partial_structural_results(monkeypatch):
    def broken(*args):raise ValueError('released source')
    client,_,_,calls=client_fixture(monkeypatch,provider=broken)
    response=client.post('/api/opportunities/strategic-discover',json={'max_candidates':4,'evaluation_budget':0})
    assert response.status_code==200,response.text
    assert response.json()['candidate_packages']
    assert response.json()['diagnostics']['raw_source'] is None
    assert len(calls)==1


def test_busy_existing_coordinator_fails_before_source(monkeypatch):
    from contextlib import contextmanager
    class Busy:
        @contextmanager
        def claim(self,**kwargs):
            assert kwargs['timeout_seconds']<=0.1
            raise TimeoutError('busy')
            yield
    client,_,_,calls=client_fixture(monkeypatch,coordinator=Busy())
    response=client.post('/api/opportunities/strategic-discover',json={})
    assert response.status_code==409,response.text
    assert calls==[]


def governed_runtime_fixture(*,superflex=True,team_count=12):
    """Synthetic point-in-time contracts, not historical/production forecasts."""
    from fsffl.state.models import League,LeagueRules,LeagueState,Team,TeamState,Player,PlayerState,RosterEntry,LineupRequirement,Provenance,DraftPick,PickOwnership
    from fsffl.value.cardinal_authority import FSFFLCardinalValueScore
    from tests.test_product_forecast_refresh import _forecast,_evidence
    from tests.test_dynasty_position_room import _career_current_components
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    runtime,_,_=fixture(); now=runtime.league_state.as_of
    teams=tuple(Team(team_id=f't{i}',league_id='fixture',display_name=f'Team {i}') for i in range(team_count))
    positions=('QB','QB','RB','RB','RB','RB','WR','WR','WR','WR','WR','WR','TE','TE')
    players=tuple(Player(player_id=f'{team.team_id}-{i}',full_name=f'{team.team_id} {pos} {i}',position=pos) for team in teams for i,pos in enumerate(positions))
    lineup=[LineupRequirement(slot=s,count=n) for s,n in (('QB',1),('RB',2),('WR',3),('TE',1),('FLEX',1))]
    lineup.append(LineupRequirement(slot='SUPERFLEX' if superflex else 'FLEX',count=1))
    if not superflex:lineup=[r for r in lineup if r.slot.value!='FLEX']+[LineupRequirement(slot='FLEX',count=2)]
    provenance=Provenance(source='synthetic',retrieved_at=now,effective_at=now)
    state=LeagueState(league=League(league_id='fixture',name='Synthetic',season=2026,rules=LeagueRules(team_count=team_count,roster_size=14,lineup=tuple(lineup),scoring=())),as_of=now,
        teams=teams,team_states=tuple(TeamState(team_id=t.team_id,roster=tuple(RosterEntry(player_id=p.player_id,slot='BENCH') for p in players if p.player_id.startswith(t.team_id+'-'))) for t in teams),
        players=players,player_states=tuple(PlayerState(player_id=p.player_id,as_of=now,provenance=provenance) for p in players),
        draft_picks=tuple(DraftPick(pick_id=f'pick-{t.team_id}',league_id='fixture',season=2027,round=1,original_team_id=t.team_id) for t in teams),
        pick_ownership=tuple(PickOwnership(pick_id=f'pick-{t.team_id}',owner_team_id=t.team_id) for t in teams))
    forecasts=tuple(_forecast().model_copy(update={'player_id':p.player_id,'position':p.position,'as_of':now,
        'distribution':_forecast().distribution.model_copy(update={'mean':max(10.,350.-i*7-(int(p.player_id.split('-')[0][1:])%3)*4)})}) for i,p in enumerate(players))
    evidence=replace(_evidence(),league_scored_forecasts=forecasts)
    scores=tuple(FSFFLCardinalValueScore(asset_id=p.player_id,asset_kind='player',score=100.+(i*73)%8000,as_of=now,market_context_id='synthetic') for i,p in enumerate(players))
    pick_scores=tuple(FSFFLCardinalValueScore(asset_id=f'pick-{t.team_id}',asset_kind='pick',score=4500.,as_of=now,market_context_id='synthetic',slot_certainty='generic_unknown_slot') for t in teams)
    runtime=replace(runtime,league_state=state,selected_team_id='t0',forecast_evidence=evidence,value_evidence=SimpleNamespace(fsffl_cardinal_values=(*scores,*pick_scores)))
    components={p.player_id:((i%17)*1.,(i%11)*2.,(i%7)*3.) for i,p in enumerate(players)}
    contract=_career_current_components(state,components,positions={p.player_id:p.position for p in players})
    contract=contract.model_copy(update={'estimates':tuple(r.model_copy(update={'long_horizon_raw_y4_y7_reference':800.,'terminal_raw_y8_plus_reference':200.}) for r in contract.estimates)})
    record=SimpleNamespace(user_id=runtime.user_id,league_state_id=state.state_id,status=IntrinsicBuildStatus.COMPLETED,contract=contract,intrinsic_input_fingerprint='synthetic-dependency')
    return runtime,record


@pytest.mark.parametrize('superflex',[True,False])
def test_twelve_team_governed_roster_screens_cut_costs_and_all_shapes(monkeypatch,superflex):
    import fsffl.product.strategic_discovery as module
    runtime,record=governed_runtime_fixture(superflex=superflex)
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(p.player_id for p in runtime.league_state.players),record=record,publication_validator=lambda c,r:True)
    before=runtime.league_state.model_dump(mode='json')
    calls=[];original=module.attach_provisional_position_floor_forecasts
    def shared(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(module,'attach_provisional_position_floor_forecasts',shared)
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(search_instructions={'objectives':['three_year_contribution']}),read=read)
    assert len(calls)==1
    assert result['diagnostics']['candidate_count']==80
    assert result['diagnostics']['pair_visits']<=640
    assert result['diagnostics']['preliminary_decision_attempts']==8
    assert result['diagnostics']['preliminary_decision_errors']==0
    assert set(result['diagnostics']['shapes'])=={'1_for_1','2_for_1','1_for_2','2_for_2'}
    screened=[r for r in result['candidate_packages'] if r['evidence_status']=='pre_simulation_screened']
    assert all(r['preliminary_decision_screen'] is not None for r in screened)
    assert any(any(c['required_cut_count']>0 for c in r['roster_legality']) for r in screened)
    assert all('current_competitiveness' in r['objective_assessment']['side_b']['unresolved'] for r in screened)
    assert any(any(a.startswith('pick:') for a in r['trade_center_request']['counterparty_asset_refs']) for r in result['candidate_packages'])
    assert runtime.league_state.model_dump(mode='json')==before


def test_complementary_horizons_are_investigated_with_sacrifices_visible(monkeypatch):
    import fsffl.product.trade_objectives as objective_module
    from fsffl.team_utility.utility import CalculatedCompetitiveState
    runtime,record,_=fixture()
    rows=record.contract.estimates
    record.contract=record.contract.model_copy(update={'estimates':(rows[0].model_copy(update={
        'long_horizon_raw_y4_y7_reference':2000.,'raw_career_forward_reference':2260.}),rows[1])})
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset({'a1','b1'}),record=record,publication_validator=lambda c,r:True)
    monkeypatch.setattr(objective_module,'calculated_competitive_state',lambda c:CalculatedCompetitiveState.REBUILDING)
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(search_instructions={'objectives':['three_year_contribution']}),read=read)
    complement=next(row for row in result['candidate_packages'] if row['pre_cut_horizon_complement_hypothesis'])
    assert complement['evidence_status']=='pre_simulation_screened'
    for side in ('side_a','side_b'):
        assert complement['objective_assessment'][side]['status']=='aligns_with_priorities'
        assert complement['objective_assessment'][side]['sacrifices']
    assert complement['non_dominated_within_comparable_evaluated_group'] is True
    assert complement['action_authority']=='diagnostic_only'
    assert complement['raw_horizon_trade_deltas']['career']['side_a']<0
    assert complement['raw_horizon_trade_deltas']['three_year']['side_a']>0


def test_protected_required_cuts_block_alignment_without_changing_cut_policy():
    runtime,record=governed_runtime_fixture(team_count=2)
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(p.player_id for p in runtime.league_state.players),record=record,publication_validator=lambda c,r:True)
    protected=[p.player_id for p in runtime.league_state.players if p.player_id.startswith('t0-') and p.player_id!='t0-0']
    request=StrategicDiscoveryRequest(search_instructions={'objectives':['three_year_contribution'],'protected_player_ids':protected},counterparty_team_id='t1')
    result=build_strategic_discovery(runtime,request,read=read)
    violated=[row for row in result['candidate_packages'] if row.get('objective_assessment',{}).get('side_a',{}).get('status')=='constraints_violated']
    assert violated
    assert all(row['non_dominated_within_comparable_evaluated_group'] is None for row in violated)
    assert all(row['objective_assessment']['side_a']['protected_players_lost'] for row in violated)


def test_admission_rechecks_current_team_before_reading_source(monkeypatch):
    from contextlib import contextmanager
    class ChangeSelection:
        store=None
        @contextmanager
        def claim(self,**kwargs):
            self.store.select_team('local-beta-user','beta')
            yield
    coordinator=ChangeSelection()
    client,_,store,calls=client_fixture(monkeypatch,coordinator=coordinator)
    coordinator.store=store
    response=client.post('/api/opportunities/strategic-discover',json={'search_instructions':{'objectives':['career_contribution'],'protected_player_ids':['a1']}})
    assert response.status_code==422
    assert calls==[]


def test_reused_projection_does_not_serialize_full_state_per_candidate(monkeypatch):
    import fsffl.state.serialization as serialization
    runtime,record,proposal,read=read_fixture()
    calls=[];original=serialization.deterministic_state_id
    def count(state):calls.append(state);return original(state)
    monkeypatch.setattr(serialization,'deterministic_state_id',count)
    for _ in range(80):
        assert bind_trade_intrinsic_values(runtime,proposal,read)['status']=='complete'
    assert not calls
    # An ephemeral reader cannot silently cross to another snapshot object.
    cloned=replace(runtime,league_state=runtime.league_state.model_copy())
    assert bind_trade_intrinsic_values(cloned,proposal,read)['status']=='unavailable'


def test_cheap_canonical_proposal_path_matches_existing_economics_and_rejects_mismatch():
    from fsffl.product.market_discovery_runtime import evaluate_candidate_economics,_proposal_from_row
    from fsffl.product.trade_center_view import build_trade_center_browser_view,owned_asset_index
    runtime,_=governed_runtime_fixture(team_count=2)
    row={'counterparty_team_id':'t1','send':[{'asset_ref':'player:t0-0'}],'receive':[{'asset_ref':'player:t1-0'}]}
    proposal=_proposal_from_row(runtime,row,prefix='market-economic')
    index=owned_asset_index(build_trade_center_browser_view(runtime.league_state,focal_team_id='t0'))
    old=evaluate_candidate_economics(runtime,row,asset_index=index)
    new=evaluate_candidate_economics(runtime,row,asset_index=index,proposal=proposal)
    assert old==new
    with pytest.raises(ValueError,match='does not match'):
        evaluate_candidate_economics(runtime,{**row,'send':[{'asset_ref':'player:t0-1'}]},asset_index=index,proposal=proposal)


def test_budget_limits_and_single_screen_failure_keep_other_results(monkeypatch):
    import fsffl.product.strategic_discovery as module
    runtime,_,_,read=read_fixture()
    calls=[];original=module.build_private_beta_trade_analysis
    def sometimes(*args,**kwargs):
        calls.append(1)
        if len(calls)==1:raise RuntimeError('one candidate unavailable')
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'build_private_beta_trade_analysis',sometimes)
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(max_candidates=4,evaluation_budget=2),read=read)
    assert result['diagnostics']['pair_visits']<=32
    assert result['diagnostics']['candidate_count']<=4
    assert result['diagnostics']['preliminary_decision_errors']==1
    assert [r['evidence_status'] for r in result['candidate_packages']].count('pre_simulation_screened')==1
    assert [r['evidence_status'] for r in result['candidate_packages']].count('screen_unavailable')==1
