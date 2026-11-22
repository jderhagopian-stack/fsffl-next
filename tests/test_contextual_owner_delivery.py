"""One vertical path: source normalization → grounded case → profile → restore."""
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
import pytest
from fsffl.behavioral.historical_cases import compile_historical_owner_case,attach_historical_owner_cases,preserve_historical_owner_cases
from fsffl.behavioral.sleeper_history import normalize_sleeper_behavior_transaction
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.behavioral.historical_circumstances import build_historical_trade_circumstances
from fsffl.state.historical_roster_context import _digest
from fsffl.state.historical_season_lineage import build_historical_season_lineage
from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
from tests.test_historical_circumstances import fixture,production,week
from tests.test_historical_cross_season_context import OBS,provider_case


def inputs(mutator=None,extra_production=()):
    original,old,_,_,_,_=fixture()
    for tx in original['transactions']:
        if tx['type']=='trade':tx['creator']='u1'
    if mutator is not None:mutator(original)
    data,source,_,spec=provider_case(original)
    source=source.model_copy(update={'raw_position_or_slot_codes':tuple(data['league']['roster_positions'])})
    _,_,_,priorlineage,_,_=fixture()
    lineage=build_historical_season_lineage(sources=(old,source),links=priorlineage.links)
    integration=build_sleeper_historical_context(seasons={source.season:data},lineage=lineage,rookie_drafts=(spec,),source_revision='fixture',source_observed_at=OBS)
    coverage=integration.trades.rows[0];history=integration.roster_histories[0]
    raw=next(t for t in data['transactions']if t['type']=='trade')
    owner_map={int(b.provider_roster_id):b.provider_manager_id for b in source.roster_bindings}
    events=tuple(event for tx in data['transactions'] for event in normalize_sleeper_behavior_transaction(tx,
        family_id=source.season.league_family_id,league_external_id=source.provider_ref.external_id,
        season=source.season.season,owner_by_roster=owner_map,player_positions={}))
    observed_production=production(old)
    if extra_production:observed_production=replace(observed_production,players=observed_production.players+tuple(extra_production))
    circumstances=build_historical_trade_circumstances(coverage=coverage,history=history,lineage=lineage,
        prior_production=observed_production,results=(week(source,1,coverage.request.completed_at-timedelta(days=7)),))
    return dict(event=events[0],circumstances=circumstances,history=history,source=source,
        season_data=data,player_names={'player-a':'Receiver A','player-b':'Runner B'},evidence_as_of=OBS),events


def test_source_to_case_to_profile_roundtrip_and_refresh_survival(tmp_path):
    kwargs,events=inputs();compiled=compile_historical_owner_case(**kwargs)
    assert compiled.case is not None and not compiled.blockers
    case=compiled.case
    assert case.sent[0]=='Receiver A' and case.received[0]=='Runner B'
    assert case.situation=='1–0 through Week 1'
    assert case.context_sentences==('They were 1–0 through Week 1.',)
    assert not case.learned_preference
    profiles=build_owner_behavior_profiles(events,as_of=OBS)
    enriched=attach_historical_owner_cases(profiles,events=events,cases=(case,))
    store=BehavioralIntelligenceStore(tmp_path/'history.sqlite3')
    store.put_events(events);store.put_profiles(enriched)
    restored=BehavioralIntelligenceStore(tmp_path/'history.sqlite3').load_profiles(case.league_family_id)
    assert next(p for p in restored if p.owner_id==case.owner_id).historical_trade_cases==(case,)
    refreshed=preserve_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS+timedelta(days=1)),
        previous_profiles=restored,events=events)
    assert next(p for p in refreshed if p.owner_id==case.owner_id).historical_trade_cases==(case,)
    assert all(not p.historical_trade_cases for p in refreshed if p.owner_id!=case.owner_id)


def test_counterparty_does_not_inherit_initiator_attribution():
    kwargs,events=inputs();kwargs['event']=events[1]
    result=compile_historical_owner_case(**kwargs)
    assert result.case is None and result.blockers==('initiating_account_not_witnessed',)


