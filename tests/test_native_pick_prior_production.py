from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from fsffl.persistence.native_pick_prior import persist_native_pick_release, restore_native_pick_release, release_key
from fsffl.product.presentation_continuity import PresentationContinuityStore, HOME_SURFACE
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values, bind_trade_intrinsic_values
from fsffl.state.models import DraftPick, PickOwnership, PickAsset
from fsffl.trade_decision.models import TradeLeg
from fsffl.value.career_tail import lineup_capacity_signature
from fsffl.value.native_pick_prior import NativePickPriorRelease, NativePickPriorReference, packaged_native_pick_reference, scoring_signature
from fsffl.value.origin_aware_pick import OriginPickProbabilityEvidence
from tests.test_trade_intrinsic_evidence import fixture as player_fixture
from tests.test_presentation_continuity import MemoryPersistence as BaseMemoryPersistence


class MemoryPersistence(BaseMemoryPersistence):
    def put_immutable_artifact(self, record):
        existing=next((r for r in self.artifacts if r.key==record.key),None)
        if existing is not None:return existing
        self.artifacts.append(record)
        return record


def fixture():
    runtime, record, proposal = player_fixture()
    old = runtime.league_state
    picks = tuple(DraftPick(pick_id=f'pick:{origin}', league_id=old.league.league_id, season=2027, round=1,
                           original_team_id=origin) for origin in ('alpha','beta'))
    state = old.model_copy(update={'draft_picks':picks,
        'pick_ownership':tuple(PickOwnership(pick_id=p.pick_id, owner_team_id=p.original_team_id) for p in picks)})
    release = NativePickPriorRelease(evaluation_season=2026, draft_season=2027, team_count=2, round_count=1,
        released_at=state.as_of-timedelta(days=1), source_as_of=state.as_of-timedelta(days=2),
        rules_signature=lineup_capacity_signature(state.league.rules), scoring_signature=scoring_signature(state.league.rules),
        source_fingerprints=('synthetic-source',), source_classes=(2019,2020), source_drafts=2, source_limitations=('synthetic',),
        slots=tuple({'rank':i,'annual_native_means':(v,v*.8,v*.6),
                     'career_authority':{'low':v,'reference_center':v*2.4,'high':v*3.8,'width':v*2.8},
                     'prefix_backoff_mass':0,'long_term_backoff_mass':.1} for i,v in ((1,100),(2,10))))
    distributions = tuple(OriginPickProbabilityEvidence(draft_season=2027,original_team_id=origin,
        slot_probabilities=({'slot_in_round':1,'probability':a},{'slot_in_round':2,'probability':1-a}),
        expected_slot=2-a, median_slot=1 if a>=.5 else 2, early_probability=a,mid_probability=0,late_probability=1-a,
        simulation_count=50000,simulation_model_version='synthetic',simulation_input_fingerprint='sim',
        draft_order_policy_id='synthetic',draft_order_policy_version='1',draft_order_policy_authority='synthetic',
        draft_order_projection_model_version='synthetic',provenance='synthetic') for origin,a in (('alpha',.25),('beta',.75)))
    analytics=SimpleNamespace(team_views=(),scenario_preparation=None,
        league_view=SimpleNamespace(context=SimpleNamespace(league_state_id=state.state_id)),
        simulation_result=SimpleNamespace(outcomes=(),simulation_count=50000,simulation_input_fingerprint='sim',future_pick_distributions=distributions))
    runtime=replace(runtime,league_state=state,simulation_analytics=analytics)
    record=SimpleNamespace(**{**vars(record),'league_state_id':state.state_id})
    proposal=proposal.model_copy(update={'side_a':TradeLeg(team_id='alpha',sends=(PickAsset(pick_id='pick:alpha'),))})
    return runtime, record, proposal, release


def read(runtime, record, release, fingerprint='sim'):
    return read_published_trade_horizon_values(runtime,player_ids=frozenset({'a1','b1'}), record=record,
        publication_validator=lambda c,r:True,pick_release=release,pick_simulation_fingerprint=fingerprint)


def test_released_coordinate_calendar_and_provenance_are_complete():
    *_,release=fixture()
    assert release.status=='bounded_provisional'
    assert release.source_as_of<=release.released_at
    assert release.release_id==NativePickPriorRelease.model_validate_json(release.model_dump_json()).release_id
    assert 'stddev' not in release.model_dump_json()
    reference=packaged_native_pick_reference()
    assert len(reference.release_id)==len(reference.scope_key)==64


