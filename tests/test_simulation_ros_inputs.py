"""Current competitive outcomes must consume governed forward participation."""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from fsffl.forecast.in_season_orchestration import canonical_week_window
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.persistence.runtime_cache import encode_forecast_evidence, decode_forecast_evidence
from fsffl.product.scenario_cache import _forecast_fingerprint, build_scenario_dependency_plan, ScenarioComputationStage
from fsffl.product.season_comparison_runtime import SeasonComparisonService
from fsffl.product.simulation_forecasts import require_forward_simulation_evidence
from fsffl.product.webapp import _build_default_simulation
from fsffl.state.models import WeeklyAvailabilityStatus, PlayerWeekAvailability
from fsffl.team_utility import build_bye_aware_weekly_team_scoring_panel
from tests.test_bye_aware_weekly_simulation import _state, _forecast, PROV
from tests.test_product_forecast_refresh import _evidence
from tests.test_season_comparison import Store
from fsffl.forecast.season_comparison import SEASON_COMPARISON_VERSION


def market(state):
    from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult
    from fsffl.value.cardinal_authority import FSFFLCardinalValueScore
    return CurrentMarketValueRuntimeResult(league_state_id=state.state_id,
        estimates=(), successful_source_ids=(), failed_sources=(), errors_by_source_id={},
        roster_player_count=len(state.players), valued_roster_player_count=0, market_context_id='test',
        fsffl_cardinal_values=tuple(FSFFLCardinalValueScore(asset_id=p.player_id,
            asset_kind='player', score=1000, as_of=state.as_of, market_context_id='test') for p in state.players))


def fixture():
    start, _ = canonical_week_window(2026, 5)
    _, end = canonical_week_window(2026, 18)
    state = _state().model_copy(update={'completed_through_week': 4, 'as_of': start})
    from fsffl.state.models import ProviderRef
    state = state.model_copy(update={'league': state.league.model_copy(update={
        'provider_refs': (ProviderRef(provider='sleeper', external_id='123'),)})})
    cutoff = start + timedelta(minutes=1)
    rows = tuple(_forecast(pid, mean, 0).model_copy(update={
        'horizon': ForecastHorizon.REST_OF_SEASON, 'period_start': start, 'period_end': end,
        'as_of': cutoff, 'source': 'fsffl:participation-zero-ros:verified_unavailable' if mean == 0 else 'governed-ros',
    }) for pid, mean in (('starter', 0), ('bench', 70), ('opp', 140)))
    evidence = replace(_evidence(), evidence_basis="preseason_baseline", simulation_forward_forecasts=rows,
        simulation_evaluation_as_of=cutoff, simulation_source_state_id=state.state_id,
        simulation_basis='current_rest_of_season')
    return state, evidence


def panel(state, evidence, weeks):
    return build_bye_aware_weekly_team_scoring_panel(state, evidence.simulation_forward_forecasts,
        team_ids=('a', 'b'), weeks=weeks, as_of=evidence.simulation_evaluation_as_of,
        horizon=ForecastHorizon.REST_OF_SEASON)


def test_zero_ros_starter_is_replaced_and_remaining_total_is_conserved():
    state, evidence = fixture()
    frozen = encode_forecast_evidence(evidence)
    results = panel(state, evidence, tuple(range(5, 19)))
    team = [r for r in results if r.team_id == 'a']
    assert sum(r.mean_points for r in team) == pytest.approx(70)
    assert next(r.mean_points for r in team if r.week == 6) == pytest.approx(70 / 13)
    assert next(r.mean_points for r in team if r.week == 10) == 0  # bench bye; zero-ROS starter
    assert next(r.stddev_points for r in team if r.week == 10) == 0
    assert encode_forecast_evidence(evidence) == frozen
    assert evidence.league_scored_forecasts == _evidence().league_scored_forecasts
    with pytest.raises(ValueError, match='completed weeks'):
        panel(state, evidence, (4,))


