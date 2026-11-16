from dataclasses import replace
from datetime import timedelta
from fastapi.testclient import TestClient

from fsffl.behavioral.models import BehavioralAsset, BehavioralEventKind
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.product.behavioral_runtime import BehavioralRuntimeCoordinator,cached_behavior_profile_for_team
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.owner_history_runtime import build_trade_owner_history
from fsffl.product.webapp import create_app
from fsffl.state.models import ProviderRef,PlayerAsset
from fsffl.trade_decision.models import BilateralTradeProposal,TradeLeg
from tests.test_behavioral_intelligence import _event
from tests.test_state_foundation import make_state


def fixture(tmp_path):
    state=make_state()
    state=state.model_copy(update={'teams':tuple(t.model_copy(update={'provider_refs':(
        ProviderRef(provider='sleeper',external_id='1' if t.team_id=='team:a' else '2'),)}) for t in state.teams)})
    qb=BehavioralAsset(kind='player',asset_ref='player:1',position='QB')
    rb=BehavioralAsset(kind='player',asset_ref='player:2',position='RB')
    trade=_event('first',acquired=(qb,),disposed=(rb,))
    other=trade.model_copy(update={'event_id':'other','owner_id':'owner-b','roster_id':2,
        'acquired':trade.disposed,'disposed':trade.acquired,'counterparty_owner_ids':('owner-a',)})
    waiver=_event('waiver',acquired=(rb,),disposed=()).model_copy(update={'kind':BehavioralEventKind.WAIVER})
    events=(trade,other,waiver)
    cutoff=state.as_of-timedelta(days=1)
    profiles=tuple(p.model_copy(update={'completed_trade_activity':None}) for p in build_owner_behavior_profiles(events,as_of=cutoff))
    disk=BehavioralIntelligenceStore(tmp_path/'history.sqlite3')
    disk.put_events(events);disk.put_profiles(profiles)
    disk.put_runtime_context(user_id='local-beta-user',league_state_id=state.state_id,sleeper_league_external_id='fixture',
        league_family_id=profiles[0].league_family_id,current_owner_by_roster=((1,'owner-a'),(2,'owner-b')))
    return state,disk,profiles


def test_cold_restart_binds_existing_history_via_actual_api_without_refresh_or_writes(tmp_path,monkeypatch):
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    state,disk,legacy=fixture(tmp_path)
    reads=[]
    for name in ('load_events','load_profiles','load_runtime_context'):
        original=getattr(disk,name)
        def record(*args,_original=original,_name=name,**kwargs):
            reads.append(_name);return _original(*args,**kwargs)
        monkeypatch.setattr(disk,name,record)
    def forbidden(*a,**k):raise AssertionError('Cold restore must not fetch, write or refresh')
    for name in ('put_events','put_profiles','put_runtime_context'):
        monkeypatch.setattr(disk,name,forbidden)
    coordinator=BehavioralRuntimeCoordinator(store_factory=lambda:disk,work=forbidden,max_workers=1)
    restored=coordinator.current('local-beta-user')
    assert restored.result is not None
    assert cached_behavior_profile_for_team(state,'team:b') is None
    store=PrivateBetaRuntimeStore();store.set_league_state('local-beta-user',state);store.select_team('local-beta-user','team:a')
    app=create_app(runtime_store=store,behavioral_coordinator=coordinator,state_loader=forbidden,forecast_loader=forbidden)
    client=TestClient(app)
    assert client.get('/api/behavioral/status').status_code==200
    assert cached_behavior_profile_for_team(state,'team:b').owner_id=='owner-b'
    assert client.get('/api/behavioral/profiles').status_code==200
    result=client.post('/api/opportunities/strategic-discover',json={'evaluation_budget':0,'max_candidates':8})
    assert result.status_code==200,result.text
    rows=result.json()['candidate_packages'];assert rows
    assert all(r['owner_history']['team:b']['status']=='observed' for r in rows)
    proposal=BilateralTradeProposal(proposal_id='post-restart',as_of=state.as_of,
        side_a=TradeLeg(team_id='team:a',sends=(PlayerAsset(player_id='player:1'),)),
        side_b=TradeLeg(team_id='team:b',sends=(PlayerAsset(player_id='player:2'),)))
    history=build_trade_owner_history(store.get('local-beta-user'),proposal)
    assert history['team:b']['facts'] and history['team:b']['trade_asset_detail_available']
    a=cached_behavior_profile_for_team(state,'team:a')
    assert a.acquired_positions=={'QB':1,'RB':1} and a.completed_trade_activity.acquired_positions=={'QB':1}
    assert reads==['load_runtime_context','load_profiles','load_events']
    # Publication is coalesced, including the exact same result through both APIs.
    import fsffl.product.behavioral_runtime as module
    original=module._publish_profiles_for_state
    assert original(state,restored.result) is False
    assert all(p.completed_trade_activity is None for p in legacy)


def test_restore_does_not_bind_a_different_state_or_use_future_profiles(tmp_path):
    state,disk,_=fixture(tmp_path)
    coordinator=BehavioralRuntimeCoordinator(store_factory=lambda:disk,max_workers=1)
    wrong=state.model_copy(update={'as_of':state.as_of+timedelta(seconds=1)})
    coordinator.current('local-beta-user',league_state=wrong)
    assert cached_behavior_profile_for_team(wrong,'team:b') is None


def test_restored_history_publication_coalesces_and_evicts_source_references(tmp_path,monkeypatch):
    import fsffl.product.behavioral_runtime as module
    state,disk,_=fixture(tmp_path)
    coordinator=BehavioralRuntimeCoordinator(store_factory=lambda:disk,max_workers=1)
    record=coordinator.current('local-beta-user')
    monkeypatch.setattr(module,'_MAX_PROFILE_CACHE_STATES',2)
    with module._profile_cache_lock:
        module._profile_cache.clear();module._profile_cache_state_order.clear();module._profile_cache_results.clear()
    states=[state.model_copy(update={'as_of':state.as_of+timedelta(days=i)}) for i in range(3)]
    for item in states:
        assert module._publish_profiles_for_state(item,record.result) is True
        assert module._publish_profiles_for_state(item,record.result) is False
    assert len(module._profile_cache_results)==2
    assert states[0].state_id not in module._profile_cache_results
    assert all(key[0] in module._profile_cache_results for key in module._profile_cache)
