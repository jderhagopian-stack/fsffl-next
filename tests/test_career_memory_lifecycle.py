"""Execute hosted lifecycle functions with bounded, synthetic dependencies."""
import ast
from contextlib import contextmanager, nullcontext
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace as NS

import pytest


def function(path, name, namespace):
    tree = ast.parse(Path(path).read_text())
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.returns = None
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('career_published', [True, False])
@pytest.mark.parametrize('snapshot_exists', [True, False])
@pytest.mark.parametrize('current_ready', [True, False])
def test_startup_restores_without_scheduling_career(snapshot_exists, current_ready, career_published):
    context = NS(league_state=NS(state_id='fixture-state', league=NS(league_id='fixture-league')),
                 selected_team_id='fixture-team', publication_generation_id='fixture-generation',
                 forecast_evidence=object(), value_evidence=object(), simulation_analytics=object())
    calls = []
    def forbidden(*args):
        raise AssertionError('startup must not acquire or fit Career')
    logger = NS(info=lambda *args: None, warning=lambda *args: None)
    ns = dict(_startup_restore_state={}, _beta_restore_user='fixture-user',
        _journey_telemetry=NS(set_restore_id=lambda:(None,'fixture-restore'), reset_restore_id=lambda token:None),
        _runtime_store=NS(restore_user=lambda user:context, get=lambda user:context,
                         bind_publication_generation_id=lambda *args:calls.append('bind')),
        _shapley_intrinsic_coordinator=NS(restore_compatible_staged=lambda ctx:None,
            current=lambda ctx:NS(status='completed',contract=object()) if current_ready else None),
        IntrinsicBuildStatus=NS(COMPLETED='completed'),
        _career_intrinsic_coordinator=NS(restore_compatible_staged=lambda ctx:None,
            current=lambda ctx:NS(status="completed",contract=object()),request=forbidden),
        _presentation_continuity=NS(has_snapshot=lambda **kwargs:snapshot_exists,
            career_publication_matches=lambda *args:career_published),
        _prepare_presentation_for_user=forbidden,
        _promote_presentation_for_user=lambda *args:(calls.append('promote') or NS(publication_generation_id='new-generation')),
        _startup_restore_complete=Event(), _log_startup_runtime_readiness=lambda:None, _logger=logger)
    run = function('src/fsffl/product/persistent_webapp.py','_run_lightweight_startup_restore',ns)
    run()
    assert ns['_startup_restore_state']['status'] == 'complete'
    assert calls == (['promote'] if not (snapshot_exists and career_published) and current_ready else [])


def test_presentation_allocations_wait_for_existing_heavy_work():
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    coordinator = HeavyWorkCoordinator()
    entered, requested, sequence_entered = Event(), Event(), Event()
    context = NS(league_state=NS(state_id='fixture-state'), selected_team_id='fixture-team',publication_generation_id='fixture-generation')
    result_object = NS(publication_generation_id='published')
    bound = []
    @contextmanager
    def sequence(user):
        sequence_entered.set()
        yield
    ns = dict(_presentation_continuity=NS(enabled=True),_heavy_work_coordinator=coordinator,
              _compose_presentation_for_user=lambda *args:(entered.set() or result_object),
              _runtime_store=NS(publication_sequence=sequence,get=lambda user:context,
                                bind_publication_generation_id=lambda *args:bound.append(args)))
    promote = function('src/fsffl/product/persistent_webapp.py','_promote_presentation_for_user',ns)
    result = []
    def worker():
        requested.set()
        result.append(promote('fixture-user',context))
    with coordinator.claim(kind='intrinsic',key='fixture-build'):
        thread = Thread(target=worker)
        thread.start()
        assert requested.wait(1)
        assert not entered.wait(.05)
        assert not sequence_entered.is_set()
    thread.join(2)
    assert not thread.is_alive()
    assert result == [result_object]
    assert bound == [('fixture-user','published')]


