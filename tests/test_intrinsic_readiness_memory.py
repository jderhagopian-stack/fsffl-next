"""Hosted readiness uses bounded completion facts, never a model restore."""
import gc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace as NS
from weakref import ref

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.intrinsic_background import ShapleyIntrinsicBackgroundCoordinator, IntrinsicBuildStatus
from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability, build_shapley_intrinsic_contract,
    build_unavailable_shapley_intrinsic_contract,
)
from tests.test_shapley_intrinsic_contract import _result
from tests.test_career_memory_lifecycle import function


def context(user='fixture',state='state',league='league'):
    return NS(user_id=user,league_state=NS(state_id=state,league=NS(league_id=league)),
        publication_generation_id='generation',selected_team_id='team',served_intelligence=None)


def forbidden(*args,**kwargs):
    raise AssertionError('readiness must not pin, fingerprint, load, restore or claim heavy work')


def hosted(coordinator):
    ns=dict(IntrinsicBuildStatus=IntrinsicBuildStatus,
        ShapleyIntrinsicAvailability=ShapleyIntrinsicAvailability,VNEXT_FORECAST_VERSION='fixture',
        _shapley_intrinsic_coordinator=coordinator,
        _webapp=NS(_runtime_capability_readiness=lambda ctx:{
            'overall_status':'full',**{k:{'status':'full'} for k in ('forecast','simulation','current_value')}}),
        _presentation_continuity=NS(has_snapshot=lambda **kwargs:True))
    ns['_intrinsic_readiness_from_record']=function('src/fsffl/product/persistent_webapp.py','_intrinsic_readiness_from_record',ns)
    return function('src/fsffl/product/persistent_webapp.py','_hosted_capability_readiness',ns)


@pytest.mark.parametrize('availability',['full','partial','unavailable'])
def test_repeated_http_readiness_after_weak_release_preserves_truth_without_restoring(availability):
    contract=build_shapley_intrinsic_contract(_result())
    if availability=='partial':
        contract=contract.model_copy(update={'coverage':contract.coverage.model_copy(update={'year_2_i1_players':0})})
    elif availability=='unavailable':
        contract=build_unavailable_shapley_intrinsic_contract(evaluation_season=2026,reason='fixture missing facts',missing_required_fact_families=('fixture',))
    loader=NS(restore_compatible=lambda _:contract)
    coordinator=ShapleyIntrinsicBackgroundCoordinator(loader,
        intrinsic_input_fingerprint_resolver=lambda _:'input',forecast_coordinate_resolver=lambda _:'forecast')
    ctx=context(); reader=hosted(coordinator)
    try:
        owned=coordinator.restore_compatible(ctx)
        assert owned.completion_summary.estimate_count==len(contract.estimates)
        expected=reader(ctx)['intrinsic']
        assert expected['status']=={'full':'full','partial':'partial_provisional','unavailable':'unavailable'}[availability]
        handle=ref(contract)
        assert coordinator.release_completed_contract(ctx,contract)
        del owned,contract
        gc.collect()
        assert handle() is None # Summary cannot retain the full contract graph.
        loader.restore_compatible=forbidden
        loader.pin_build_context=forbidden
        coordinator._intrinsic_input_fingerprint_resolver=forbidden
        coordinator.current=forbidden
        coordinator.restore_compatible_staged=forbidden
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert all(r['intrinsic']==expected for r in pool.map(lambda _:reader(ctx),range(100)))
        # Minimal HTTP harness executes the same hosted callback as the real status route.
        app=FastAPI()
        app.get('/api/intelligence/status')(lambda:reader(ctx))
        with TestClient(app) as client:
            for _ in range(10):
                response=client.get('/api/intelligence/status')
                assert response.status_code==200 and response.json()['intrinsic']==expected
    finally:
        coordinator._executor.shutdown(wait=True)


