from datetime import timedelta
from types import SimpleNamespace as NS

import pytest

from fsffl.forecast.participation import SparseProductionEvidence, SPARSE_PRODUCTION_POLICY_APPROVED_AT
from fsffl.forecast.season_comparison import apply_participation_exceptions
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine
from fsffl.state.models import Position, PlayerStatus
from tests.test_in_season_hosted_orchestration import _state, _preseason_forecast

NOW = SPARSE_PRODUCTION_POLICY_APPROVED_AT + timedelta(seconds=1)
PID = 'sleeper:player:1'


def state_for(position='WR', status='active', completed=5):
    state = _state()
    return state.model_copy(update={
        'as_of': NOW, 'completed_through_week': completed,
        'players': (state.players[0].model_copy(update={'position':Position(position),'nfl_team':'BUF'}),),
        'player_states': (state.player_states[0].model_copy(update={
            'as_of':NOW,'status':PlayerStatus(status),'nfl_team':'BUF'}),),
    })


def measured(state, stats=None, *, omit=(), empty=()):
    evidence = SparseProductionEvidence(state)
    for week in range(1, (state.completed_through_week or 0)+1):
        if week in omit: continue
        rows = () if week in empty else (SleeperWeeklyStatLine(
            PID,2026,week,stats if week==1 and stats is not None else {},NOW),)
        evidence.add_week(week, rows)
    return evidence


def receipts(evidence, *, rows=(), ready=True, now=NOW):
    return evidence.receipts(as_of=now,available_projection_rows=rows,source_ready=ready)


@pytest.mark.parametrize('position',['QB','RB','WR','TE'])
@pytest.mark.parametrize('status',['active','inactive','practice_squad'])
def test_universal_rule_uses_stats_not_name_position_or_fantasy_slot(position,status):
    evidence=measured(state_for(position,status),{'pass_att':1,'rush_att':1,'rec_tgt':3,'rec':2,'rec_yd':50})
    row=receipts(evidence)[PID]
    assert row.status=='low_confidence_ytd_only_no_additional_production_assumed'
    assert '4w-5opp-50yd-0td' in row.source_version


@pytest.mark.parametrize('stats',[{'rush_att':6},{'rec':6},{'rec_tgt':6},{'pass_att':6},
    {'rush_yd':51},{'rec_yd':-51},{'pass_td':1},{'rush_td':1},{'rec_td':1},
    {'rec_yd':float('nan')},{'rush_att':'bad'}])
def test_meaningful_or_invalid_production_does_not_become_zero(stats):
    assert not receipts(measured(state_for(),stats))


@pytest.mark.parametrize('status',['injured','pup','suspended','unknown','retired'])
def test_injury_or_unknown_status_is_not_evidence_of_development(status):
    assert not receipts(measured(state_for(status=status)))


def test_no_projection_is_not_a_provider_outage_or_early_season_rule():
    evidence=measured(state_for())
    assert not receipts(evidence,ready=False)
    assert not receipts(evidence,rows=(NS(player_id=PID),)) # Even partial source rows veto.
    assert not receipts(evidence,now=SPARSE_PRODUCTION_POLICY_APPROVED_AT-timedelta(seconds=1))
    assert not receipts(measured(state_for(completed=3)))
    assert not receipts(measured(state_for(),omit=(2,)))
    assert not receipts(measured(state_for(),empty=(2,)))
    evidence.add_week(1,(SleeperWeeklyStatLine(PID,2026,1,{},NOW),))
    assert not receipts(evidence) # Duplicate acquisition cannot conceal an incomplete cohort.


def test_missing_player_rows_in_successful_full_cohorts_are_labeled_assumption():
    evidence=SparseProductionEvidence(state_for())
    for week in range(1,6):
        evidence.add_week(week,(SleeperWeeklyStatLine('other',2026,week,{'rec':10},NOW),))
    assert PID in receipts(evidence)
    assert evidence.totals=={} # Does not retain other players' raw evidence.
    evidence.captured_at=NOW+timedelta(seconds=1)
    assert not receipts(evidence)