def test_missing_initiator_is_not_replaced_with_season_end_owner():
    kwargs,_=inputs();data=kwargs['season_data']
    next(t for t in data['transactions']if t['type']=='trade').pop('creator')
    # Changed source is rejected before any attribution fallback.
    with pytest.raises(ValueError,match='cohort'):compile_historical_owner_case(**kwargs)


def test_wrong_event_exchange_or_source_snapshot_never_gets_a_story():
    kwargs,_=inputs()
    kwargs['event']=kwargs['event'].model_copy(update={'disposed':()})
    with pytest.raises(ValueError,match='normalized source event'):compile_historical_owner_case(**kwargs)
    kwargs,_=inputs();kwargs['circumstances']=replace(kwargs['circumstances'],snapshot_id='wrong')
    with pytest.raises(ValueError,match='snapshot'):compile_historical_owner_case(**kwargs)


def test_removed_changed_or_future_events_do_not_survive_refresh():
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    profiles=attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,))
    changed=tuple(e.model_copy(update={'disposed':()})if e.owner_id==case.owner_id else e for e in events)
    fresh=build_owner_behavior_profiles(changed,as_of=OBS+timedelta(days=1))
    assert all(not p.historical_trade_cases for p in preserve_historical_owner_cases(fresh,previous_profiles=profiles,events=changed))
    earlier=build_owner_behavior_profiles(events,as_of=OBS-timedelta(days=1))
    assert all(not p.historical_trade_cases for p in attach_historical_owner_cases(earlier,events=events,cases=(case,)))
    assert all(not p.historical_trade_cases for p in attach_historical_owner_cases(profiles,events=(),cases=()))


def test_gapped_results_cannot_be_called_a_complete_team_record():
    kwargs,_=inputs();context=kwargs['circumstances'];team=context.teams[0]
    gapped=replace(team.records[0],weeks=(2,))
    kwargs['circumstances']=replace(context,teams=(replace(team,records=(gapped,)),)+context.teams[1:])
    case=compile_historical_owner_case(**kwargs).case
    assert case.situation is None and not case.context_sentences


def test_no_invented_starter_replacement_or_retained_nonmember():
    kwargs,_=inputs();context=kwargs['circumstances'];team=context.teams[0]
    fake=replace(team.prior_production[0],player_id='not-rostered')
    kwargs['circumstances']=replace(context,teams=(replace(team,prior_production=(fake,)),)+context.teams[1:])
    with pytest.raises(ValueError,match='roster facts'):compile_historical_owner_case(**kwargs)


def test_all_trade_sides_keep_same_transaction_key_and_only_one_initiator_case():
    kwargs,events=inputs();results=[]
    for event in events:results.append(compile_historical_owner_case(**{**kwargs,'event':event}))
    assert sum(r.case is not None for r in results)==1
    assert results[0].case.transaction_id==kwargs['circumstances'].transaction_id


def test_duplicate_case_revisions_need_explicit_selection():
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    with pytest.raises(ValueError,match='revision'):
        attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,case))


