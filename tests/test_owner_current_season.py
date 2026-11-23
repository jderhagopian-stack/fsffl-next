from dataclasses import replace
from datetime import UTC,datetime,timedelta
from types import SimpleNamespace
import pytest
from fsffl.behavioral.sleeper_history import SleeperBehaviorHistorySource
from fsffl.behavioral.current_season import attach_current_season_activity
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.product.owner_current_season import current_owner_view
from fsffl.state.models import ProviderRef,PickAsset,PlayerAsset
from fsffl.trade_decision.models import BilateralTradeProposal,TradeLeg
from fsffl.trade_decision.owner_history import describe_owner_package_history
from tests.test_state_foundation import make_state

NOW=datetime(2026,11,23,tzinfo=UTC)


def history():
    created=datetime(2026,11,1,tzinfo=UTC)
    raw={'transaction_id':'one','status':'complete','type':'trade',
        'created':int(created.timestamp()*1000),'status_updated':int((created+timedelta(hours=1)).timestamp()*1000),
        'roster_ids':[1,2],'adds':{'p1':2},'drops':{'p1':1},
        'draft_picks':[{'season':'2027','round':1,'roster_id':2,'owner_id':1,'previous_owner_id':2}]}
    calls=[]
    def get(url):
        path=url.split('/v1')[1];calls.append(path)
        if path=='/league/live':return {'league_id':'live','season':'2026'}
        if path.endswith('/rosters'):return [{'roster_id':1,'owner_id':'a'},{'roster_id':2,'owner_id':'b'}]
        if path.endswith('/transactions/1'):return [raw,{**raw,'transaction_id':'future','status_updated':int((NOW+timedelta(days=1)).timestamp()*1000)}]
        return []
    result=SleeperBehaviorHistorySource(http_get_json=get,max_workers=2).fetch_history('live')
    assert len(calls)==20  # Existing acquisition only; no extra HTTP requests.
    return result


def profiles(h=None):
    h=h or history()
    return attach_current_season_activity(build_owner_behavior_profiles(h.events,as_of=NOW),history=h,season=2026,cutoff=NOW)


def test_receipts_keep_created_completed_observed_separate_and_bound_future():
    h=history();p=profiles(h)[0];a=p.current_season_activity
    assert a.trade_count==1 and a.picks_acquired_in_trades==1
    assert len(a.recent_moves)==1 and a.recent_moves[0].completed_at>a.recent_moves[0].event.occurred_at
    assert a.observed_at>NOW and a.recent_moves[0].observed_at>NOW
    assert len(a.recent_moves[0].source_sha256)==64
    assert OwnerBehaviorProfile.model_validate_json(p.model_dump_json())==p
    with pytest.raises(ValueError,match='owner/family'):
        OwnerBehaviorProfile.model_validate({**p.model_dump(),'owner_id':'foreign'})


def test_current_inventory_is_canonical_and_foreign_activity_is_not_attached():
    state=make_state(NOW);state=state.model_copy(update={'league':state.league.model_copy(update={
        'provider_refs':(ProviderRef(provider='sleeper',external_id='live'),)})})
    p=profiles()[0];view=current_owner_view(state,'team:b',p)
    assert len(view['picks'])==1 and view['picks'][0]['season']==2027
    assert view['counts']['trades']==1 and view['record'] is None
    assert 'Trades this season have added 1 net draft pick.' in view['insights']
    foreign=make_state(NOW)
    assert current_owner_view(foreign,'team:b',p)['counts'] is None


def test_live_facts_use_shared_consumer_but_never_future_observation_or_fake_context():
    p=profiles()[0]
    proposal=BilateralTradeProposal(proposal_id='x',as_of=NOW,
        side_a=TradeLeg(team_id='a',sends=(PlayerAsset(player_id='p1'),)),
        side_b=TradeLeg(team_id='b',sends=(PickAsset(pick_id='pick'),)))
    def describe(at,profile):
        return describe_owner_package_history(proposal.model_copy(update={'as_of':at}),team_id='a',
            profile=profile,player_positions={},source_state_id='state')
    assert not describe(NOW,p)['contextual_precedents']
    result=describe(NOW+timedelta(days=2),p)
    assert result['matching_features']==['directional_precedent']
    example=result['contextual_precedents'][0]
    assert example['record_context'] is None and example['trade_phase']=='unknown'
    assert example['sent_summary']=='1 player' and example['received_summary']=='1 draft pick'
    assert result['acceptance_probability'] is None and result['decision_effect']=='no_disposition_change'