@pytest.mark.parametrize('changed', ['state', 'team', 'generation'])
def test_startup_promotion_revalidates_identity_after_waiting_for_memory(changed):
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    coordinator = HeavyWorkCoordinator()
    original = NS(league_state=NS(state_id='fixture-state'), selected_team_id='fixture-team',
                  publication_generation_id='fixture-generation')
    active = [original]
    requested, sequence_entered = Event(), Event()
    @contextmanager
    def sequence(user):
        sequence_entered.set()
        yield
    def forbidden(*args):
        raise AssertionError('obsolete startup cannot compose or bind')
    ns = dict(_presentation_continuity=NS(enabled=True),_heavy_work_coordinator=coordinator,
              _compose_presentation_for_user=forbidden,
              _runtime_store=NS(publication_sequence=sequence,get=lambda user:active[0],
                                bind_publication_generation_id=forbidden))
    promote = function('src/fsffl/product/persistent_webapp.py','_promote_presentation_for_user',ns)
    result = []
    def worker():
        requested.set()
        result.append(promote('fixture-user',original))
    with coordinator.claim(kind='intrinsic',key='fixture-build'):
        thread = Thread(target=worker)
        thread.start()
        assert requested.wait(1)
        assert not sequence_entered.wait(.05)
        fields = dict(league_state=original.league_state,selected_team_id=original.selected_team_id,
                      publication_generation_id=original.publication_generation_id)
        fields[{'state':'league_state','team':'selected_team_id','generation':'publication_generation_id'}[changed]] = (
            NS(state_id='new-state') if changed == 'state' else 'new-identity')
        active[0] = NS(**fields)
    thread.join(2)
    assert not thread.is_alive()
    assert result == [None]


@pytest.mark.parametrize('preparation_fails', [False, True])
def test_optional_career_is_requested_only_after_durable_core_publication(preparation_fails):
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    coordinator = HeavyWorkCoordinator()
    requested, sequence_entered = Event(), Event()
    calls = []
    locked = False
    context = NS(league_state=NS(state_id='fixture-state',league=NS(league_id='fixture-league')))
    @contextmanager
    def sequence(user):
        nonlocal locked
        locked = True
        sequence_entered.set()
        try:yield
        finally:locked = False
    @contextmanager
    def read(user,ctx):
        yield
    def publish(*args,**kwargs):
        calls.append('publish')
        return context
    def prepare(user,ctx):
        assert not locked
        assert calls == ['checkpoint','compose','publish','durable']
        calls.append('career')
        if preparation_fails:raise RuntimeError('optional failure')
    store = NS(publication_sequence=sequence,get=lambda user:context,working_context=lambda user:context,
        checkpoint_working_generation=lambda user:(calls.append('checkpoint') or True),
        read_context=read,publish_working_generation=publish,
        wait_for_checkpoint=lambda *args,**kwargs:(calls.append('durable') or True))
    promoter = lambda *args:(calls.append('compose') or NS(publication_generation_id='fixture-generation'))
    def claim(**kwargs):
        requested.set()
        return coordinator.claim(**kwargs)
    ns = dict(store=store,heavy_claim=claim,application=NS(state=NS(presentation_preparer=prepare,presentation_promoter=promoter)),
              _logger=NS(exception=lambda *args:calls.append('optional-error')))
    run = function('src/fsffl/product/webapp.py','publish_working_generation',ns)
    results = []
    with coordinator.claim(kind='intrinsic',key='fixture-build'):
        thread = Thread(target=lambda:results.append(run('fixture-user')))
        thread.start()
        assert requested.wait(1)
        assert not sequence_entered.wait(.05)
    thread.join(2)
    assert not thread.is_alive()
    assert results == [context]
    assert calls == ['checkpoint','compose','publish','durable','career'] + (['optional-error'] if preparation_fails else [])


def test_hosted_wrapper_forwards_approved_reference_coordinates():
    standard = (object(),)
    league = (object(),)
    seen = {}
    def builder(state, **kwargs):
        seen.update(kwargs)
        return 'candidate-result'
    reader = object()
    ns = dict(build_live_p0_rostered_candidate_forecasts=builder,_projection_history_store=reader)
    run = function('src/fsffl/product/persistent_webapp.py','_hosted_career_candidate_builder',ns)
    assert "candidate_builder=_hosted_career_candidate_builder" in Path('src/fsffl/product/persistent_webapp.py').read_text()
    assert run(object(),projection_history_as_of='cutoff',
               reference_standard_year_one=standard,reference_league_year_one=league) == 'candidate-result'
    assert seen == dict(projection_history_as_of='cutoff',projection_history_reader=reader,
                        reference_standard_year_one=standard,reference_league_year_one=league)


