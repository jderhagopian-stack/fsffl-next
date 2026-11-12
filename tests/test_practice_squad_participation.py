"""General role evidence, not player-name exceptions or low-usage thresholds."""
from dataclasses import asdict, replace
from datetime import timedelta
from types import SimpleNamespace as NS
import hashlib
import json

import pytest
from fsffl.forecast.participation import (
    PRACTICE_SQUAD_POLICY_APPROVED_AT, PRACTICE_SQUAD_POLICY_VERSION,
    recorded_ytd_only_year_one_evidence, practice_squad_no_projection_receipt,
)
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric
from fsffl.forecast import season_comparison as comparison
from fsffl.providers.nfl_status_evidence import (
    NflRoleReceipt, NFL_ROLE_RECEIPTS, canonical_practice_squad_role_receipts,
    current_catalog_role_receipts, acquire_official_reserve_role_receipts,
)
from fsffl.state.models import Player, PlayerState, PlayerStatus, Position, Provenance, RosterEntry
from tests.test_in_season_hosted_orchestration import _state, _preseason_forecast

NOW = PRACTICE_SQUAD_POLICY_APPROVED_AT + timedelta(minutes=10)
PID = 'sleeper:player:13268'  # public identity supports the existing accepted P0 future fixture


def state(position='WR', pid=PID, status='practice_squad'):
    base = _state()
    prov = Provenance(source='synthetic-current-catalog',retrieved_at=NOW,effective_at=NOW)
    return base.model_copy(update={'as_of':NOW,'completed_through_week':5,
        'players':(Player(player_id=pid,full_name='Synthetic PS player',position=position,nfl_team='BUF'),
            Player(player_id='control',full_name='Control',position='WR',nfl_team='BUF')),
        'player_states':(PlayerState(player_id=pid,as_of=NOW,nfl_team='BUF',status=status,age_years=23,provenance=prov),
            PlayerState(player_id='control',as_of=NOW,nfl_team='BUF',age_years=23,provenance=prov)),
        'team_states':(base.team_states[0].model_copy(update={'roster':(RosterEntry(player_id=pid,slot='BENCH'),)}),base.team_states[1])})


def row(pid='control', mean=50):
    return _preseason_forecast().model_copy(update={'player_id':pid,'position':Position.WR,
        'horizon':ForecastHorizon.REST_OF_SEASON,'period_start':comparison.canonical_week_window(2026,6)[0],
        'period_end':comparison.canonical_week_window(2026,18)[1], 'as_of':NOW,
        'distribution':ForecastDistribution(mean=mean,stddev=0),'source':'synthetic-provider'})


@pytest.mark.parametrize('position',['QB','RB','WR','TE'])
def test_any_canonical_ps_identity_is_eligible_without_a_named_admission(position):
    snapshot=state(position,pid='new-arbitrary-'+position)
    pid=snapshot.players[0].player_id
    receipts=recorded_ytd_only_year_one_evidence(snapshot,as_of=NOW)
    assert receipts[pid].source_version.startswith(PRACTICE_SQUAD_POLICY_VERSION)
    assert practice_squad_no_projection_receipt(pid,receipts=receipts,
        available_projection_rows=(row(),),source_ready=True) is receipts[pid]
    assert not recorded_ytd_only_year_one_evidence(snapshot,as_of=PRACTICE_SQUAD_POLICY_APPROVED_AT-timedelta(seconds=1))
    assert not recorded_ytd_only_year_one_evidence(snapshot,as_of=NOW+timedelta(hours=6))
    taxi=snapshot.model_copy(update={'player_states':tuple(p.model_copy(update={'status':PlayerStatus.ACTIVE}) for p in snapshot.player_states),
        'team_states':(snapshot.team_states[0].model_copy(update={'roster':(RosterEntry(player_id=pid,slot='TAXI'),)}),snapshot.team_states[1])})
    assert not recorded_ytd_only_year_one_evidence(taxi,as_of=NOW)


@pytest.mark.parametrize('rows,healthy',[((),True),((row(),),False),((row(PID),),True)])
def test_outages_and_even_partial_player_rows_veto_ps_zero(rows,healthy):
    receipts=recorded_ytd_only_year_one_evidence(state(),as_of=NOW)
    assert practice_squad_no_projection_receipt(PID,receipts=receipts,
        available_projection_rows=rows,source_ready=healthy) is None


def test_catalog_ps_is_explicit_position_and_team_bound_and_role_hashes_are_compatible():
    snapshot=state()
    roles=current_catalog_role_receipts(snapshot,as_of=NOW,captured_at=NOW,
        catalog={'13268':{'team':'BUF','status':'Practice Squad','position':Position.WR}})
    assert roles[PID].status=='practice_squad' and roles[PID].nfl_team=='BUF'
    assert not current_catalog_role_receipts(snapshot,as_of=NOW,captured_at=NOW,
        catalog={'13268':{'team':'BUF','status':'Practice Squad','position':'QB'}})
    for fact in NFL_ROLE_RECEIPTS:
        if fact.nfl_team is None:
            legacy=asdict(fact);legacy.pop('nfl_team')
            assert fact.fingerprint==hashlib.sha256(json.dumps(legacy,sort_keys=True,default=str).encode()).hexdigest()


