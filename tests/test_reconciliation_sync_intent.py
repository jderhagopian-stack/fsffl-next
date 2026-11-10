from datetime import timedelta
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

from fsffl.product.reconciliation_intent import ReconciliationSyncIntent
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.webapp import create_app
from tests.test_resource_boundary_closure import _state


def test_pending_sync_upgrades_one_pass_and_many_explicit_joins_do_not_repeat_it():
    intent = ReconciliationSyncIntent()
    assert intent.begin_pass() is False
    for _ in range(100): assert intent.request_sync()
    assert intent.finish_pass() is True
    assert intent.begin_pass() is True
    for _ in range(100): assert intent.request_sync()
    assert intent.finish_pass() is False
    assert intent.request_sync() is False  # Closing intent must not silently accept a tap.


def terminal(coordinator):
    until = monotonic()+8
    while monotonic()<until:
        job=coordinator.current('local-beta-user')
        if job is not None and job.status.value not in {'queued','running'}:
            return job
        sleep(.01)
    raise AssertionError('reconciliation did not terminate')


def make_app(monkeypatch, *, block_sync=False):
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    old = _state('sync-intent').model_copy(update={'completed_through_week':8})
    fresh = old.model_copy(update={'completed_through_week':9,'as_of':old.as_of+timedelta(hours=1)})
    store = PrivateBetaRuntimeStore()
    store.set_league_state('local-beta-user', old)
    store.select_team('local-beta-user', old.teams[0].team_id)
    entered, release = Event(), Event()
    loads, forecasts = [], []
    def load(external):
        loads.append(external)
        if block_sync:
            entered.set(); assert release.wait(5)
        return fresh
    def forecast(state):
        forecasts.append(state.completed_through_week)
        if not block_sync and len(forecasts)==1:
            entered.set(); assert release.wait(5)
        observation = NS(as_of=state.as_of,player_id='fixture-player')
        return NS(raw_forecasts=(observation,),league_scored_forecasts=(observation,),
            successful_source_ids=('fixture-source',),failed_sources=(),uncertainty_ready=True,
            evidence_basis='fixture-governed',runtime_result=NS(simulation_authority_blockers=(),
                partial_fantasy_point_forecasts=(),simulation_material_partial_player_ids=(),
                fumbles_lost_non_material_partial_player_ids=(),fumbles_lost_material_partial_player_ids=(),
                family_coverage=(),evaluation_as_of=state.as_of))
    app = create_app(runtime_store=store,state_loader=load,forecast_loader=forecast,
        simulation_loader=lambda state,evidence:NS(league_view=NS(context=NS(league_state_id=state.state_id)),
            simulation_result=NS(simulation_count=50000)),
        value_loader=lambda state:NS(league_state_id=state.state_id,estimates=(NS(as_of=state.as_of),),
            fsffl_cardinal_values=(),pick_variant_market_values=(),successful_source_ids=('fixture-value',),
            coverage=1.,cardinal_player_coverage=1.),
        product_capability_reconciler=lambda context:{'status':'full'})
    return app,store,old,fresh,entered,release,loads,forecasts


def test_manual_post_joining_automatic_repair_syncs_new_week_in_same_job(monkeypatch):
    app,store,old,fresh,entered,release,loads,forecasts=make_app(monkeypatch)
    with TestClient(app) as client:
        auto=app.state.start_intelligence_reconciliation('local-beta-user')
        assert entered.wait(2)
        try:
            replies=[client.post('/api/intelligence/jobs') for _ in range(3)]
            assert all(r.status_code==200 and r.json()['job_id']==auto['job_id'] for r in replies)
            assert not loads
        finally: release.set()
        job=terminal(app.state.intelligence_jobs)
        assert job.status.value=='completed', job
        assert len(loads)==1 and forecasts==[8]  # This no-fumbles fixture permits season Forecast reuse.
        current=store.get('local-beta-user')
        assert current.league_state.state_id==fresh.state_id
        assert current.simulation_analytics.league_view.context.league_state_id==fresh.state_id
        assert current.value_evidence.league_state_id==fresh.state_id
        assert sum(t.phase.value=='refreshing_state' for t in job.phase_timings)==1


def test_repeated_manual_posts_coalesce_into_one_state_sync(monkeypatch):
    app,store,old,fresh,entered,release,loads,forecasts=make_app(monkeypatch,block_sync=True)
    with TestClient(app) as client:
        first=client.post('/api/intelligence/jobs')
        assert entered.wait(2)
        try:
            for _ in range(3):
                response=client.post('/api/intelligence/jobs')
                assert response.status_code==200 and response.json()['job_id']==first.json()['job_id']
        finally: release.set()
        job=terminal(app.state.intelligence_jobs)
        assert job.status.value=='completed',job
        assert len(loads)==1 and forecasts==[9]
        assert store.get('local-beta-user').league_state.state_id==fresh.state_id


def test_lifecycle_switch_cancels_pending_old_owner_sync(monkeypatch):
    app,store,old,fresh,entered,release,loads,forecasts=make_app(monkeypatch)
    with TestClient(app) as client:
        app.state.start_intelligence_reconciliation('local-beta-user')
        assert entered.wait(2)
        try:
            assert client.post('/api/intelligence/jobs').status_code==200
            store.select_team('local-beta-user',old.teams[1].team_id)
        finally: release.set()
        job=terminal(app.state.intelligence_jobs)
        assert job.status.value=='interrupted',job
        assert not loads
        assert store.get('local-beta-user').selected_team_id==old.teams[1].team_id
        assert store.get('local-beta-user').league_state.state_id==old.state_id


def test_manual_sync_before_worker_begins_is_consumed_in_first_pass():
    intent=ReconciliationSyncIntent()
    assert intent.request_sync()
    assert intent.begin_pass() is True
    assert intent.finish_pass() is False


def test_manual_request_during_terminal_handoff_is_busy_then_can_sync(monkeypatch):
    app,store,old,fresh,entered,release,loads,forecasts=make_app(monkeypatch)
    closed,finish=Event(),Event()
    original=ReconciliationSyncIntent.finish_pass
    def pause_after_closing(intent):
        result=original(intent)
        if not result:
            closed.set(); assert finish.wait(5)
        return result
    monkeypatch.setattr(ReconciliationSyncIntent,'finish_pass',pause_after_closing)
    with TestClient(app) as client:
        app.state.start_intelligence_reconciliation('local-beta-user')
        assert entered.wait(2)
        release.set()
        assert closed.wait(3)
        try:
            response=client.post('/api/intelligence/jobs')
            assert response.status_code==503 and response.headers['Retry-After']=='1'
            assert not loads
        finally: finish.set()
        assert terminal(app.state.intelligence_jobs).status.value=='completed'
        response=client.post('/api/intelligence/jobs')
        assert response.status_code==200
        assert terminal(app.state.intelligence_jobs).status.value=='completed'
        assert len(loads)==1 and store.get('local-beta-user').league_state.state_id==fresh.state_id