def test_exact_week_unavailability_preserves_total_and_uses_other_starters():
    state, evidence = fixture()
    state = state.model_copy(update={'player_week_availability': (
        PlayerWeekAvailability(player_id='bench', week=6, status=WeeklyAvailabilityStatus.UNAVAILABLE, provenance=PROV),)})
    results = [r for r in panel(state, evidence, tuple(range(5, 19))) if r.team_id == 'a']
    assert next(r.mean_points for r in results if r.week == 6) == 0
    assert sum(r.mean_points for r in results) == pytest.approx(70)


def test_weekly_starter_selection_uses_per_game_ros_instead_of_unequal_totals():
    state, evidence = fixture()
    # Starter has no remaining bye, while bench has one. Lower ROS total can
    # therefore have the higher active-game projection and should start W6.
    state = state.model_copy(update={'completed_through_week': 5})
    rows = tuple(row.model_copy(update={'distribution': ForecastDistribution(
        mean={'starter': 130, 'bench': 125, 'opp': 140}[row.player_id], stddev=0)})
        for row in evidence.simulation_forward_forecasts)
    evidence = replace(evidence, simulation_forward_forecasts=rows)
    result = next(r for r in panel(state, evidence, (6,)) if r.team_id == 'a')
    assert result.mean_points == pytest.approx(125 / 12)


def test_production_loader_uses_native_ros_and_rejects_missing_or_mixed_coverage():
    state, evidence = fixture()
    result = _build_default_simulation(state, evidence, simulation_count=100)
    assert result.scenario_preparation is not None
    lineup = next(v.optimized_lineup for v in result.team_views if v.team_id == 'a')
    assert [a.player_id for a in lineup.assignments] == ['bench']
    assert result.scenario_preparation.forward_weekly_scoring
    old = replace(evidence, simulation_forward_forecasts=None)
    with pytest.raises(ValueError, match='preseason projections cannot confirm'):
        _build_default_simulation(state, old, simulation_count=100)
    with pytest.raises(ValueError, match='coverage missing'):
        _build_default_simulation(state, replace(evidence,
            simulation_forward_forecasts=evidence.simulation_forward_forecasts[:1]), simulation_count=100)
    with pytest.raises(ValueError, match='forward coordinates'):
        _build_default_simulation(state, replace(evidence, simulation_forward_forecasts=tuple(
            row.model_copy(update={'horizon': ForecastHorizon.SEASON}) for row in evidence.simulation_forward_forecasts)), simulation_count=100)


def test_forward_identity_fences_scenario_cache_and_baseline():
    state, evidence = fixture()
    baseline = _build_default_simulation(state, evidence, simulation_count=100)
    require_forward_simulation_evidence(state, evidence, baseline)
    revised = replace(evidence, simulation_forward_forecasts=tuple(row.model_copy(update={
        'distribution': ForecastDistribution(mean=30 if row.player_id == 'starter' else row.distribution.mean, stddev=0)
    }) for row in evidence.simulation_forward_forecasts))
    assert _forecast_fingerprint(evidence) != _forecast_fingerprint(revised)
    with pytest.raises(ValueError, match='same ROS evidence'):
        require_forward_simulation_evidence(state, revised, baseline)
    with pytest.raises(ValueError, match='baseline State'):
        require_forward_simulation_evidence(state.model_copy(update={'as_of': state.as_of + timedelta(seconds=1)}), evidence)
    plan = build_scenario_dependency_plan(state, state, revised, baseline, stage=ScenarioComputationStage.CONFIRMATION)
    assert not plan.forecast_compatible
    restored = decode_forecast_evidence(encode_forecast_evidence(evidence))
    assert _forecast_fingerprint(restored) == _forecast_fingerprint(evidence)
    assert restored.league_scored_forecasts == evidence.league_scored_forecasts


def test_legacy_full_season_fingerprint_stays_exact_and_no_forward_is_invented():
    evidence = replace(_evidence(), evidence_basis="preseason_baseline")
    payload = encode_forecast_evidence(evidence)
    assert not any(key.startswith('simulation_') for key in payload)
    restored = decode_forecast_evidence(payload)
    assert restored.simulation_forward_forecasts is None
    assert encode_forecast_evidence(restored) == payload


