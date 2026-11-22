"""Publication attaches evidence without replacing current production truth."""
from datetime import timedelta
import pytest
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.behavioral.historical_cases import compile_historical_owner_case
from fsffl.behavioral.dossier_publication import (PreparedOwnerDossier,publish_owner_dossier,
    DossierPublicationConflict,validate_enrichment)
from tests.test_contextual_owner_delivery import inputs,OBS


@pytest.fixture(params=('sqlite','postgres'))
def backend(request):
    if request.param=='sqlite':return None
    import os
    from urllib.parse import urlparse
    from pathlib import Path
    dsn=os.getenv('FSFFL_DOSSIER_TEST_DATABASE_URL')
    if not dsn:pytest.skip('isolated PostgreSQL service not configured')
    parsed=urlparse(dsn)
    if parsed.hostname not in ('localhost','127.0.0.1') or parsed.path!='/fsffl_dossier_test':
        raise ValueError('dossier tests must use the isolated local test database')
    import psycopg
    with psycopg.connect(dsn,autocommit=True) as connection:
        connection.execute('create schema if not exists fsffl')
        for name in ('20260909_004_durable_behavioral_evidence.sql','20260909_005_behavioral_runtime_context.sql'):
            connection.execute((Path('db/migrations')/name).read_text())
        for table in ('behavior_event','behavior_profile','behavior_season','behavior_runtime_context'):
            connection.execute('alter table fsffl.'+table+' enable row level security')
            connection.execute('truncate table fsffl.'+table)
    return dsn


def fixture(tmp_path,backend):
    kwargs,events=inputs();case=compile_historical_owner_case(**kwargs).case
    profiles=build_owner_behavior_profiles(events,as_of=OBS)
    if backend is None:store=BehavioralIntelligenceStore(tmp_path/'owners.sqlite3')
    else:
        from fsffl.behavioral.postgres_store import PostgresBehavioralIntelligenceStore
        store=PostgresBehavioralIntelligenceStore(backend)
    store.put_events(events);store.put_profiles(profiles)
    store.put_runtime_context(user_id='user',league_state_id='current-state',sleeper_league_external_id=case.provider_league_id,
        league_family_id=case.league_family_id,current_owner_by_roster=((e.roster_id,e.owner_id)for e in events))
    bundle=PreparedOwnerDossier(league_family_id=case.league_family_id,current_provider_league_id=case.provider_league_id,cases=(case,))
    return store,bundle,profiles,events


def test_dry_run_atomic_publish_idempotence_and_refresh(tmp_path,backend):
    store,bundle,profiles,events=fixture(tmp_path,backend)
    result=publish_owner_dossier(store=store,user_id='user',prepared=bundle)
    assert not result.published and result.changed_profiles==1 and result.attached_cases==1
    assert store.load_profiles(bundle.league_family_id)==tuple(sorted(profiles,key=lambda p:p.owner_id))
    result=publish_owner_dossier(store=store,user_id='user',prepared=bundle,publish=True)
    assert result.published and result.attached_cases==1
    restored=store.load_profiles(bundle.league_family_id)
    validate_enrichment(profiles,restored)
    assert not publish_owner_dossier(store=store,user_id='user',prepared=bundle,publish=True).published
    # Refresh prepared before attachment must preserve the newer persisted dossier.
    updated=store.put_refreshed_profiles(profiles,events=events)
    assert sum(len(p.historical_trade_cases)for p in updated)==1
    assert store.load_runtime_context('user')['league_state_id']=='current-state'


def test_cas_rejects_changed_profile_or_late_event_atomically(tmp_path,backend):
    store,bundle,profiles,events=fixture(tmp_path,backend)
    prepared=publish_owner_dossier(store=store,user_id='user',prepared=bundle).profiles
    newer=tuple(p.model_copy(update={'as_of':OBS+timedelta(days=1)})for p in profiles)
    store.put_profiles(newer)
    with pytest.raises(DossierPublicationConflict):
        store.put_profile_enrichment_if_unchanged(expected_profiles=profiles,profiles=prepared,expected_events=events)
    assert sum(len(p.historical_trade_cases)for p in store.load_profiles(bundle.league_family_id))==0
    store.put_profiles(profiles)
    extra=events[0].model_copy(update={'event_id':'newly-discovered-older-event'})
    store.put_events((extra,))
    with pytest.raises(DossierPublicationConflict):
        store.put_profile_enrichment_if_unchanged(expected_profiles=profiles,profiles=prepared,expected_events=events)
    assert sum(len(p.historical_trade_cases)for p in store.load_profiles(bundle.league_family_id))==0


def test_foreign_user_family_and_count_replacement_rejected(tmp_path,backend):
    store,bundle,profiles,events=fixture(tmp_path,backend)
    for candidate in (bundle.model_copy(update={'league_family_id':'foreign'}),
        bundle.model_copy(update={'current_provider_league_id':'foreign-league'})):
        with pytest.raises(ValueError,match='context'):
            publish_owner_dossier(store=store,user_id='user',prepared=candidate,publish=True)
    with pytest.raises(ValueError,match='context'):
        publish_owner_dossier(store=store,user_id='other-user',prepared=bundle,publish=True)
    changed=tuple(p.model_copy(update={'as_of':OBS+timedelta(seconds=1)})for p in profiles)
    with pytest.raises(ValueError,match='current profile truth'):validate_enrichment(profiles,changed)
    with pytest.raises(ValueError,match='membership'):validate_enrichment(profiles,())


