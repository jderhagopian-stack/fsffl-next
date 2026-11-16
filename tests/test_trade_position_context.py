import pytest
from fsffl.state.models import Player,Position,RosterEntry,RosterSlot,LineupRequirement,PlayerAsset
from fsffl.forecast.models import ForecastHorizon
from fsffl.trade_decision.models import TradeLeg
from fsffl.product.trade_analysis_runtime import _position_comparison_and_context
from tests.test_dynasty_position_room import _state
from tests.test_bye_aware_weekly_simulation import _forecast


def fixture(superflex=False,send='a5'):
    state=_state()
    players=tuple(Player(player_id=pid,full_name=pid,position=Position.QB if pid=='qb' else Position.WR)
        for pid in ('a1','a2','a3','a4','a5','a6','a7','b1','qb'))
    team=state.team_states[0].model_copy(update={'roster':state.team_states[0].roster+(
        RosterEntry(player_id='a5',slot=RosterSlot.BENCH),RosterEntry(player_id='a6',slot=RosterSlot.BENCH),
        RosterEntry(player_id='a7',slot=RosterSlot.BENCH),RosterEntry(player_id='qb',slot=RosterSlot.QB))})
    lineup=(LineupRequirement(slot=RosterSlot.WR,count=1),LineupRequirement(slot=RosterSlot.FLEX,count=1),
        LineupRequirement(slot=RosterSlot.SUPERFLEX if superflex else RosterSlot.QB,count=1))
    state=state.model_copy(update={'players':players,'team_states':(team,state.team_states[1]),
        'league':state.league.model_copy(update={'rules':state.league.rules.model_copy(update={'lineup':lineup})})})
    # Native fixture forecasts are issued before the State; no providers involved.
    forecasts=tuple(_forecast(pid,points,0).model_copy(update={'position':next(p.position for p in players if p.player_id==pid)})
        for pid,points in [('a1',100),('a2',80),('a3',120),('a4',110),('a5',60),('a7',0),('qb',90)])
    after=state.model_copy(update={'team_states':(team.model_copy(update={'roster':tuple(r for r in team.roster if r.player_id!=send)}),state.team_states[1])})
    leg=TradeLeg(team_id='alpha',sends=(PlayerAsset(player_id=send),))
    return state,after,forecasts,leg


@pytest.mark.parametrize('superflex',[False,True])
def test_actual_optimizer_distinguishes_depth_from_wr_in_flex(superflex):
    for send,role in [('a5','outgoing_bench_ids'),('a2','outgoing_starter_ids')]:
        before,after,forecasts,leg=fixture(superflex,send)
        original=before.model_dump_json()
        comparison,result=_position_comparison_and_context(before,after,forecasts,team_id='alpha',leg=leg,
            horizon=ForecastHorizon.SEASON,forecast_as_of=before.as_of)
        wr=result['positions'][0]
        assert wr[role]==(send,)
        assert 'a3' not in wr['before_forecasted_bench_ids']  # IR
        assert 'a4' not in wr['before_forecasted_bench_ids']  # taxi
        assert 'a6' not in wr['before_forecasted_bench_ids']  # no forecast
        assert result['horizon']=='season' and result['basis']=='optimized_horizon_lineup'
        assert not result['surplus_confirmed']
        assert before.model_dump_json()==original
        if send=='a5':assert result['expected_points_delta']==0
        else:
            assert result['expected_points_delta']==-20
            assert result['entering_lineup_ids']==('a5',)


def test_missing_or_unavailable_player_role_is_not_bench_surplus():
    for send,key in [('a3','outgoing_unavailable_ids'),('a6','outgoing_missing_forecast_ids')]:
        before,after,forecasts,leg=fixture(send=send)
        _,r=_position_comparison_and_context(before,after,forecasts,team_id='alpha',leg=leg,
            horizon=ForecastHorizon.SEASON,forecast_as_of=before.as_of)
        assert r['positions'][0][key]==(send,)
        assert not r['positions'][0]['outgoing_bench_ids']


def test_unavailable_lineup_stays_unavailable():
    before,after,forecasts,leg=fixture()
    assert _position_comparison_and_context(before,after,(),team_id='alpha',leg=leg)==(None,None)


def test_received_pick_identity_and_cut_player_roles_are_retained():
    from fsffl.state.models import PickAsset
    before,after,forecasts,leg=fixture()
    team=after.team_states[0]
    after=after.model_copy(update={'team_states':(team.model_copy(update={'roster':tuple(r for r in team.roster if r.player_id!='a7')}),after.team_states[1])})
    _,r=_position_comparison_and_context(before,after,forecasts,team_id='alpha',leg=leg,
        received_assets=(PickAsset(pick_id='future'),),horizon=ForecastHorizon.SEASON,forecast_as_of=before.as_of)
    assert r['received_pick_ids']==('future',)
    assert r['positions'][0]['removed_nontrade_player_ids']==('a7',)


def test_position_totals_and_exact_slot_replacements_reconcile():
    before,after,forecasts,leg=fixture(send='a2')
    comparison,context=_position_comparison_and_context(before,after,forecasts,team_id='alpha',leg=leg,
        horizon=ForecastHorizon.SEASON,forecast_as_of=before.as_of)
    for row in context['positions']:
        expected=next(r for r in comparison.positions if r.position.value==row['position'])
        assert row['expected_points_delta']==expected.expected_points_delta
        assert row['before_expected_points']==expected.before_expected_points
        assert row['after_expected_points']==expected.after_expected_points
    assert context['starter_replacements']==({'slot':'FLEX','outgoing_player_id':'a2','replacement_was_already_starting':False,'replacement_player_id':'a5'},)


def test_published_strength_reuse_requires_state_horizon_and_full_assignment_identity():
    from types import SimpleNamespace as N
    from fsffl.team_utility import optimize_team_lineup,build_league_relative_position_strengths
    before,after,forecasts,leg=fixture(send='a2')
    lineup=optimize_team_lineup(before,forecasts,team_id='alpha',as_of=before.as_of,
        horizon=ForecastHorizon.SEASON,allow_unfilled_slots=True,model_version='test')
    view=N(team_id='alpha',context=N(league_state_id=before.state_id),optimized_lineup=lineup,
        position_strengths=build_league_relative_position_strengths((lineup,)))
    baseline=N(team_views=(view,))
    def read():
        return _position_comparison_and_context(before,after,forecasts,team_id='alpha',leg=leg,
            horizon=ForecastHorizon.SEASON,forecast_as_of=before.as_of,baseline=baseline)[1]['positions'][0]
    assert read()['baseline_league_strength']['strength_index']==100
    view.context.league_state_id='stale'
    assert 'baseline_league_strength' not in read()
    view.context.league_state_id=before.state_id
    view.optimized_lineup=lineup.model_copy(update={'horizon':ForecastHorizon.REST_OF_SEASON})
    assert 'baseline_league_strength' not in read()
    # Equal totals with a different assigned player still cannot establish identity.
    view.optimized_lineup=lineup.model_copy(update={'assignments':(lineup.assignments[0].model_copy(update={'player_id':'other'}),*lineup.assignments[1:])})
    assert 'baseline_league_strength' not in read()