def test_existing_comparison_producer_is_reused_without_reader_acquisition():
    state, evidence = fixture()
    calls = []
    def builder(s, **kwargs):
        calls.append(s.state_id)
        return {'version': SEASON_COMPARISON_VERSION, 'league_state_id': s.state_id,
            'season': s.league.season, 'completed_through_week': s.completed_through_week,
            'as_of': evidence.simulation_evaluation_as_of.isoformat(), 'players': {},
            'evidence_basis': 'current_rest_of_season',
            'forward_forecasts': [row.model_dump(mode='json') for row in evidence.simulation_forward_forecasts]}
    store = Store()
    service = SeasonComparisonService(persistence_store=store, builder=builder)
    context = SimpleNamespace(user_id='u', league_state=state)
    with pytest.raises(ValueError, match='Refresh Intelligence'):
        service.simulation_evidence(context, _evidence())
    assert calls == []
    service.prepare(context)
    for _ in range(3):
        loaded = service.simulation_evidence(context, _evidence())
        assert loaded.simulation_forward_forecasts == evidence.simulation_forward_forecasts
        assert loaded.league_scored_forecasts == _evidence().league_scored_forecasts
    assert len(calls) == store.writes == 1


def test_comparison_prepare_reuses_existing_admission_and_cutoff_is_explicit():
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    from fsffl.analytics.models import AnalyticsContext
    state, evidence = fixture()
    coordinator = HeavyWorkCoordinator()
    service = SeasonComparisonService(heavy_work=coordinator,
        builder=lambda s, **kwargs: {'version': SEASON_COMPARISON_VERSION,
            'league_state_id': s.state_id, 'season': 2026, 'players': {}})
    with coordinator.claim(kind='forecast', key='owned-refresh'):
        service.prepare(SimpleNamespace(league_state=state), already_admitted=True)
    result = _build_default_simulation(state, evidence, simulation_count=100)
    context = result.league_view.context
    assert context.as_of == state.as_of
    assert context.league_state_id == state.state_id
    assert context.forecast_evaluation_as_of == evidence.simulation_evaluation_as_of
    for invalid in (state.as_of - timedelta(seconds=1), context.generated_at + timedelta(seconds=1), state.as_of.replace(tzinfo=None)):
        with pytest.raises(ValueError, match='cutoff'):
            AnalyticsContext.model_validate({**context.model_dump(), 'forecast_evaluation_as_of': invalid})


def test_native_ros_preserves_completed_standings_and_has_no_actual_points_in_forward_panel():
    from tests.test_live_simulation_runtime import _state as live_state, _forecasts
    state = live_state().model_copy(update={'completed_through_week': 2})
    state = state.model_copy(update={'matchups': tuple(m.model_copy(update={
        'team_a_points': 120 if m.week == 1 else 90,
        'team_b_points': 100 if m.week == 1 else 110,
    }) if m.week <= 2 else m for m in state.matchups)})
    start = canonical_week_window(2026, 3)[0]
    end = canonical_week_window(2026, 18)[1]
    rows = tuple(row.model_copy(update={'horizon': ForecastHorizon.REST_OF_SEASON,
        'period_start': start, 'period_end': end,
        'distribution': ForecastDistribution(mean=160, stddev=0)}) for row in _forecasts())
    evidence = replace(_evidence(), simulation_forward_forecasts=rows,
        simulation_source_state_id=state.state_id, simulation_evaluation_as_of=state.as_of,
        simulation_basis='current_rest_of_season')
    result = _build_default_simulation(state, evidence, simulation_count=100)
    for row in result.simulation_result.outcomes:
        assert row.expected_wins == pytest.approx(1 + row.expected_remaining_wins)
    assert {row.week for row in result.scenario_preparation.forward_weekly_scoring} == {3, 4}


