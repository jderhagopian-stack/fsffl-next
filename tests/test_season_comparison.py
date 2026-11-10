from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from threading import Event, Thread

import pytest

from tests.test_in_season_hosted_orchestration import _state, _preseason_forecast, NOW
from fsffl.forecast.season_comparison import build_season_comparison, SEASON_COMPARISON_VERSION
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.forecast.in_season_runtime import InSeasonForecastRuntimeResult
from fsffl.providers.sleeper_weekly_stats import SleeperNflState, SleeperWeeklyStatLine
from fsffl.product.season_comparison_runtime import SeasonComparisonService

PID = 'sleeper:player:1'

class Stats:
    def fetch_nfl_state(self):
        return SleeperNflState(season=2026, week=3, season_type='regular', captured_at=NOW)

    def fetch_week(self, *, season, week):
        assert season == 2026 and week in (1, 2)
        return (SleeperWeeklyStatLine(player_id=PID, season=season, week=week,
            stats={'rush_yd': 100, 'rush_td': 1, 'rec': 4, 'rec_yd': 20}, captured_at=NOW),)


def ros_runtime(state):
    start = __import__('fsffl.forecast.in_season_orchestration', fromlist=['canonical_week_window']).canonical_week_window(2026, 3)[0]
    row = _preseason_forecast().model_copy(update={
        'horizon': ForecastHorizon.REST_OF_SEASON, 'period_start': start,
        'distribution': ForecastDistribution(mean=160, stddev=20), 'as_of': NOW,
        'source': 'fsffl:in-season-league-scored',
    })
    return SimpleNamespace(source_observations=(row,), evaluation_as_of=NOW,
        fantasy_point_forecasts=(row,), partial_fantasy_point_forecasts=(),
        model_copy=lambda **kwargs: SimpleNamespace(**{**vars(ros_runtime(state)), **kwargs['update']}))


def test_real_actual_scoring_plus_ros_retains_original_snapshot_and_sum(monkeypatch):
    state = _state().model_copy(update={'completed_through_week': 2})
    import fsffl.forecast.season_comparison as module
    monkeypatch.setattr(module, 'build_in_season_forecasts', lambda *a, **k: ros_runtime(state))
    monkeypatch.setattr(module, 'complete_comparison_ros', lambda state, result, **k: result)
    packet = build_season_comparison(state, preseason_forecasts=(_preseason_forecast(),),
        stats_source=Stats(), clock=lambda: NOW)
    row = packet['players'][PID]
    assert row['actual_points'] == 40  # 2 * (100*.1 + 6 + 4*.5 + 20*.1)
    assert row['weekly_actuals'] == [{'week': 1, 'points': 20}, {'week': 2, 'points': 40}]
    assert row['ros_points'] == 160
    assert row['outlook_points'] == 200
    assert row['preseason_points'] == 170
    assert row['change_from_preseason'] == 30
    assert row['preseason_as_of'] == _preseason_forecast().as_of.isoformat()
    assert row['status'] == 'ready'


def test_stale_completed_week_is_not_backdated_into_new_comparison():
    with pytest.raises(ValueError, match='exact State completed-week boundary'):
        build_season_comparison(_state().model_copy(update={'completed_through_week': 1}),
            preseason_forecasts=(_preseason_forecast(),), stats_source=Stats(), clock=lambda: NOW)


def test_unsigned_prior_fallback_retains_actuals_and_no_ros(monkeypatch):
    state = _state().model_copy(update={'completed_through_week': 2})
    state = state.model_copy(update={'players': (state.players[0].model_copy(update={'nfl_team': None}),)})
    import fsffl.forecast.season_comparison as module
    def fail(*a, **k): raise ValueError('provider unavailable')
    monkeypatch.setattr(module, 'build_in_season_forecasts', fail)
    row = build_season_comparison(state, preseason_forecasts=(_preseason_forecast(),),
        stats_source=Stats(), clock=lambda: NOW)['players'][PID]
    assert row['actual_points'] == 40
    assert row['ros_points'] == 0
    assert row['outlook_points'] == 40
    assert row['low_confidence']


class Store:
    def __init__(self): self.rows = {}; self.writes = 0; self.reads = 0
    def get_reusable_artifact(self, key):
        self.reads += 1; return self.rows.get(key)
    def put_artifact(self, record):
        self.writes += 1; self.rows[record.key] = record


def packet(state):
    return {'version': SEASON_COMPARISON_VERSION, 'league_state_id': state.state_id,
            'season': 2026, 'as_of': NOW.isoformat(), 'players': {PID: {'status': 'ready', 'outlook_points': 200}}}


def context(state):
    return SimpleNamespace(league_state=state, user_id='u', publication_generation_id='generation-1')