@pytest.mark.parametrize('code,expected',[('DEV','practice_squad'),('PS','practice_squad'),('ACT','not_practice_squad')])
def test_official_renewal_is_bounded_and_fresh_promotion_revokes_old_ps(monkeypatch,code,expected):
    import fsffl.providers.nfl_status_evidence as provider
    snapshot=state(status='active')
    fact=NflRoleReceipt(PID,'WR',2026,'practice_squad','https://www.nfl.com/teams/buffalo-bills/roster',NOW-timedelta(minutes=1),nfl_team='BUF')
    monkeypatch.setattr(provider,'NFL_ROLE_RECEIPTS',(fact,))
    reads=[]
    def fetch(url):
        reads.append(url)
        return f'<table><tr><td>Synthetic PS player</td><td>WR</td><td>{code}</td></tr></table>',NOW
    roles=acquire_official_reserve_role_receipts(snapshot,evaluation_cutoff=NOW,fetcher=fetch)
    assert reads==[fact.source_url] and roles[PID].status==expected
    receipts=recorded_ytd_only_year_one_evidence(snapshot,as_of=NOW,verified_roles=roles)
    assert (PID in receipts)==(expected=='practice_squad')
    assert acquire_official_reserve_role_receipts(snapshot,evaluation_cutoff=NOW-timedelta(seconds=1),fetcher=fetch)=={}


def test_current_card_retains_meaningful_actuals_and_preserved_preseason(monkeypatch):
    from fsffl.providers.sleeper_weekly_stats import SleeperNflState,SleeperWeeklyStatLine
    snapshot=state()
    class Stats:
        def fetch_nfl_state(self):return SleeperNflState(season=2026,week=6,season_type='regular',captured_at=NOW)
        def fetch_week(self,*,season,week):
            return (SleeperWeeklyStatLine(PID,2026,week,{'rec':10,'rec_yd':100},NOW),) if week==1 else ()
    control=row()
    fake=NS(source_observations=(control,),evaluation_as_of=NOW,fantasy_point_forecasts=(control,),
        partial_fantasy_point_forecasts=(),successful_source_ids=('synthetic-provider',))
    monkeypatch.setattr(comparison,'build_in_season_forecasts',lambda *a,**k:fake)
    monkeypatch.setattr(comparison,'complete_comparison_ros',lambda state,result,**k:result)
    preseason=_preseason_forecast().model_copy(update={'player_id':PID,'position':Position.WR})
    packet=comparison.build_season_comparison(snapshot,preseason_forecasts=(preseason,),stats_source=Stats(),clock=lambda:NOW)
    player=packet['players'][PID]
    assert player['actual_points']==15 and player['outlook_points']==15
    assert player['ros_points']==0 and player['preseason_points']==170
    assert player['low_confidence'] and player['participation_basis']=='practice_squad_no_projection'
    assert player['participation_assumption']
    # An existing provider projection wins, even if roster evidence still says PS.
    positive=row(PID,mean=80)
    fake.source_observations=(control,positive);fake.fantasy_point_forecasts=(control,positive)
    packet=comparison.build_season_comparison(snapshot,preseason_forecasts=(preseason,),stats_source=Stats(),clock=lambda:NOW)
    assert packet['players'][PID]['ros_points']==80 and packet['players'][PID]['outlook_points']==95


def test_real_p0_year_one_retains_earned_production_and_future_models(monkeypatch):
    from fsffl.product import p0_live_candidate_runtime as runtime
    from fsffl.providers.sleeper_weekly_stats import SleeperNflState,SleeperWeeklyStatLine
    from tests.test_nfl_status_evidence import _approved_ytd_state
    snapshot=state()
    # Match the existing accepted standard/league scorer's complete fixture.
    league=_approved_ytd_state().league
    snapshot=snapshot.model_copy(update={'league':league,
        'teams':tuple(t.model_copy(update={'league_id':league.league_id}) for t in snapshot.teams)})
    capture=NOW
    stats=NS(fetch_nfl_state=lambda:SleeperNflState(season=2026,week=6,season_type='regular',captured_at=capture),
        fetch_week=lambda **kw: (SleeperWeeklyStatLine(PID,2026,1,{'rec':10,'rec_yd':100},capture),) if kw['week']==1 else (),
        fetch_season=lambda **kw:())
    catalog=NS(captured_at=capture,payload={'players':{'13268':{'years_exp':0}}})
    monkeypatch.setattr(runtime.SleeperSnapshotNormalizer,'normalize_snapshot',lambda *a,**kw:snapshot)
    raw=(row().model_copy(update={'metric':ForecastMetric.REC_YARDS}),)
    ros=NS(evaluation_as_of=capture,source_observations=raw,raw_ensemble=(),
        successful_source_ids=('synthetic-provider',),failed_sources=(),
        fantasy_point_forecasts=(),partial_fantasy_point_forecasts=(),
        coverage=NS(minimum_independent_sources=2),ensemble_ready=True,ensemble_unavailability_reason=None)
    ros.model_copy=lambda *,update:NS(**(vars(ros)|update))
    monkeypatch.setattr(runtime,'build_in_season_forecasts',lambda *a,**kw:ros)
    monkeypatch.setattr('fsffl.forecast.in_season_orchestration.build_current_ros_fumbles_lost_supplement_observations',lambda *a,**kw:())
    result=runtime.build_live_p0_rostered_candidate_forecasts(snapshot,stats_source=stats,
        sleeper_source=NS(fetch_latest=lambda **kw:catalog),evaluation_as_of=capture,
        projection_history_as_of=capture,retain_ros_runtime_details=False)
    assert not result.failures
    assert result.year_one_league[PID].distribution.mean==15
    assert PRACTICE_SQUAD_POLICY_VERSION in result.year_one_league[PID].model_version
    assert result.year_one_league[PID].distribution.stddev==0
    assert result.future is not None
    future=[f for f in result.future.contract.forecasts if f.player_id==PID]
    assert len(future)==2 and any(f.central_expectation>0 for f in future)
    assert all(PRACTICE_SQUAD_POLICY_VERSION not in f.model_version for f in future)