def test_comparison_uses_shared_assumption_and_preserves_projection_precedence():
    state=state_for()
    row=_preseason_forecast().model_copy(update={'player_id':PID})
    result=NS(current_runtime=NS(source_observations=(),fantasy_point_forecasts=(),
        successful_source_ids=('fixture',)),forward_forecasts=(),completed_through_week=5)
    labels=apply_participation_exceptions(state,result,as_of=NOW,sparse_production=measured(state))
    assert labels[PID]['participation_basis']=='sparse_production'
    assert labels[PID]['participation_assumption'] is True
    assert result.forward_forecasts[0].distribution.mean==0
    result.current_runtime.source_observations=(row,)
    result.forward_forecasts=(row,)
    assert not apply_participation_exceptions(state,result,as_of=NOW,sparse_production=measured(state))
    assert result.forward_forecasts==(row,)


def test_real_intrinsic_year_one_fallback_preserves_actuals_and_future_scoring(monkeypatch):
    from tests.test_nfl_status_evidence import _run_current_ros_policy_case
    result,pid,_=_run_current_ros_policy_case(monkeypatch,unsigned=False,provider_case='absent',sparse_case=True)
    assert not result.failures
    assert result.year_one_league[pid].distribution.mean==pytest.approx(1.)
    assert 'sparse-production-no-ros-v1' in result.year_one_evidence_modes[pid]
    assert len(result.future.contract.forecasts)==2 # Real unchanged Y2/Y3 scorer still runs.


def test_end_to_end_comparison_retains_actuals_and_original_preseason(monkeypatch):
    import fsffl.forecast.season_comparison as module
    from fsffl.providers.sleeper_weekly_stats import SleeperNflState
    state=state_for()
    def week_rows(*,season,week):
        return (SleeperWeeklyStatLine(PID,season,week,
            {'rec':1,'rec_tgt':2,'rec_yd':10} if week==1 else {},NOW),)
    source=NS(fetch_nfl_state=lambda:SleeperNflState(2026,6,'regular',NOW),fetch_week=week_rows)
    other=_preseason_forecast().model_copy(update={'player_id':'other'})
    runtime=NS(source_observations=(other,),fantasy_point_forecasts=(),
        partial_fantasy_point_forecasts=(),successful_source_ids=('fixture',),evaluation_as_of=NOW)
    monkeypatch.setattr(module,'build_in_season_forecasts',lambda *a,**k:runtime)
    def complete(state,runtime,**kwargs):
        # Existing first-party completion may read the same acquired week again.
        kwargs['stats_source'].fetch_week(season=2026,week=1)
        return runtime
    monkeypatch.setattr(module,'complete_comparison_ros',complete)
    row=module.build_season_comparison(state,preseason_forecasts=(_preseason_forecast(),),
        stats_source=source,clock=lambda:NOW)['players'][PID]
    assert row['status']=='ready' and row['participation_basis']=='sparse_production'
    assert row['actual_points']==pytest.approx(1.5)
    assert row['outlook_points']==pytest.approx(1.5)
    assert row['ros_points']==0 and row['preseason_points']==170
    assert row['low_confidence']


def test_policy_enters_dependency_identity_only_after_approval():
    from fsffl.forecast.participation import sparse_production_policy_version
    assert sparse_production_policy_version(SPARSE_PRODUCTION_POLICY_APPROVED_AT-timedelta(microseconds=1)) is None
    assert sparse_production_policy_version(NOW)
    with pytest.raises(ValueError,match='timezone'):
        sparse_production_policy_version(NOW.replace(tzinfo=None))


@pytest.mark.parametrize('bad_season,bad_week',[(2025,1),(2026,6)])
def test_incorrect_weekly_identity_never_supports_assumption(bad_season,bad_week):
    evidence=measured(state_for(),omit=(1,))
    evidence.add_week(1,(SleeperWeeklyStatLine(PID,bad_season,bad_week,{},NOW),))
    assert not receipts(evidence)


def test_four_week_minimum_and_no_unknown_status_or_unsigned_reclassification():
    assert PID in receipts(measured(state_for(completed=4)))
    state=state_for()
    state=state.model_copy(update={'players':(state.players[0].model_copy(update={'nfl_team':None}),)})
    assert not receipts(measured(state))