def test_later_refresh_invalidates_newly_discovered_earlier_activity(tmp_path,backend):
    store,bundle,profiles,events=fixture(tmp_path,backend)
    publish_owner_dossier(store=store,user_id='user',prepared=bundle,publish=True)
    earlier=events[0].model_copy(update={'event_id':'new-earlier-source'})
    events=events+(earlier,)
    refreshed=store.put_refreshed_profiles(build_owner_behavior_profiles(events,as_of=OBS),events=events)
    assert sum(len(p.historical_trade_cases)for p in refreshed)==0


def test_existing_artifact_identity_and_owned_refresh_loader(tmp_path):
    from types import SimpleNamespace
    from dataclasses import replace
    from fsffl.behavioral.dossier_publication import dossier_artifact,load_admitted_dossier,enrich_current_profiles
    store,bundle,profiles,events=fixture(tmp_path,None)
    record=dossier_artifact(bundle,computed_at=OBS)
    class ArtifactStore:
        def get_latest_reusable_artifact(self,**kwargs):
            assert kwargs['scope_id']==bundle.league_family_id
            return record
    assert load_admitted_dossier(ArtifactStore(),family_id=bundle.league_family_id,
        current_provider_league_id=bundle.current_provider_league_id)==bundle
    attached=enrich_current_profiles(profiles,events=events,prepared=bundle)
    validate_enrichment(profiles,attached)
    assert sum(len(p.historical_trade_cases)for p in attached)==1
    with pytest.raises(ValueError,match='identity mismatch'):
        load_admitted_dossier(ArtifactStore(),family_id=bundle.league_family_id,current_provider_league_id='foreign')
    record=replace(record,key=replace(record.key,input_fingerprint='0'*64))
    with pytest.raises(ValueError,match='identity mismatch'):
        load_admitted_dossier(ArtifactStore(),family_id=bundle.league_family_id,current_provider_league_id=bundle.current_provider_league_id)


def test_real_service_consumes_staged_dossier_in_owned_sync(tmp_path):
    from types import SimpleNamespace
    from fsffl.behavioral.service import BehavioralIntelligenceService
    store,bundle,profiles,events=fixture(tmp_path,None)
    history=SimpleNamespace(league_family_id=bundle.league_family_id,current_league_external_id=bundle.current_provider_league_id,
        league_chain=(bundle.current_provider_league_id,),events=events,
        current_owner_by_roster=tuple((e.roster_id,e.owner_id)for e in events))
    class Source:
        def fetch_history(self,*args,**kwargs):return history
    calls=[]
    def loader(family,league):calls.append((family,league));return bundle
    service=BehavioralIntelligenceService(source=Source(),store=store,dossier_loader=loader)
    state=SimpleNamespace(players=(),as_of=OBS,league=SimpleNamespace(season=events[0].season))
    synced=service.sync_sleeper_league(state,sleeper_league_external_id=bundle.current_provider_league_id)
    assert len(calls)==1 and sum(len(p.historical_trade_cases)for p in synced.profiles)==1
    assert tuple(p.trade_count for p in synced.profiles)==tuple(p.trade_count for p in profiles)
    # A subsequent normal sync with no staged artifact keeps the valid attachment.
    service.dossier_loader=lambda *_:None
    again=service.sync_sleeper_league(state,sleeper_league_external_id=bundle.current_provider_league_id)
    assert sum(len(p.historical_trade_cases)for p in again.profiles)==1
    def broken_loader(*_):raise ValueError('invalid staged identity')
    service.dossier_loader=broken_loader
    intact=service.sync_sleeper_league(state,sleeper_league_external_id=bundle.current_provider_league_id)
    assert sum(len(p.historical_trade_cases)for p in intact.profiles)==1
    assert tuple(p.trade_count for p in intact.profiles)==tuple(p.trade_count for p in profiles)



def test_future_evidence_waits_for_a_newer_state_cutoff(tmp_path):
    from fsffl.behavioral.owner_resume import OwnerFranchiseResume
    from fsffl.behavioral.dossier_publication import enrich_current_profiles
    store,bundle,profiles,events=fixture(tmp_path,None)
    later=OBS+timedelta(days=1)
    case=bundle.cases[0].model_copy(update={'evidence_as_of':later})
    resume=OwnerFranchiseResume(league_family_id=bundle.league_family_id,owner_id=case.owner_id,
        evidence_as_of=later,tenure_reference='new-confirmation')
    bundle=bundle.model_copy(update={'cases':(case,),'resumes':(resume,)})
    old=enrich_current_profiles(profiles,events=events,prepared=bundle)
    assert all(not p.historical_trade_cases and p.franchise_resume is None for p in old)
    fresh=tuple(p.model_copy(update={'as_of':later}) for p in profiles)
    admitted=enrich_current_profiles(fresh,events=events,prepared=bundle)
    assert sum(len(p.historical_trade_cases) for p in admitted)==1
    assert sum(p.franchise_resume is not None for p in admitted)==1