def test_reader_never_builds_and_other_players_reuse_same_state_artifact():
    state = _state(); store = Store(); builds = []
    service = SeasonComparisonService(persistence_store=store,
        builder=lambda s, **k: (builds.append(s.state_id) or packet(s)))
    assert service.player(context(state), PID)['status'] == 'needs_refresh'
    assert not builds
    service.prepare(context(state)); service.prepare(context(state))
    for _ in range(10): assert service.player(context(state), PID)['outlook_points'] == 200
    assert len(builds) == store.writes == 1
    restarted = SeasonComparisonService(persistence_store=store, builder=lambda *a, **k: pytest.fail('read fitted'))
    assert restarted.player(context(state), PID)['publication_generation_id'] == 'generation-1'


def test_switch_during_acquisition_cannot_persist_for_new_state_and_read_is_nonblocking():
    state = _state(); store = Store(); entered, release = Event(), Event(); owned = [True]
    def build(s, **k):
        entered.set(); assert release.wait(3); return packet(s)
    service = SeasonComparisonService(persistence_store=store, builder=build,
        ownership_validator=lambda c: owned[0])
    thread = Thread(target=service.prepare, args=(context(state),)); thread.start()
    assert entered.wait(3)
    assert service.player(context(state), PID)['status'] == 'preparing'
    owned[0] = False; release.set(); thread.join(3)
    assert not thread.is_alive() and not store.writes


def test_bounded_cache_and_exact_state_restore():
    store = Store(); service = SeasonComparisonService(persistence_store=store, builder=lambda s, **k: packet(s))
    states = [_state().model_copy(update={'as_of': NOW + timedelta(seconds=i)}) for i in range(4)]
    for state in states: service.prepare(context(state))
    assert len(service._cache) == 2
    assert service.player(context(states[0]), PID)['league_state_id'] == states[0].state_id


def test_original_archived_projection_is_read_without_current_fumbles_reconstruction():
    from tests.test_preseason_forecast_baseline import _state as state_factory, _raw_qb_runtime, _Store
    from fsffl.forecast.preseason_baseline import baseline_from_runtime, preseason_scope_id
    from fsffl.persistence.runtime_cache import preseason_forecast_baseline_artifact
    from fsffl.product.forecast_resilience import make_preseason_comparison_loader
    state = state_factory(); raw = _raw_qb_runtime()
    baseline = baseline_from_runtime(state, raw, source_artifact_id='12')
    record = preseason_forecast_baseline_artifact(league_season_scope_id=preseason_scope_id(state), baseline=baseline)
    archive_points = raw.raw_ensemble[0].model_copy(update={
        'metric': __import__('fsffl.forecast.models', fromlist=['ForecastMetric']).ForecastMetric.FANTASY_POINTS, 'distribution': ForecastDistribution(mean=311.7, stddev=30)})
    class ArchiveStore(_Store):
        def get_forecast_archive(self, **kwargs):
            assert kwargs == {'artifact_id': 12, 'league_id': state.league.league_id, 'season': 2026}
            return {'raw_forecasts': [r.model_dump(mode='json') for r in raw.raw_ensemble],
                    'league_scored_forecasts': [archive_points.model_dump(mode='json')],
                    'rules': state.league.rules.model_dump(mode='json')}
    result = make_preseason_comparison_loader(ArchiveStore(record))(state)
    assert result['basis'] == 'original_published_preseason'
    assert result['forecasts'][0].distribution.mean == 311.7
    assert result['as_of'] == baseline.evaluation_as_of.isoformat()


def test_missing_preseason_fumbles_cannot_be_invented_for_historical_comparison():
    from tests.test_preseason_forecast_baseline import _state_scoring_fumbles_lost, _raw_qb_runtime, _Store
    from fsffl.forecast.preseason_baseline import baseline_from_runtime, preseason_scope_id
    from fsffl.persistence.runtime_cache import preseason_forecast_baseline_artifact
    from fsffl.product.forecast_resilience import make_preseason_comparison_loader
    state = _state_scoring_fumbles_lost()
    baseline = baseline_from_runtime(state, _raw_qb_runtime())
    record = preseason_forecast_baseline_artifact(league_season_scope_id=preseason_scope_id(state), baseline=baseline)
    assert make_preseason_comparison_loader(_Store(record))(state)['forecasts'] == ()