def test_native_pick_player_binding_uses_origin_probabilities_and_same_calendar():
    runtime,record,proposal,release=fixture();before=runtime.league_state.model_dump_json()
    projection=read(runtime,record,release)
    expected=.25*(100*.85+80*.85**2)+.75*(10*.85+8*.85**2)
    assert projection.pick_values['three_year']['pick:alpha']==pytest.approx(expected)
    result=bind_trade_intrinsic_values(runtime,proposal,projection)
    assert result['status']=='complete'
    assert result['three_year']['side_a']['sent_mean']==pytest.approx(expected)
    assert result['career']['side_a']['sent_mean']==pytest.approx(.25*240+.75*24)
    assert result['three_year']['side_a']['mean_delta']==-result['three_year']['side_b']['mean_delta']
    assert result['career']['package_uncertainty'] is None
    assert result['source']['pick_sources']['pick:alpha']['status']=='bounded_provisional'
    assert runtime.league_state.model_dump_json()==before
    with pytest.raises(TypeError):projection.pick_values['career']['pick:alpha']=1


@pytest.mark.parametrize('failure',['old_release','rules','season','generation','simulation_state','simulation_fingerprint','preview','no_simulation'])
def test_bad_or_missing_evidence_withholds_only_the_pick_channel(failure):
    runtime,record,proposal,release=fixture()
    fingerprint='sim'
    if failure=='old_release':release=release.model_copy(update={'released_at':runtime.league_state.as_of+timedelta(seconds=1)})
    if failure=='rules':release=release.model_copy(update={'rules_signature':'other'})
    if failure=='season':release=release.model_copy(update={'evaluation_season':2027})
    if failure=='generation':runtime=replace(runtime,publication_generation_id=None)
    if failure=='simulation_state':runtime.simulation_analytics.league_view.context.league_state_id='other'
    if failure=='simulation_fingerprint':fingerprint='other'
    if failure=='preview':runtime.simulation_analytics.simulation_result.simulation_count=100
    if failure=='no_simulation':runtime=replace(runtime,simulation_analytics=None)
    if failure=='generation':
        with pytest.raises(ValueError):read(runtime,record,release,fingerprint)
        return
    projection=read(runtime,record,release,fingerprint)
    assert not projection.pick_values['career'] and projection.values['career']
    assert bind_trade_intrinsic_values(runtime,proposal,projection)['status']=='partial'


def test_ownership_changes_do_not_change_slot_release_or_origin_economics():
    runtime,record,proposal,release=fixture();before=read(runtime,record,release)
    state=runtime.league_state
    state=state.model_copy(update={'pick_ownership':tuple(p.model_copy(update={'owner_team_id':'beta'}) for p in state.pick_ownership)})
    runtime=replace(runtime,league_state=state)
    runtime.simulation_analytics.league_view.context.league_state_id=state.state_id
    record.league_state_id=state.state_id
    after=read(runtime,record,release)
    assert after.pick_values==before.pick_values
    assert after.pick_sources['pick:alpha']['owner_team_id']=='beta'
    assert after.pick_sources['pick:alpha']['release_id']==before.pick_sources['pick:alpha']['release_id']
    assert bind_trade_intrinsic_values(runtime,proposal,after)['status']=='unavailable'


def test_annual_persistence_reuses_shared_identity_and_preserves_older_release():
    *_,release=fixture();store=MemoryPersistence()
    persist_native_pick_release(store,release);persist_native_pick_release(store,release)
    assert len(store.artifacts)==2  # immutable baseline identity plus content-addressed curve
    restored=restore_native_pick_release(store,scope_key=release.economic_scope_key,release_id=release.release_id)
    assert restored==release
    changed=release.model_copy(update={'source_fingerprints':('explicit-new-source-version',)})
    with pytest.raises(ValueError,match='frozen'):persist_native_pick_release(store,changed)
    assert len(store.artifacts)==2 and release.release_id!=changed.release_id
    assert restore_native_pick_release(store,scope_key=release.economic_scope_key,release_id=release.release_id)==release


