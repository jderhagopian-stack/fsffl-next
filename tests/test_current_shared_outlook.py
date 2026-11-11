"""Real Current slot composition and card arithmetic share Forecast preparation."""
from datetime import timedelta
from types import SimpleNamespace as NS

import pytest

from fsffl.forecast import season_comparison as forecast
from fsffl.forecast.models import ForecastObservation, ForecastDistribution, ForecastHorizon, ForecastMetric
from fsffl.forecast.participation import SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT
from fsffl.product.current_position_depth import build_governed_current_position_depth
from fsffl.providers.sleeper_weekly_stats import SleeperNflState, SleeperWeeklyStatLine
from fsffl.state.models import (
    League, LeagueRules, LeagueState, LineupRequirement, Player, PlayerState,
    Position, Provenance, RosterEntry, Team, TeamState, ScoringRule,
)

NOW=SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT+timedelta(seconds=1)


def fixture(monkeypatch,*,complete_fumbles=True):
    ids=('a1','a2','a3','b1','b2','b3','sparse','ir')
    state=LeagueState(league=League(league_id='shared-current',name='Fixture',season=2026,
        rules=LeagueRules(team_count=2,roster_size=5,lineup=(LineupRequirement(slot='WR',count=3),),
            scoring=(ScoringRule(stat='rec',points=.5),ScoringRule(stat='rec_yd',points=.1),
                ScoringRule(stat='rec_td',points=6),ScoringRule(stat='fum_lost',points=-2)))),
        as_of=NOW,completed_through_week=5,
        teams=tuple(Team(team_id=t,league_id='shared-current',display_name=t) for t in ('a','b')),
        team_states=(TeamState(team_id='a',roster=tuple(RosterEntry(player_id=p,slot='WR') for p in ids[:3])),
            TeamState(team_id='b',roster=tuple(RosterEntry(player_id=p,slot='IR' if p=='ir' else 'BENCH') for p in ids[3:]))),
        players=tuple(Player(player_id=p,full_name=p,position='WR',nfl_team='BUF') for p in ids),
        player_states=tuple(PlayerState(player_id=p,as_of=NOW,nfl_team='BUF',status='injured' if p=='sparse' else 'active',
            provenance=Provenance(source='fixture',retrieved_at=NOW,effective_at=NOW)) for p in ids))
    start=forecast.canonical_week_window(2026,6)[0]
    end=forecast.canonical_week_window(2026,18)[1]
    def row(pid,metric,mean,source='razzball'):
        return ForecastObservation(player_id=pid,position='WR',metric=metric,horizon=ForecastHorizon.REST_OF_SEASON,
            period_start=start,period_end=end,as_of=NOW,distribution=ForecastDistribution(mean=mean,stddev=0),
            source=source,model_version='fixture',provenance=Provenance(source=source,retrieved_at=NOW,effective_at=NOW))
    ready=tuple(row(p,ForecastMetric.FANTASY_POINTS,100,'fsffl:in-season-league-scored') for p in ids[:6] if p!='a3')
    source_rows=tuple(row('a3',metric,value) for metric,value in [
        (ForecastMetric.RECEPTIONS,3),(ForecastMetric.REC_YARDS,30),(ForecastMetric.REC_TD,0)])
    runtime=NS(evaluation_as_of=NOW,source_observations=source_rows,fantasy_point_forecasts=ready,
        partial_fantasy_point_forecasts=(),successful_source_ids=('cbs','razzball'))
    runtime.model_copy=lambda *,update:NS(**{**vars(runtime),**update})
    monkeypatch.setattr(forecast,'build_in_season_forecasts',lambda *a,**k:runtime)
    monkeypatch.setattr(forecast,'fill_current_ros_fumbles_lost_gaps',lambda *a,**k:(ready,()))
    # Inject the accepted fumbles predictor's output, retaining real strict scoring/composition.
    monkeypatch.setattr(forecast,'build_current_ros_fumbles_lost_supplement_observations',
        lambda *a,**k:(row('a3',ForecastMetric.FUMBLES_LOST,.2,'fsffl:first-party-fumbles'),) if complete_fumbles else ())
    class Stats:
        def __init__(self): self.calls=[]
        def fetch_nfl_state(self): return SleeperNflState(2026,6,'regular',NOW)
        def fetch_week(self,*,season,week):
            self.calls.append(week)
            return tuple(SleeperWeeklyStatLine(p,season,week,
                {'rec':1,'rec_yd':10,'rec_tgt':2} if p=='a3' and week==1 else {'gp':1},NOW) for p in ids)
    return state,Stats