def test_single_source_ros_requires_first_party_fumbles_completion(monkeypatch):
    from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
    from fsffl.forecast.season_comparison import complete_comparison_ros
    from fsffl.forecast.models import ForecastMetric
    from fsffl.state.models import ScoringRule
    state = _state().model_copy(update={'completed_through_week': 2})
    state = state.model_copy(update={'league': state.league.model_copy(update={
        'rules': state.league.rules.model_copy(update={'scoring': state.league.rules.scoring + (ScoringRule(stat='fum_lost', points=-2),)})})})
    template = ros_runtime(state).fantasy_point_forecasts[0]
    values = {ForecastMetric.RUSH_YARDS: 100, ForecastMetric.RUSH_TD: 1,
              ForecastMetric.RECEPTIONS: 4, ForecastMetric.REC_YARDS: 20, ForecastMetric.REC_TD: 0}
    rows = tuple(template.model_copy(update={'metric': metric, 'source': 'one-provider',
        'distribution': ForecastDistribution(mean=value, stddev=0)}) for metric, value in values.items())
    runtime = InSeasonForecastRuntimeResult(horizon=ForecastHorizon.REST_OF_SEASON,
        source_observations=rows, raw_ensemble=(), fantasy_point_forecasts=(),
        coverage=LiveEnsembleCoverage(independent_source_ids=('one-provider',),
            active_source_ids=('one-provider',), excluded_aggregate_source_ids=(),
            observation_count=len(rows), minimum_independent_sources=2),
        successful_source_ids=('one-provider',), failed_sources=(), persistence_failures=(),
        evaluation_as_of=NOW, ensemble_ready=False)
    import fsffl.forecast.season_comparison as module
    calls = []
    lost = template.model_copy(update={'metric': ForecastMetric.FUMBLES_LOST,
        'distribution': ForecastDistribution(mean=2, stddev=0)})
    def supplement(*a, **k): calls.append(k['eligible_player_ids']); return (lost,)
    monkeypatch.setattr(module, 'build_current_ros_fumbles_lost_supplement_observations', supplement)
    output = complete_comparison_ros(state, runtime, stats_source=Stats(), completed=2, as_of=NOW)
    assert calls == [{PID}]
    assert output.fantasy_point_forecasts[0].distribution.mean == 16
    assert 'single-source' in output.fantasy_point_forecasts[0].source
    assert output.coverage.minimum_independent_sources == 2
    monkeypatch.setattr(module, 'build_current_ros_fumbles_lost_supplement_observations', lambda *a, **k: ())
    assert not complete_comparison_ros(state, runtime, stats_source=Stats(), completed=2, as_of=NOW).fantasy_point_forecasts


def test_finished_season_has_actuals_only_and_never_acquires_ros(monkeypatch):
    state = _state().model_copy(update={'completed_through_week': 18})
    class FinishedStats(Stats):
        def fetch_nfl_state(self):
            return SleeperNflState(season=2026, week=19, season_type='post', captured_at=NOW)
        def fetch_week(self, *, season, week):
            return (SleeperWeeklyStatLine(player_id=PID, season=season, week=week,
                stats={'rush_yd': 100}, captured_at=NOW),)
    import fsffl.forecast.season_comparison as module
    monkeypatch.setattr(module, 'build_in_season_forecasts', lambda *a, **k: pytest.fail('finished season fetched ROS'))
    row = build_season_comparison(state, preseason_forecasts=(_preseason_forecast(),),
        stats_source=FinishedStats(), clock=lambda: NOW)['players'][PID]
    assert row['actual_points'] == row['outlook_points'] == 180
    assert row['ros_points'] == 0
    assert row['weekly_actuals'][-1] == {'week': 18, 'points': 180}


def test_ros_evaluation_cutoff_follows_actual_acquisition_without_changing_source_provenance(monkeypatch):
    import fsffl.forecast.season_comparison as module
    state = _state().model_copy(update={'completed_through_week': 2})
    actual_capture = NOW + timedelta(seconds=3)
    provider_capture = NOW - timedelta(hours=1)
    class LaterStats(Stats):
        def fetch_week(self, **kwargs):
            return tuple(replace(line, captured_at=actual_capture)
                         for line in super().fetch_week(**kwargs))
    cutoffs = []
    def runtime(league_state, **kwargs):
        cutoff = kwargs['clock']()
        cutoffs.append(cutoff)
        row = ros_runtime(state).fantasy_point_forecasts[0].model_copy(update={
            'as_of': cutoff,
            'provenance': _preseason_forecast().provenance.model_copy(update={
                'retrieved_at': provider_capture, 'effective_at': provider_capture,
            }),
        })
        return SimpleNamespace(source_observations=(row,), evaluation_as_of=cutoff,
                               fantasy_point_forecasts=(row,), partial_fantasy_point_forecasts=())
    monkeypatch.setattr(module, 'build_in_season_forecasts', runtime)
    monkeypatch.setattr(module, 'complete_comparison_ros', lambda state, result, **kwargs: result)
    packet = build_season_comparison(state, preseason_forecasts=(_preseason_forecast(),),
        stats_source=LaterStats(), clock=lambda: NOW)
    row = packet['players'][PID]
    assert cutoffs == [actual_capture]
    assert row['status'] == 'ready'
    assert row['actual_points'] == 40 and row['outlook_points'] == 200
    assert row['preseason_as_of'] == _preseason_forecast().as_of.isoformat()
    assert packet['as_of'] == actual_capture.isoformat()