def test_manifest_pins_release_cold_restore_and_memory_only_request_reads(monkeypatch):
    runtime,record,proposal,release=fixture();store=MemoryPersistence();continuity=PresentationContinuityStore(store)
    persist_native_pick_release(store,release)
    monkeypatch.setattr('fsffl.product.presentation_continuity.packaged_native_pick_reference',
        lambda:NativePickPriorReference(release_id=release.release_id,scope_key=release.economic_scope_key,
            evaluation_season=release.evaluation_season,team_count=release.team_count,released_at=release.released_at))
    promoted=continuity.promote(user_id=runtime.user_id,runtime=runtime,builders=((HOME_SURFACE,lambda:{'status':'ready'}),))
    runtime=replace(runtime,publication_generation_id=promoted.publication_generation_id)
    reference,fp=continuity.native_pick_generation_hint(runtime)
    assert reference==release and fp=='sim'
    reads=store.read_count
    for _ in range(10):assert continuity.native_pick_generation_hint(runtime)==(release,'sim')
    assert store.read_count==reads
    assert continuity.native_pick_generation_hint(replace(runtime,publication_generation_id='other'))==(None,None)
    manifest=store.artifacts[-1]
    cold=PresentationContinuityStore(store)
    cold._remember_snapshot_manifest(user_id=runtime.user_id,league_id=runtime.league_state.league.league_id,
        league_state_id=runtime.league_state.state_id,selected_team_id=runtime.selected_team_id,manifest_payload=manifest.payload)
    assert cold.native_pick_generation_hint(runtime)==(release,'sim')
    old=dict(manifest.payload);old.pop('native_pick_prior_reference')
    cold._remember_snapshot_manifest(user_id=runtime.user_id,league_id=runtime.league_state.league.league_id,
        league_state_id=runtime.league_state.state_id,selected_team_id=runtime.selected_team_id,manifest_payload=old)
    assert cold.native_pick_generation_hint(runtime)[0] is None

    # A different tenant's normal State transition must not evict this shared
    # immutable model from a still-valid published reader.
    other=replace(runtime,user_id='another-user')
    cold._remember_snapshot_manifest(user_id=other.user_id,league_id=other.league_state.league.league_id,
        league_state_id=other.league_state.state_id,selected_team_id=other.selected_team_id,manifest_payload=manifest.payload)
    cold.clear_user_validation_hints(runtime.user_id)
    assert cold.native_pick_generation_hint(other)==(release,'sim')


def test_revoked_release_cannot_fall_back_to_packaged_values():
    runtime,_,_,release=fixture();store=MemoryPersistence();persist_native_pick_release(store,release)
    row=store.artifacts[1]
    store.artifacts[1]=replace(row,invalidated_at=runtime.league_state.as_of,invalidation_reason='test')
    # Production adapters expose invalidation metadata through their exact read.
    store.get_reusable_artifact=lambda key:store.artifacts[1]
    assert restore_native_pick_release(store,scope_key=release.economic_scope_key,release_id=release.release_id) is None
    with pytest.raises(ValueError):persist_native_pick_release(store,release)


def test_discovery_includes_pick_native_channels_and_keeps_both_team_objectives():
    from fsffl.product.strategic_discovery import StrategicDiscoveryRequest, build_strategic_discovery
    runtime,record,_,release=fixture();projection=read(runtime,record,release)
    request=StrategicDiscoveryRequest(target_asset_ref='pick:pick:beta',max_candidates=8,evaluation_budget=0,
        search_instructions={'objectives':['career_contribution']})
    result=build_strategic_discovery(runtime,request,read=projection)
    assert result['candidate_packages']
    assert result['pick_evidence']['pick:pick:beta']['career_intrinsic_status']=='bounded_provisional'
    assert result['pick_evidence']['pick:pick:beta']['career_intrinsic']==projection.pick_values['career']['pick:beta']
    assert any(row['raw_horizon_trade_deltas']['career']['side_a'] is not None for row in result['candidate_packages'])
    assert all(row['action_authority']=='diagnostic_only' for row in result['candidate_packages'])
    assert result['diagnostics']['changed_state_simulation_calls']==0


def test_prepared_pick_projection_cannot_outlive_its_published_simulation():
    runtime,record,proposal,release=fixture();projection=read(runtime,record,release)
    runtime.simulation_analytics.simulation_result.simulation_input_fingerprint='new'
    assert bind_trade_intrinsic_values(runtime,proposal,projection)['status']=='unavailable'


def test_bind_many_reuses_validated_state_identity_without_serialization(monkeypatch):
    runtime,record,proposal,release=fixture();projection=read(runtime,record,release)
    def forbidden(self):
        raise AssertionError('candidate binding must not serialize or fingerprint State')
    monkeypatch.setattr(type(runtime.league_state),'state_id',property(forbidden))
    for _ in range(20):
        assert bind_trade_intrinsic_values(runtime,proposal,projection)['status']=='complete'


def test_postgres_immutable_write_keeps_invalidated_first_writer(monkeypatch):
    from fsffl.persistence.postgres import PostgresPersistenceStore
    *_,release=fixture()
    record=SimpleNamespace(key=release_key(release.economic_scope_key,release.release_id),payload=release.model_dump(mode='json'),
        computed_at=release.released_at,invalidated_at=None,invalidation_reason=None)
    calls=[]
    row={**record.key.__dict__,'payload':record.payload,'computed_at':record.computed_at,
         'invalidated_at':record.computed_at,'invalidation_reason':'revoked'}
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):calls.append(sql)
        def fetchone(self):return row
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def cursor(self):return Cursor()
    store=PostgresPersistenceStore('postgresql://unused')
    monkeypatch.setattr(store,'_connect',lambda:Connection())
    result=store.put_immutable_artifact(record)
    assert not result.reusable
    assert 'do nothing' in calls[0] and 'do update' not in calls[0]
    assert 'invalidated_at is null' not in calls[1]