def test_current_wr_fills_third_slot_from_same_single_source_plus_fumbles_as_card(monkeypatch):
    state,Stats=fixture(monkeypatch)
    stats=Stats()
    current=build_governed_current_position_depth(state,preseason_season_forecasts=(),stats_source=stats,clock=lambda:NOW)
    card=forecast.build_season_comparison(state,preseason_forecasts=(),stats_source=Stats(),clock=lambda:NOW)
    assert current.status=='ready' and current.slots[0].status=='ready'
    assert stats.calls==[1,2,3,4,5] # One actual acquisition loop, not per player.
    assert all(row.starter_count==3 and row.league_rank is not None for row in current.strengths)
    third=next(row for row in current.players if row.player_id=='a3')
    assert third.season_outlook_points==pytest.approx(5.6) # 1.5 earned + 1.5+3-.4 remaining.
    assert third.season_outlook_points==card['players']['a3']['outlook_points']
    assert third.ros_basis=='fsffl:single-source-ros-with-first-party-fumbles'
    assert third.low_confidence and third.season_outlook_failure is None
    assert next(row for row in current.strengths if row.team_id=='a').expected_points==pytest.approx(205.6)
    for pid,basis in [('sparse','sparse_production'),('ir','ir_no_projection')]:
        evidence=next(row for row in current.players if row.player_id==pid)
        assert evidence.season_outlook_points==card['players'][pid]['outlook_points']==0
        assert evidence.participation_basis==basis and evidence.participation_assumption
        assert evidence.low_confidence and evidence.participation_reason


def test_missing_fumbles_still_blocks_wr_rank_without_inventing_zero(monkeypatch):
    state,Stats=fixture(monkeypatch,complete_fumbles=False)
    current=build_governed_current_position_depth(state,preseason_season_forecasts=(),stats_source=Stats(),clock=lambda:NOW)
    assert current.slots[0].status=='unavailable'
    assert current.slots[0].incomplete_team_ids==('a',)
    assert all(row.league_rank is None and row.expected_points is None for row in current.strengths)
    third=next(row for row in current.players if row.player_id=='a3')
    assert third.season_outlook_points is None and third.season_outlook_failure


def test_real_team_views_api_exposes_completed_wr_column_and_input_labels(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    state,Stats=fixture(monkeypatch)
    store=PrivateBetaRuntimeStore()
    store.set_league_state('local-beta-user',state)
    app=create_app(runtime_store=store,current_position_depth_provider=lambda current, _evidence:
        build_governed_current_position_depth(current,preseason_season_forecasts=(),
            stats_source=Stats(),clock=lambda:NOW))
    with TestClient(app) as client:
        response=client.get('/api/league/team-views')
        assert response.status_code==200
        current=response.json()['current_position_depth']
        assert current['model_version'].startswith('league-atlas-current-position-depth-v3:')
        assert current['league_state_id']==state.state_id
        assert current['slots'][0]['slot']=='WR' and current['slots'][0]['status']=='ready'
        assert len(current['strengths'])==2
        assert all(r['league_rank'] is not None and r['starter_count']==3 for r in current['strengths'])
        sparse=next(r for r in current['players'] if r['player_id']=='sparse')
        assert sparse['participation_assumption'] and sparse['low_confidence']


def test_write_only_history_consumer_keeps_live_ros_authority(monkeypatch):
    state,Stats=fixture(monkeypatch)
    writer=NS() # Optional writer does not have to implement the history reader protocol.
    current=build_governed_current_position_depth(state,preseason_season_forecasts=(),
        stats_source=Stats(),clock=lambda:NOW,history_writer=writer)
    assert current.status=='ready'
    sparse=next(r for r in current.players if r.player_id=='sparse')
    assert sparse.participation_source_version.startswith('sparse-production-no-ros-v2')
    assert sparse.participation_observed_at and sparse.ros_as_of and sparse.ros_model_version