def test_all_live_source_corrections_change_manifest_binding():
    from datetime import UTC, datetime
    from fsffl.product.p0_live_candidate_runtime import (
        LIVE_INPUT_SOURCE_NAMES, live_source_manifest, valid_live_source_manifest,
    )
    from fsffl.persistence.contracts import canonical_fingerprint
    fingerprints = {name:'a'*64 for name in LIVE_INPUT_SOURCE_NAMES}
    original = live_source_manifest(captured_at=datetime(2026,10,16,tzinfo=UTC),fingerprints=fingerprints)
    assert valid_live_source_manifest(original)
    bound = canonical_fingerprint('career-complete-live-inputs-v1','publication',original['digest'])
    for name in LIVE_INPUT_SOURCE_NAMES:
        revised = live_source_manifest(captured_at=datetime(2026,10,16,tzinfo=UTC),
            fingerprints={**fingerprints,name:'b'*64})
        assert valid_live_source_manifest(revised)
        assert canonical_fingerprint('career-complete-live-inputs-v1','publication',revised['digest']) != bound
    assert not valid_live_source_manifest({**original,'fingerprints':{}})


def test_typed_weekly_prior_and_catalog_corrections_change_source_digests():
    from dataclasses import replace
    from datetime import UTC, datetime
    from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperSeasonStatLine
    from fsffl.product.p0_live_candidate_runtime import _rows_digest, _input_digest
    captured = datetime(2026,10,16,tzinfo=UTC)
    weekly = SleeperWeeklyStatLine('fixture-player',2026,5,{'rush_yd':10.},captured)
    prior = SleeperSeasonStatLine('fixture-player',2025,{'rush_yd':100.},captured)
    assert _rows_digest((weekly,)) != _rows_digest((replace(weekly,stats={'rush_yd':11.}),))
    assert _rows_digest((prior,)) != _rows_digest((replace(prior,stats={'rush_yd':101.}),))
    assert _input_digest({'fixture-player':{'years_exp':1}}) != _input_digest({'fixture-player':{'years_exp':2}})


def test_completed_career_waits_for_visible_presentation_before_serializing(monkeypatch):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import fsffl.product.foundation4_shadow_routes as routes
    from datetime import UTC, datetime
    state = NS(state_id='fixture-state')
    context = NS(league_state=state, publication_generation_id='old-generation')
    serialized = []
    contract = NS(model_dump=lambda **kwargs:(serialized.append(True) or {'estimates':[]}))
    record = NS(status=routes.IntrinsicBuildStatus.COMPLETED, contract=contract,
                league_state_id=state.state_id, intrinsic_input_fingerprint='career-dependency')
    visible = [False]
    monkeypatch.setattr(routes, '_career_position_depth_rows', lambda *args: [])
    monkeypatch.setattr(routes, 'career_lens_for_publication', lambda *args, **kwargs: ({}, {}))
    monkeypatch.setattr(routes, 'build_dynasty_position_rooms', lambda *args, **kwargs: [])
    app = FastAPI()
    routes.install_career_intrinsic_routes(app,
        runtime_store=NS(get=lambda user:context),
        loader=NS(pin_build_context=lambda ctx:NS(career_fingerprint_evaluation_as_of=datetime.now(UTC))),
        coordinator=NS(current=lambda ctx:record),
        career_publication_validator=lambda ctx, rec:visible[0])
    career = next(r.endpoint for r in app.routes if r.path == routes.CAREER_INTRINSIC_ENDPOINT)
    dynasty = next(r.endpoint for r in app.routes if r.path == '/api/league/dynasty-position-rooms')
    request = NS(url=NS(path=routes.CAREER_INTRINSIC_ENDPOINT))
    pending = career(request, state_id=state.state_id,
                     publication_generation_id='old-generation', user_id='fixture-user')
    assert isinstance(pending, JSONResponse) and pending.status_code == 202
    assert b'publication_pending' in pending.body
    assert serialized == []  # No large contract allocation while promotion is pending.
    assert dynasty(state.state_id, 'old-generation', 'fixture-user')['status'] == 'preparing'
    context.publication_generation_id = 'new-generation'
    visible[0] = True
    obsolete = career(request, state_id=state.state_id,
                      publication_generation_id='old-generation', user_id='fixture-user')
    assert obsolete.status_code == 409 and serialized == []
    ready = career(request, state_id=state.state_id,
                   publication_generation_id='new-generation', user_id='fixture-user')
    assert ready['status'] == 'ready'
    assert ready['publication_generation_id'] == 'new-generation'
    assert serialized == [True]
    assert dynasty(state.state_id, 'new-generation', 'fixture-user')['status'] == 'ready'