def test_refresh_restore_preserves_first_observation_only_for_same_receipt(tmp_path):
    h=history();initial=profiles(h);store=BehavioralIntelligenceStore(tmp_path/'owners.sqlite3')
    store.put_events(h.events);store.put_refreshed_profiles(initial,events=h.events)
    later=replace(h,observed_at=h.observed_at+timedelta(days=1),current_completed_moves=tuple(
        m.model_copy(update={'observed_at':m.observed_at+timedelta(days=1)}) for m in h.current_completed_moves))
    newer=attach_current_season_activity(build_owner_behavior_profiles(h.events,as_of=NOW+timedelta(days=1)),
        history=later,season=2026,cutoff=NOW+timedelta(days=1))
    store.put_refreshed_profiles(newer,events=h.events)
    restored=store.load_profiles(h.league_family_id)[0]
    assert restored.current_season_activity.recent_moves[-1].observed_at==initial[0].current_season_activity.recent_moves[0].observed_at


def test_api_reads_live_inventory_and_explicit_refresh_reuses_existing_job(tmp_path,monkeypatch):
    from time import monotonic,sleep
    from fastapi.testclient import TestClient
    from fsffl.product.behavioral_runtime import BehavioralRuntimeCoordinator
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    from fsffl.behavioral.service import BehavioralSyncResult
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    h=history();ps=profiles(h);state=make_state(NOW)
    teams=tuple(t.model_copy(update={'provider_refs':(ProviderRef(provider='sleeper',external_id=str(i)),)}) for i,t in enumerate(state.teams,1))
    state=state.model_copy(update={'teams':teams,'league':state.league.model_copy(update={
        'provider_refs':(ProviderRef(provider='sleeper',external_id='live'),)})})
    history_store=BehavioralIntelligenceStore(tmp_path/'api.sqlite3');history_store.put_profiles(ps)
    history_store.put_runtime_context(user_id='local-beta-user',league_state_id=state.state_id,
        sleeper_league_external_id='live',league_family_id=h.league_family_id,current_owner_by_roster=h.current_owner_by_roster)
    calls=[]
    def work(s,external):
        calls.append((s.state_id,external))
        return BehavioralSyncResult(league_family_id=h.league_family_id,profile_count=2,total_event_count=len(h.events),
            inserted_event_count=0,reused_historical_league_ids=(),scanned_league_ids=('live',),
            current_owner_by_roster=h.current_owner_by_roster,profiles=ps)
    coordinator=BehavioralRuntimeCoordinator(work=work,store_factory=lambda:history_store,max_workers=1)
    runtime=PrivateBetaRuntimeStore();runtime.set_league_state('local-beta-user',state)
    client=TestClient(create_app(runtime_store=runtime,behavioral_coordinator=coordinator))
    response=client.get('/api/behavioral/profiles');assert response.status_code==200
    live=response.json()['profiles'][0]['current_season']
    assert live['state_id']==state.state_id and live['counts']['trades']==1
    assert live['picks'][0]['pick_id']=='pick:2027:1:a'
    assert not calls  # GET does not acquire or reconstruct anything.
    response=client.post('/api/behavioral/refresh');assert response.status_code==200
    deadline=monotonic()+2
    while not calls and monotonic()<deadline:sleep(.01)
    assert calls==[(state.state_id,'live')]


def test_completed_matchups_supply_current_record_not_archived_zero():
    from fsffl.state.models import LeagueMatchup,Provenance
    state=make_state(NOW)
    provenance=Provenance(source='fixture',effective_at=NOW,retrieved_at=NOW)
    state=state.model_copy(update={'completed_through_week':2,
        'league':state.league.model_copy(update={'rules':state.league.rules.model_copy(update={'fantasy_regular_season_end_week':14})}),
        'matchups':tuple(LeagueMatchup(week=w,team_a_id='team:b',team_b_id='team:a',
            team_a_points=a,team_b_points=b,provenance=provenance) for w,a,b in ((1,100,90),(2,80,90)))})
    view=current_owner_view(state,'team:b',profiles()[0])
    assert (view['record']['wins'],view['record']['losses'],view['record']['through_week'])==(1,1,2)
    assert current_owner_view(state,'team:a',profiles()[0])['record']['wins']==1
