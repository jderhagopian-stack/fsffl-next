"""Distinct bounded screens, signed scope, and bounded response reuse."""
from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from fsffl.product.progressive_discovery import ProgressiveDiscovery, MAX_TOTAL_SCREENS
from fsffl.product.strategic_discovery import StrategicDiscoveryRequest
from tests.test_strategic_discovery import read_fixture, governed_runtime_fixture


def synthetic_builder(monkeypatch, *, fits=()):
    from fsffl.product import progressive_discovery as module
    calls=[]
    def build(runtime,request,*,read,previously_screened,feedback_already_attempted):
        available=[f'p{i}' for i in range(60) if f'p{i}' not in previously_screened]
        picked=available[:request.evaluation_budget]
        calls.extend(picked)
        return {'candidate_packages':[{'point_id':p,'evaluation_kind':'root',
            'display_context':{'group':'preliminary_fit' if p in fits else 'priority_concern'}} for p in picked],
            'diagnostics':{'unexamined_pool_count':len(available)-len(picked),'repair_sequence_attempted':feedback_already_attempted}}
    monkeypatch.setattr(module,'build_strategic_discovery',build)
    return calls


def test_continuation_never_rescreens_and_stops_at_total_budget(monkeypatch):
    calls=synthetic_builder(monkeypatch)
    runtime,_,_,_=read_fixture()
    service=ProgressiveDiscovery()
    token=None
    for batch in range(4):
        result=service.build(runtime,StrategicDiscoveryRequest(continuation_token=token))
        progress=result['search_progress']
        assert progress['screens_this_batch']==8
        assert progress['total_screened']==8*(batch+1)
        token=progress['next_token']
    assert len(calls)==len(set(calls))==MAX_TOTAL_SCREENS
    assert token is None and progress['stop_reason']=='screening_limit'


def test_shortlist_ready_allows_explicit_continuation_without_replaying_first_batch(monkeypatch):
    calls=synthetic_builder(monkeypatch,fits=('p0','p1','p2','p3'))
    runtime,_,_,_=read_fixture();service=ProgressiveDiscovery()
    first=service.build(runtime,StrategicDiscoveryRequest())
    assert first['search_progress']['stop_reason']=='shortlist_ready'
    second=service.build(runtime,StrategicDiscoveryRequest(continuation_token=first['search_progress']['next_token']))
    assert second['search_progress']['total_screened']==16
    assert len(calls)==len(set(calls))
    replay=service.build(runtime,StrategicDiscoveryRequest())
    assert replay['search_progress']['cache_hit']
    assert len(calls)==16


@pytest.mark.parametrize('change',['user','team','generation','evidence','instructions','offer','tamper','expiry'])
def test_cursor_is_bound_to_exact_request_and_tenant(monkeypatch,change):
    calls=synthetic_builder(monkeypatch)
    runtime,_,_,_=read_fixture();clock=[100.]
    service=ProgressiveDiscovery(clock=lambda:clock[0])
    first=service.build(runtime,StrategicDiscoveryRequest())
    body={'continuation_token':first['search_progress']['next_token']}
    if change=='user':runtime=replace(runtime,user_id='someone-else')
    if change=='team':runtime=replace(runtime,selected_team_id='beta')
    if change=='generation':runtime=replace(runtime,publication_generation_id='other')
    if change=='evidence':runtime=replace(runtime,value_evidence=NS())
    if change=='instructions':body['search_instructions']={'objectives':['career_contribution']}
    if change=='offer':body['offered_asset_ref']='player:a1'
    if change=='tamper':body['continuation_token']='x'+body['continuation_token']
    if change=='expiry':clock[0]+=601
    with pytest.raises(ValueError,match='expired or its evidence/settings changed'):
        service.build(runtime,StrategicDiscoveryRequest(**body))
    assert len(calls)==8


def test_cache_has_entry_byte_and_expiry_bounds(monkeypatch):
    calls=synthetic_builder(monkeypatch)
    runtime,_,_,_=read_fixture();clock=[1.]
    service=ProgressiveDiscovery(clock=lambda:clock[0],max_entries=2,max_bytes=50000)
    for i in range(5):
        service.build(replace(runtime,user_id=str(i)),StrategicDiscoveryRequest())
    assert len(service.cache)<=2 and service.cache_bytes<=50000
    clock[0]+=301
    service.build(runtime,StrategicDiscoveryRequest())
    assert len(service.cache)==1
    too_small=ProgressiveDiscovery(max_bytes=1)
    too_small.build(runtime,StrategicDiscoveryRequest())
    assert not too_small.cache and too_small.cache_bytes==0