@pytest.mark.parametrize('published', [True, False])
def test_value_lens_overlay_waits_for_its_published_career_dependency(published):
    context = NS(league_state=NS(state_id='fixture-state'), publication_generation_id='generation',
                 forecast_evidence=object())
    record = object()
    consumed = []
    def attach(payload, **kwargs):
        consumed.append(kwargs['record'])
        return dict(payload)
    ns = dict(career_record_loader=lambda ctx:record,
              career_publication_validator=lambda ctx, rec:published,
              background_coordinator=None,attach_career_player_lenses=attach)
    overlay = function('src/fsffl/product/league_value_lens_routes.py','with_career',ns)
    overlay({'league_state_id':'fixture-state','publication_generation_id':'generation'},context,persisted=True)
    assert consumed == [record if published else None]


def test_player_intelligence_withholds_unpublished_career_without_changing_current():
    from fastapi import FastAPI
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    from fsffl.product.career_presentation import career_lens_for_publication
    from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability
    current = NS(status=NS(value='ready'), estimates=(object(),), status_reason=None)
    career = NS(status=IntrinsicBuildStatus.COMPLETED, league_state_id='fixture-state',
        intrinsic_input_fingerprint='career-fp',contract=NS(estimates=(
            NS(player_id='fixture-a',raw_career_forward_reference=10.),
            NS(player_id='fixture-b',raw_career_forward_reference=20.))))
    runtime = NS(league_state=NS(state_id='fixture-state'), publication_generation_id='old')
    checks = []
    def validate(context, record):
        checks.append((context.publication_generation_id, record))
        return context.publication_generation_id == 'new'
    ns = dict(app=FastAPI(), Depends=lambda fn:None, require_user=lambda:None,
        _validated_player_id=lambda pid:pid, runtime_store=NS(get=lambda user:runtime),
        intrinsic_coordinator=NS(request=lambda ctx:NS(status=IntrinsicBuildStatus.COMPLETED,contract=current)),
        build_player_intelligence_overview=lambda *args,**kwargs:{'value':{'raw_shapley_marginal_points':7.5}},
        future_forecasts=object(), career_record_loader=lambda ctx:career,
        career_publication_validator=validate, career_lens_for_publication=career_lens_for_publication,
        career_reference_ids_from_current=lambda rec:frozenset({'fixture-a','fixture-b'}),
        IntrinsicBuildStatus=IntrinsicBuildStatus,ShapleyIntrinsicAvailability=ShapleyIntrinsicAvailability,
        _logger=NS(info=lambda *args:None))
    endpoint = function('src/fsffl/product/player_intelligence_routes.py','player_intelligence',ns)
    pending = endpoint('fixture-a','fixture-user')
    assert pending['publication_generation_id'] == 'old'
    assert pending['value']['career_status'] == 'unavailable'
    assert pending['value']['raw_career_forward_reference'] is None
    assert pending['value']['raw_shapley_marginal_points'] == 7.5
    runtime.publication_generation_id = 'new'
    ready = endpoint('fixture-a','fixture-user')
    assert ready['publication_generation_id'] == 'new'
    assert ready['value']['raw_career_forward_reference'] == 10.
    assert ready['value']['career_intrinsic_index'] == 0.
    assert ready['value']['raw_shapley_marginal_points'] == 7.5
    assert checks == [('old',career),('new',career)]
    source = Path('src/fsffl/product/persistent_webapp.py').read_text().split('install_player_intelligence_routes(',1)[1].split('install_provisional_k_dst_routes(',1)[0]
    assert 'career_publication_validator=_presentation_continuity.career_publication_matches' in source