def test_readiness_exact_scope_ambiguity_and_invalidation_fail_closed():
    contract=build_shapley_intrinsic_contract(_result())
    coordinator=ShapleyIntrinsicBackgroundCoordinator(NS(restore_compatible=lambda _:contract),
        intrinsic_input_fingerprint_resolver=lambda _:'input',forecast_coordinate_resolver=lambda _:'forecast')
    ctx=context()
    try:
        owned=coordinator.restore_compatible(ctx)
        coordinator._intrinsic_input_fingerprint_resolver=forbidden
        assert coordinator.readiness_record_for_state(ctx) is owned
        assert coordinator.readiness_record_for_state(context(user='other')) is None
        assert coordinator.readiness_record_for_state(context(state='other')) is None
        assert coordinator.readiness_record_for_state(context(league='other')) is None
        coordinator._records[('fixture','league','ambiguous')]=replace(owned,intrinsic_input_fingerprint='ambiguous')
        assert coordinator.readiness_record_for_state(ctx) is None
        coordinator.clear_user('fixture')
        assert coordinator.readiness_record_for_state(ctx) is None
    finally:
        coordinator._executor.shutdown(wait=True)


def test_fresh_background_completion_retains_summary_for_status_reads():
    from threading import Event
    entered,release=Event(),Event()
    def load(_):
        entered.set()
        assert release.wait(3)
        return build_shapley_intrinsic_contract(_result())
    coordinator=ShapleyIntrinsicBackgroundCoordinator(load,
        intrinsic_input_fingerprint_resolver=lambda _:'input',forecast_coordinate_resolver=lambda _:'forecast')
    ctx=context();reader=hosted(coordinator)
    try:
        coordinator.request(ctx)
        assert entered.wait(2)
        assert reader(ctx)['intrinsic']['status']=='building'
        release.set()
        record=coordinator.wait_for_terminal(ctx)
        assert record.completion_summary.estimate_count==1
        coordinator._intrinsic_input_fingerprint_resolver=forbidden
        assert reader(ctx)['intrinsic']['status']=='full'
    finally:
        release.set()
        coordinator._executor.shutdown(wait=True)


def test_explicit_model_read_reuses_completed_record_without_unguarded_key_resolution():
    contract=build_shapley_intrinsic_contract(_result())
    loader=NS(restore_compatible=lambda _:contract)
    coordinator=ShapleyIntrinsicBackgroundCoordinator(loader,
        intrinsic_input_fingerprint_resolver=lambda _:'input',forecast_coordinate_resolver=lambda _:'forecast')
    ctx=context()
    try:
        record=coordinator.restore_compatible(ctx)
        loader.pin_build_context=forbidden
        coordinator._intrinsic_input_fingerprint_resolver=forbidden
        assert coordinator.current(ctx) is record
        assert coordinator.current(context(state='other')) is None
    finally:
        coordinator._executor.shutdown(wait=True)


def test_expired_model_restore_resolves_inputs_only_after_memory_admission():
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    gate=HeavyWorkCoordinator()
    calls=[]
    def resolve(_):
        calls.append(gate.snapshot().active_kind)
        return 'input'
    def restore(_):
        assert gate.snapshot().active_kind=='intrinsic_restore'
        return build_shapley_intrinsic_contract(_result())
    coordinator=ShapleyIntrinsicBackgroundCoordinator(NS(restore_compatible=restore),
        intrinsic_input_fingerprint_resolver=resolve,forecast_coordinate_resolver=lambda _:'forecast',
        heavy_work_coordinator=gate)
    ctx=context()
    try:
        record=coordinator.restore_compatible_staged(ctx)
        assert coordinator.release_completed_contract(ctx,record.contract)
        handle=ref(record.contract)
        del record
        gc.collect()
        assert handle() is None
        calls.clear()
        restored=coordinator.current(ctx)
        assert restored.contract is not None
        assert calls and set(calls)=={'intrinsic_restore'}
    finally:
        coordinator._executor.shutdown(wait=True)