def participation_result(state, *, projected=False, complete=False):
    row = ros_runtime(state).fantasy_point_forecasts[0]
    runtime = SimpleNamespace(source_observations=(row,) if projected else (),
                              fantasy_point_forecasts=(row,) if complete else ())
    return SimpleNamespace(current_runtime=runtime, completed_through_week=2,
                           forward_forecasts=(row,) if complete else ())


def ir_state():
    state = _state().model_copy(update={'completed_through_week': 2})
    team = state.team_states[0]
    from fsffl.state.models import RosterEntry, RosterSlot
    roster = (RosterEntry(player_id=PID, slot=RosterSlot.IR),)
    return state.model_copy(update={'team_states': (team.model_copy(update={'roster': roster}),)})


@pytest.mark.parametrize('projected,complete,expected', [(False,False,True),(True,False,False),(True,True,False)])
def test_ir_exception_matches_intrinsic_projection_veto(projected,complete,expected):
    from fsffl.forecast.season_comparison import apply_participation_exceptions
    from fsffl.forecast.participation import IR_NO_PROJECTION_POLICY_APPROVED_AT
    state = ir_state(); result = participation_result(state, projected=projected, complete=complete)
    cutoff = IR_NO_PROJECTION_POLICY_APPROVED_AT + timedelta(seconds=1)
    explanation = apply_participation_exceptions(state, result, as_of=cutoff)
    assert (PID in explanation) is expected
    if expected:
        assert explanation[PID]['participation_basis'] == 'ir_no_projection'
        assert explanation[PID]['participation_assumption'] is True
        assert result.forward_forecasts[0].distribution.mean == 0
        assert result.forward_forecasts[0].provenance.source == 'fsffl:exact-state-ir-no-projection'


def test_ir_exception_is_not_applied_before_acceptance_or_to_ordinary_bench():
    from fsffl.forecast.season_comparison import apply_participation_exceptions
    from fsffl.forecast.participation import IR_NO_PROJECTION_POLICY_APPROVED_AT
    for state, cutoff in [(ir_state(),IR_NO_PROJECTION_POLICY_APPROVED_AT-timedelta(seconds=1)),
                          (_state(),IR_NO_PROJECTION_POLICY_APPROVED_AT+timedelta(seconds=1))]:
        result = participation_result(state)
        assert not apply_participation_exceptions(state,result,as_of=cutoff)
        assert not result.forward_forecasts


def test_verified_season_unavailability_keeps_actuals_and_original_preseason(monkeypatch):
    import fsffl.forecast.participation as policy
    import fsffl.forecast.season_comparison as module
    state = _state().model_copy(update={'completed_through_week':2})
    receipt = policy.StatusBasedZeroRosEvidence(PID,'out_for_season','https://example.test/official',
        'recorded-official-v1',NOW,True,season=2026)
    monkeypatch.setattr(policy,'recorded_status_based_zero_ros_evidence',lambda *args,**kwargs:{PID:receipt})
    monkeypatch.setattr(module,'build_in_season_forecasts',lambda *args,**kwargs: (_ for _ in ()).throw(ValueError('no source')))
    row = build_season_comparison(state,preseason_forecasts=(_preseason_forecast(),),
        stats_source=Stats(),clock=lambda:NOW)['players'][PID]
    assert row['status']=='ready' and row['actual_points']==40
    assert row['ros_points']==0 and row['outlook_points']==40 and row['preseason_points']==170
    assert row['participation_basis']=='verified_unavailable'
    assert row['participation_assumption'] is False
    assert row['participation_source']==receipt.source
    assert row['participation_observed_at']==NOW.isoformat()
    complete = participation_result(state, projected=True, complete=True)
    assert not module.apply_participation_exceptions(state,complete,as_of=NOW)
    assert complete.forward_forecasts[0].distribution.mean==160


def test_comparison_and_intrinsic_share_identical_eligibility_functions():
    import fsffl.forecast.participation as policy
    import fsffl.product.p0_live_candidate_runtime as intrinsic
    for name in ['recorded_status_based_zero_ros_evidence','recorded_ytd_only_year_one_evidence',
                 'recorded_ir_no_projection_year_one_evidence','_unsigned_ytd_override']:
        assert getattr(intrinsic,name) is getattr(policy,name)