def test_heavy_admission_refuses_over_hard_cap_and_releases_ownership(monkeypatch):
    import fsffl.product.resource_coordinator as resource
    resident = 513 * 1024 * 1024
    monkeypatch.setattr(resource, 'current_rss_bytes', lambda: resident)
    monkeypatch.setattr(resource, 'process_peak_rss_bytes', lambda: resident)
    monkeypatch.setattr(resource, 'release_unused_process_memory', lambda **kwargs: {})
    coordinator = resource.HeavyWorkCoordinator(memory_limit_bytes=512 * 1024 * 1024)
    with pytest.raises(MemoryError, match='before heavy-work admission'):
        with coordinator.claim(kind='intrinsic',key='fixture'):
            raise AssertionError('over-limit model work must not start')
    assert coordinator.snapshot().active_kind is None
    assert coordinator.snapshot().waiting_count == 0


def test_heavy_admission_reclaims_before_work_and_preserves_career_target_exception(monkeypatch):
    import fsffl.product.resource_coordinator as resource
    resident = [513 * 1024 * 1024]
    monkeypatch.setattr(resource, 'current_rss_bytes', lambda: resident[0])
    monkeypatch.setattr(resource, 'process_peak_rss_bytes', lambda: resident[0])
    def reclaim(**kwargs):
        resident[0] = 455 * 1024 * 1024
        return {}
    monkeypatch.setattr(resource, 'release_unused_process_memory', reclaim)
    coordinator = resource.HeavyWorkCoordinator(memory_limit_bytes=512 * 1024 * 1024)
    with coordinator.claim(kind='intrinsic',key='fixture'):
        assert resident[0] > coordinator.memory_budget_bytes
        assert resident[0] < 512 * 1024 * 1024
    assert coordinator.snapshot().active_kind is None


def test_shapley_integer_memoization_is_bounded_and_eviction_preserves_exact_results():
    import fsffl.value.shapley_intrinsic as shapley
    caps = (((0,),12),((1,),24),((2,),36),((3,),12),((0,1,2,3),96))
    valid, options = shapley._valid_counts_cached, shapley._replacement_options_cached
    valid.cache_clear(); options.cache_clear()
    try:
        for n in range(shapley.SHAPLEY_FEASIBILITY_CACHE_MAXSIZE + 257):
            counts = (n%48,(n//48)%48,(n//2304)%24,0)
            incoming = n%4
            assert options(caps,counts,incoming) == options.__wrapped__(caps,counts,incoming)
        for cache in (valid,options):
            info = cache.cache_info()
            assert info.maxsize == shapley.SHAPLEY_FEASIBILITY_CACHE_MAXSIZE == 32768
            assert info.currsize <= info.maxsize
        # Earlier keys may have been evicted; recomputation is still identical.
        for incoming in range(4):
            assert options(caps,(0,0,0,0),incoming) == options.__wrapped__(caps,(0,0,0,0),incoming)
    finally:
        valid.cache_clear(); options.cache_clear()


@pytest.mark.parametrize('retry_after_reuse', [False, True])
@pytest.mark.parametrize('preparation_fails', [False, True])
def test_explicit_core_reuse_retries_optional_career_without_rebuilding(retry_after_reuse, preparation_fails):
    calls = []
    context = NS(league_state=NS(state_id='fixture-state'))
    def prepare(user, runtime):
        assert user == 'fixture-user' and runtime is context
        calls.append('prepare')
        if preparation_fails:
            raise RuntimeError('optional failure')
    ns = dict(reconcile=lambda progress:'core reused',
        retry_optional_after_reuse=retry_after_reuse,
        require_active_league_identity=lambda:calls.append('identity'),
        store=NS(get=lambda user:context,working_generation_active=lambda user:False),
        application=NS(state=NS(presentation_preparer=prepare)),
        user_id='fixture-user',_logger=NS(exception=lambda *args:calls.append('optional-error')))
    run = function('src/fsffl/product/webapp.py','work',ns)
    assert run(lambda *args:None) == 'core reused'
    assert calls == (['identity','prepare'] + (['optional-error'] if preparation_fails else [])
                     if retry_after_reuse else [])
