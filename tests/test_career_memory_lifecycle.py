"""Execute hosted lifecycle functions with bounded, synthetic dependencies."""
import ast
from contextlib import contextmanager
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


@pytest.mark.parametrize('snapshot_exists', [True, False])
@pytest.mark.parametrize('current_ready', [True, False])
def test_startup_restores_without_scheduling_career(snapshot_exists, current_ready):
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
        _career_intrinsic_coordinator=NS(restore_compatible_staged=lambda ctx:None,request=forbidden),
        _presentation_continuity=NS(has_snapshot=lambda **kwargs:snapshot_exists),
        _prepare_presentation_for_user=forbidden,
        _promote_presentation_for_user=lambda *args:(calls.append('promote') or NS(publication_generation_id='new-generation')),
        _startup_restore_complete=Event(), _log_startup_runtime_readiness=lambda:None, _logger=logger)
    run = function('src/fsffl/product/persistent_webapp.py','_run_lightweight_startup_restore',ns)
    run()
    assert ns['_startup_restore_state']['status'] == 'complete'
    assert calls == (['promote','bind'] if not snapshot_exists and current_ready else [])


def test_presentation_allocations_wait_for_existing_heavy_work():
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    coordinator = HeavyWorkCoordinator()
    entered = Event()
    requested = Event()
    context = NS(league_state=NS(state_id='fixture-state'))
    ns = dict(_presentation_continuity=NS(enabled=True),_heavy_work_coordinator=coordinator,
              _compose_presentation_for_user=lambda *args:(entered.set() or 'published'))
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
    thread.join(2)
    assert not thread.is_alive()
    assert result == ['published']


@pytest.mark.parametrize('preparation_fails', [False, True])
def test_optional_career_is_requested_only_after_durable_core_publication(preparation_fails):
    calls = []
    locked = False
    context = NS(league_state=NS(state_id='fixture-state',league=NS(league_id='fixture-league')))
    @contextmanager
    def sequence(user):
        nonlocal locked
        locked = True
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
    ns = dict(store=store,application=NS(state=NS(presentation_preparer=prepare,presentation_promoter=promoter)),
              _logger=NS(exception=lambda *args:calls.append('optional-error')))
    run = function('src/fsffl/product/webapp.py','publish_working_generation',ns)
    assert run('fixture-user') is context
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