@pytest.mark.parametrize('superflex',[False,True])
def test_real_generation_new_batches_and_directed_player_pick_constraints(superflex):
    from fsffl.product.strategic_discovery import build_strategic_discovery,prepare_discovery
    runtime,_=governed_runtime_fixture(superflex=superflex,team_count=4)
    service=ProgressiveDiscovery()
    body={'offered_asset_ref':'pick:pick-t0','target_asset_ref':'player:t1-6','counterparty_team_id':'t1'}
    first=service.build(runtime,StrategicDiscoveryRequest(**body))
    assert first['candidate_packages']
    for row in first['candidate_packages']:
        assert 'pick:pick-t0' in row['trade_center_request']['focal_asset_refs']
        assert 'player:t1-6' in row['trade_center_request']['counterparty_asset_refs']
    ids={r['point_id'] for r in first['candidate_packages'] if r.get('evaluation_kind')}
    token=first['search_progress']['next_token']
    if token:
        second=service.build(runtime,StrategicDiscoveryRequest(**body,continuation_token=token))
        new={r['point_id'] for r in second['candidate_packages'] if r.get('evaluation_kind')}
        assert new and not ids & new
    pick=first['pick_evidence']['pick:pick-t0']
    assert pick['three_year_intrinsic_status']=='unavailable'
    assert pick['career_intrinsic_status']=='unavailable'
    with pytest.raises(ValueError,match='belong'):
        prepare_discovery(runtime,StrategicDiscoveryRequest(offered_asset_ref='player:t1-6'))
    with pytest.raises(ValueError,match='protected'):
        prepare_discovery(runtime,StrategicDiscoveryRequest(offered_asset_ref='player:t0-0',
            search_instructions={'protected_player_ids':['t0-0']}))


def test_busy_batch_fails_fast_and_releases_guard_on_error(monkeypatch):
    from fsffl.product import progressive_discovery as module
    from threading import Event,Thread
    runtime,_,_,_=read_fixture();service=ProgressiveDiscovery()
    entered,finish=Event(),Event();errors=[]
    def blocked(*args,**kwargs):
        entered.set();finish.wait(3)
        raise RuntimeError('controlled upstream failure')
    monkeypatch.setattr(module,'build_strategic_discovery',blocked)
    def run():
        try:service.build(runtime,StrategicDiscoveryRequest())
        except RuntimeError as error:errors.append(str(error))
    thread=Thread(target=run);thread.start();assert entered.wait(2)
    with pytest.raises(ValueError,match='already running'):
        service.build(runtime,StrategicDiscoveryRequest())
    finish.set();thread.join(3)
    assert errors and not service.inflight


def test_released_or_mismatched_native_source_cannot_reuse_valid_cursor(monkeypatch):
    synthetic_builder(monkeypatch)
    runtime,_,_,read=read_fixture();service=ProgressiveDiscovery()
    first=service.build(runtime,StrategicDiscoveryRequest(),read=read)
    with pytest.raises(ValueError,match='evidence/settings changed'):
        service.build(runtime,StrategicDiscoveryRequest(continuation_token=first['search_progress']['next_token']),read=None)


def test_real_api_continuation_and_retry_reuse_actual_screens(monkeypatch):
    from tests.test_strategic_discovery import client_fixture
    from fsffl.product import strategic_discovery as module
    client,runtime,store,_=client_fixture(monkeypatch)
    original=module.build_private_beta_trade_analysis;calls=[]
    def screen(current,proposal,**kwargs):
        calls.append(proposal.proposal_id)
        return original(current,proposal,**kwargs)
    monkeypatch.setattr(module,'build_private_beta_trade_analysis',screen)
    before=store.get(runtime.user_id).league_state
    body={'max_candidates':16,'evaluation_budget':2}
    first=client.post('/api/opportunities/strategic-discover',json=body)
    assert first.status_code==200,first.text
    assert len(calls)==2
    retry=client.post('/api/opportunities/strategic-discover',json=body)
    assert retry.status_code==200 and retry.json()['search_progress']['cache_hit']
    assert len(calls)==2
    token=first.json()['search_progress']['next_token']
    response=client.post('/api/opportunities/strategic-discover',json={**body,'continuation_token':token})
    assert response.status_code==200,response.text
    assert len(calls)==4 and len(set(calls))==4
    assert response.json()['search_progress']['total_screened']==4
    changed=client.post('/api/opportunities/strategic-discover',json={**body,'continuation_token':token,
        'search_instructions':{'objectives':['career_contribution']}})
    assert changed.status_code==409
    assert store.get(runtime.user_id).league_state==before


def test_pick_slot_context_uses_origin_and_keeps_incompatible_intrinsic_missing():
    from fsffl.product.discovery_pick_context import discovery_pick_context
    from tests.test_origin_aware_pick_value import _state,_simulation
    state=_state(owner_a='b',include_2028=True)
    baseline=NS(scenario_preparation=NS(source_state_id=state.state_id),
        simulation_result=_simulation(a=(.9,0,.1)))
    runtime=NS(league_state=state,value_evidence=None,simulation_analytics=baseline)
    rows=[{'send':[{'asset_ref':'pick:pick-2027-r1-a'}],
           'receive':[{'asset_ref':'pick:pick-2028-r1-a'}]}]
    result=discovery_pick_context(runtime,rows)
    near=result['pick:pick-2027-r1-a'];far=result['pick:pick-2028-r1-a']
    assert near['owner_team_id']=='b' and near['original_team_id']=='a'
    assert near['expected_slot']==pytest.approx(1.2)
    assert far['expected_slot'] is None
    assert near['market_value'] is None
    assert near['three_year_intrinsic_status']==far['career_intrinsic_status']=='unavailable'
    baseline.scenario_preparation.source_state_id='stale'
    assert discovery_pick_context(runtime,rows)['pick:pick-2027-r1-a']['expected_slot'] is None