def test_refresh_prepares_forward_evidence_before_simulation_and_publishes_it(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.webapp import create_app
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    from time import monotonic, sleep
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    state, prepared = fixture()
    store = PrivateBetaRuntimeStore()
    steps = []
    def prepare(context, evidence):
        assert context.league_state.state_id == state.state_id
        assert evidence.simulation_forward_forecasts is None
        steps.append('forward')
        return prepared
    def simulate(s, evidence):
        assert steps == ['forward']
        assert evidence.simulation_forward_forecasts == prepared.simulation_forward_forecasts
        steps.append('simulation')
        return _build_default_simulation(s, evidence, simulation_count=100)
    app = create_app(runtime_store=store, state_loader=lambda _: state,
        forecast_loader=lambda _: _evidence(), simulation_forecast_preparer=prepare,
        simulation_loader=simulate, value_loader=lambda _: market(state),
        heavy_work_coordinator=HeavyWorkCoordinator())
    client = TestClient(app)
    assert client.post('/api/connect/sleeper', json={'league_external_id': '123'}).status_code == 200
    assert client.post('/api/select-team', json={'team_id': 'a'}).status_code == 200
    deadline = monotonic() + 5
    while monotonic() < deadline:
        job = client.get('/api/intelligence/jobs/current').json()
        if job['status'] in ('completed', 'failed', 'interrupted'):
            break
        sleep(.01)
    assert job['status'] == 'completed', job
    assert steps == ['forward', 'simulation']
    assert store.get('local-beta-user').forecast_evidence.simulation_forward_forecasts is not None


def test_trade_screen_and_confirmation_consume_same_forward_roster_evidence():
    from fsffl.product.runtime import UserRuntimeContext
    from fsffl.product.trade_analysis_runtime import build_private_beta_trade_analysis
    from fsffl.product.market_discovery_runtime import evaluate_candidate_path
    from fsffl.product.trade_simulation_runtime import build_post_trade_simulation_comparison
    from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
    from fsffl.state.models import PlayerAsset
    state, evidence = fixture()
    baseline = _build_default_simulation(state, evidence, simulation_count=50_000)
    runtime = UserRuntimeContext(user_id='u', league_state=state, selected_team_id='a',
        forecast_evidence=evidence, simulation_analytics=baseline, value_evidence=market(state))
    proposal = BilateralTradeProposal(proposal_id='forward-participation', as_of=state.as_of,
        side_a=TradeLeg(team_id='a', sends=(PlayerAsset(player_id='starter'),)),
        side_b=TradeLeg(team_id='b', sends=(PlayerAsset(player_id='opp'),)))
    analysis = build_private_beta_trade_analysis(runtime, proposal, focal_team_id='a')
    assert analysis['position_strength'] is not None
    row = {'counterparty_team_id': 'b', 'send': [{'asset_ref': 'player:starter'}], 'receive': [{'asset_ref': 'player:opp'}]}
    screen = evaluate_candidate_path(runtime, row)
    assert screen['preliminary_bilateral_screen']['focal']['starter_points_delta'] == 70
    assert screen['preliminary_bilateral_screen']['counterparty']['starter_points_delta'] == -140
    # Default progressive factory runs the existing confirmation protocol;
    # this small deterministic loader keeps a test-sized sample without providers.
    def loader(s, e):
        return _build_default_simulation(s, e, simulation_count=50_000)
    comparison = build_post_trade_simulation_comparison(runtime, proposal,
        focal_team_id='a', simulation_loader=loader)
    assert comparison['forecast_input']['horizon'] == 'rest_of_season'
    assert comparison['scenario_computation']['authoritative']


def test_standalone_comparison_cannot_invert_owned_refresh_lock_order():
    from contextlib import contextmanager
    from threading import Event, Thread
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator
    state, _ = fixture()
    waiting = Event()
    coordinator = HeavyWorkCoordinator()
    class ObservedAdmission:
        @contextmanager
        def claim(self, **kwargs):
            waiting.set()
            with coordinator.claim(**kwargs):
                yield
    builds = []
    service = SeasonComparisonService(heavy_work=ObservedAdmission(),
        builder=lambda s, **kwargs: (builds.append(s.state_id) or {
            'version': SEASON_COMPARISON_VERSION, 'league_state_id': s.state_id,
            'season': 2026, 'players': {}}))
    context = SimpleNamespace(league_state=state)
    errors = []
    def standalone():
        try:
            service.prepare(context)
        except Exception as exc:
            errors.append(exc)
    def owned():
        with coordinator.claim(kind='forecast', key='owned-refresh'):
            thread = Thread(target=standalone, daemon=True)
            thread.start()
            if not waiting.wait(2):
                errors.append(TimeoutError('standalone did not request admission'))
                return
            service.prepare(context, already_admitted=True)
        thread.join(2)
        if thread.is_alive():
            errors.append(TimeoutError('standalone did not finish'))
    owner = Thread(target=owned, daemon=True)
    owner.start()
    owner.join(4)
    assert not owner.is_alive() and not errors
    assert len(builds) == 1


def test_total_ros_source_failure_is_not_confirmed_as_current_evidence():
    state, evidence = fixture()
    prior = replace(evidence, simulation_basis='preseason_remaining_prior')
    with pytest.raises(ValueError, match='preseason prior cannot confirm'):
        require_forward_simulation_evidence(state, prior)


def test_current_position_depth_reuses_typed_outlook_and_preserves_participation_labels():
    state, evidence = fixture()
    start = canonical_week_window(2026, 1)[0]
    outlook = [row.model_copy(update={'horizon': ForecastHorizon.SEASON, 'period_start': start,
        'distribution': ForecastDistribution(mean=row.distribution.mean + 40, stddev=0)}).model_dump(mode='json')
        for row in evidence.simulation_forward_forecasts]
    service = SeasonComparisonService(builder=lambda s, **kwargs: {
        'version': SEASON_COMPARISON_VERSION, 'league_state_id': s.state_id, 'season': 2026,
        'completed_through_week': 4, 'evidence_basis': 'current_rest_of_season',
        'players': {'starter': {'participation_basis': 'verified_unavailable', 'low_confidence': False}},
        'season_outlook': outlook, 'forward_forecasts': [r.model_dump(mode='json') for r in evidence.simulation_forward_forecasts]})
    assert service.current_position_depth(state) is None
    service.prepare(SimpleNamespace(league_state=state))
    result = service.current_position_depth(state)
    starter = next(row for row in result.players if row.player_id == 'starter')
    assert starter.season_outlook_points == 40  # earned points stay in Current outlook
    assert starter.participation_basis == 'verified_unavailable'
    assert starter.ros_as_of == evidence.simulation_forward_forecasts[0].as_of.isoformat().replace('+00:00', 'Z')


def test_preserved_season_displays_do_not_disappear_when_simulation_switches_to_ros():
    state, evidence = fixture()
    season = tuple(_forecast(pid, points, 20) for pid, points in (('starter', 400), ('bench', 200), ('opp', 300)))
    evidence = replace(evidence, league_scored_forecasts=season)
    result = _build_default_simulation(state, evidence, simulation_count=100)
    players = {p.player_id: p for team in result.team_views for p in team.players}
    assert players['starter'].season_fantasy_points_projection == 400
    assert players['bench'].season_fantasy_points_projection == 200
    assert [a.player_id for a in result.team_views[0].optimized_lineup.assignments] == ['bench']
    revised_display = replace(evidence, league_scored_forecasts=(season[0].model_copy(update={
        'distribution': ForecastDistribution(mean=390, stddev=20)}), *season[1:]))
    assert _forecast_fingerprint(revised_display) != _forecast_fingerprint(evidence)


def test_current_outlook_rejects_another_cohort_even_when_state_matches():
    state, evidence = fixture()
    service = SeasonComparisonService(builder=lambda s, **kwargs: {
        'version': SEASON_COMPARISON_VERSION, 'league_state_id': s.state_id, 'season': 2026,
        'completed_through_week': 4, 'evidence_basis': 'current_rest_of_season',
        'as_of': (evidence.simulation_evaluation_as_of + timedelta(seconds=1)).isoformat(),
        'players': {}, 'season_outlook': [],
        'forward_forecasts': [r.model_dump(mode='json') for r in evidence.simulation_forward_forecasts]})
    service.prepare(SimpleNamespace(league_state=state))
    result = service.current_position_depth(state, evidence)
    assert result.status == 'unavailable'
    assert 'published Simulation cohort' in result.reason