def test_existing_profile_api_serves_restored_cases_without_starting_work(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.behavioral_runtime import BehavioralRuntimeCoordinator
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    from fsffl.state.models import ProviderRef
    from tests.test_state_foundation import make_state
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    profiles=attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,))
    history=BehavioralIntelligenceStore(tmp_path/'api-history.sqlite3')
    history.put_events(events);history.put_profiles(profiles)
    state=make_state(as_of=OBS)
    teams=tuple(t.model_copy(update={'provider_refs':(ProviderRef(provider='sleeper',external_id=str(i)),)})for i,t in enumerate(state.teams,1))
    state=state.model_copy(update={'teams':teams,'league':state.league.model_copy(update={
        'provider_refs':(ProviderRef(provider='sleeper',external_id=case.provider_league_id),)})})
    runtime=PrivateBetaRuntimeStore();runtime.set_league_state('local-beta-user',state)
    history.put_runtime_context(user_id='local-beta-user',league_state_id=state.state_id,
        sleeper_league_external_id=case.provider_league_id,league_family_id=case.league_family_id,
        current_owner_by_roster=((1,'u1'),(2,'u2')))
    def forbidden(*a,**k):raise AssertionError('GET must not start provider/history work')
    coordinator=BehavioralRuntimeCoordinator(work=forbidden,store_factory=lambda:history,max_workers=1)
    client=TestClient(create_app(runtime_store=runtime,behavioral_coordinator=coordinator))
    response=client.get('/api/behavioral/profiles');assert response.status_code==200
    payload=response.json()
    owner=next(p for p in payload['profiles']if p['owner_id']=='u1')
    assert owner['historical_trade_cases'][0]['case_id']==case.case_id
    assert owner['historical_trade_cases'][0]['context_sentences']==['They were 1–0 through Week 1.']
    assert owner['current_team_id']==teams[0].team_id
    # Same provider-league continuity remains available after a harmless State advance.
    advanced=state.model_copy(update={'as_of':OBS+timedelta(days=1)})
    runtime.set_league_state('local-beta-user',advanced)
    continuity=client.get('/api/behavioral/profiles').json()
    assert continuity['status']=='updating' and continuity['profiles']
    # Reusing roster1/2 in a different league must not expose the old owner's casebook.
    foreign=advanced.model_copy(update={'league':advanced.league.model_copy(update={
        'provider_refs':(ProviderRef(provider='sleeper',external_id='foreign-league'),)})})
    runtime.set_league_state('local-beta-user',foreign)
    assert client.get('/api/behavioral/profiles').json()=={'status':'updating','profiles':[]}


def test_late_historical_activity_invalidates_case_but_later_new_activity_does_not():
    from fsffl.behavioral.models import BehavioralEventKind
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    profiles=attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,))
    extra=events[-1].model_copy(update={'event_id':'newly-discovered','occurred_at':case.created_at-timedelta(days=1),
        'kind':BehavioralEventKind.FREE_AGENT,'acquired':(),'disposed':()})
    late=events+(extra,)
    refreshed=preserve_historical_owner_cases(build_owner_behavior_profiles(late,as_of=OBS),previous_profiles=profiles,events=late)
    assert all(not p.historical_trade_cases for p in refreshed)
    later=events+(extra.model_copy(update={'occurred_at':case.activity_through+timedelta(days=1)}),)
    refreshed=preserve_historical_owner_cases(build_owner_behavior_profiles(later,as_of=OBS),previous_profiles=profiles,events=later)
    assert next(p for p in refreshed if p.owner_id==case.owner_id).historical_trade_cases==(case,)


def test_review_data_island_cannot_close_script_element(tmp_path):
    from scripts.review_contextual_owner_delivery import write_owner_review
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    profiles=attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,))
    profile=next(p for p in profiles if p.owner_id==case.owner_id)
    payload={'profiles':[{**profile.model_dump(mode='json'),'current_team_name':'</script><script>window.injected=true</script>'}]}
    html=write_owner_review(payload,tmp_path/'review').read_text()
    island=html.split('<script id="owner-review-data" type="application/json">')[1].split('</script>')[0]
    assert '</script>' not in island
    assert '\\u003c/script\\u003e' in island
    assert (tmp_path/'review/static/behavioral_intelligence.js').exists()


def test_same_batch_departure_is_not_described_as_a_retained_player():
    from fsffl.behavioral.historical_circumstances import HistoricalPlayerProduction
    def mutate(data):
        trade=data['transactions'][0];waiver=data['transactions'][1]
        waiver['status_updated']=trade['status_updated'];waiver['created']=trade['status_updated']-1000
        waiver['drops']={'same-batch-departure':1}
    kwargs,_=inputs(mutator=mutate,extra_production=(HistoricalPlayerProduction('same-batch-departure','WR',200.,16),))
    kwargs['player_names']={**kwargs['player_names'],'same-batch-departure':'Receiver C'}
    assert any(p.player_id=='same-batch-departure'for p in kwargs['circumstances'].teams[0].prior_production)
    case=compile_historical_owner_case(**kwargs).case
    assert case.retained_players==()
    assert all('Receiver C'not in text for text in case.context_sentences)
