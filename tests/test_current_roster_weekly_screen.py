from dataclasses import replace

import pytest

from fsffl.forecast.models import ForecastDistribution
from fsffl.product.current_roster_screen import remaining_regular_points
from fsffl.product.market_discovery_runtime import evaluate_candidate_path
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.webapp import _build_default_simulation
from fsffl.state.models import LineupRequirement, PlayerAsset
from fsffl.trade_decision import BilateralTradeProposal, TradeLeg, apply_bilateral_trade
from tests.test_simulation_ros_inputs import fixture, market


def case(*, superflex=False, zero=False):
    state, evidence = fixture()
    # Team b sends a 120-point QB for a 130-point QB who misses the first
    # remaining fantasy week. A total-ROS lineup incorrectly calls this +10.
    state = state.model_copy(update={
        'team_states': tuple(t.model_copy(update={'roster': tuple(
            r for r in t.roster if r.player_id != 'bench')}) for t in state.team_states)})
    if superflex:
        rules = state.league.rules.model_copy(update={'lineup': (
            LineupRequirement(slot='QB', count=1), LineupRequirement(slot='SUPERFLEX', count=1))})
        state = state.model_copy(update={'league': state.league.model_copy(update={'rules': rules})})
    rows = tuple(r.model_copy(update={'distribution': ForecastDistribution(
        mean=(0 if zero else 130) if r.player_id == 'starter' else 120, stddev=0)})
        for r in evidence.simulation_forward_forecasts if r.player_id != 'bench')
    evidence = replace(evidence, simulation_source_state_id=state.state_id,
                       simulation_forward_forecasts=rows)
    runtime = UserRuntimeContext(user_id='u', league_state=state, selected_team_id='b',
        forecast_evidence=evidence, value_evidence=market(state))
    proposal = BilateralTradeProposal(proposal_id='bye-reversal', as_of=state.as_of,
        side_a=TradeLeg(team_id='b', sends=(PlayerAsset(player_id='opp'),)),
        side_b=TradeLeg(team_id='a', sends=(PlayerAsset(player_id='starter'),)))
    return runtime, apply_bilateral_trade(state, proposal).after


@pytest.mark.parametrize('superflex', [False, True])
def test_actual_preliminary_route_uses_weekly_sign_and_declares_units(superflex):
    runtime, _ = case(superflex=superflex)
    result = evaluate_candidate_path(runtime, {'counterparty_team_id': 'a',
        'send': [{'asset_ref': 'player:opp'}], 'receive': [{'asset_ref': 'player:starter'}]})
    screen = result['preliminary_bilateral_screen']
    assert screen['current_points_basis'] == 'remaining_regular_season_weekly_mean'
    assert screen['current_points_unit'] == 'fantasy_points'
    assert screen['current_points_weeks'] == [5, 6]
    assert screen['focal']['starter_points_delta'] == pytest.approx(-110 / 13)
    assert screen['shape'] == 'focal_dominated'
    assert screen['acceptance_probability'] is None
    assert not result['decision_completeness']['simulation_backed']
    # Keep the distinct total-ROS positional diagnostic rather than relabel it.
    comparison = result['position_strength_comparisons']['b']
    assert sum(p['expected_points_delta'] for p in comparison['positions']) == 10


def test_zero_ros_never_becomes_a_positional_floor_or_preseason_projection():
    runtime, changed = case(zero=True)
    points = remaining_regular_points(runtime, changed, team_ids=('b', 'a'))
    assert points['deltas']['b'] == pytest.approx(-240 / 13)


def test_exact_published_panel_is_reused_but_stale_forecast_panel_is_not(monkeypatch):
    runtime, changed = case()
    baseline = _build_default_simulation(runtime.league_state, runtime.forecast_evidence,
                                         simulation_count=100)
    runtime = replace(runtime, simulation_analytics=baseline)
    import fsffl.product.current_roster_screen as module
    calls = []
    original = module.build_bye_aware_weekly_team_scoring_panel
    def observed(state, *args, **kwargs):
        calls.append(state.state_id)
        return original(state, *args, **kwargs)
    monkeypatch.setattr(module, 'build_bye_aware_weekly_team_scoring_panel', observed)
    reused = remaining_regular_points(runtime, changed, team_ids=('b', 'a'))
    assert reused['baseline_reused'] and calls == [changed.state_id]
    stale = baseline.model_copy(update={'scenario_preparation': baseline.scenario_preparation.model_copy(
        update={'forecast_fingerprint': 'stale'})})
    calls.clear()
    rebuilt = remaining_regular_points(replace(runtime, simulation_analytics=stale), changed,
                                        team_ids=('b', 'a'))
    assert not rebuilt['baseline_reused']
    assert calls == [runtime.league_state.state_id, changed.state_id]
    assert rebuilt['deltas'] == reused['deltas']


def test_missing_or_different_source_state_cannot_use_weekly_screen():
    runtime, changed = case()
    for evidence in (replace(runtime.forecast_evidence, simulation_source_state_id='other'),
                     replace(runtime.forecast_evidence, simulation_missing_player_ids=('starter',))):
        with pytest.raises(ValueError):
            remaining_regular_points(replace(runtime, forecast_evidence=evidence), changed,
                                     team_ids=('b', 'a'))


def test_only_actual_remaining_regular_games_count_not_completed_or_postseason():
    runtime, changed = case()
    # Team a's week 5 matchup is removed: its hypothetical score that week
    # must not enter the comparison merely because team b still has a game.
    from fsffl.state.models import LeagueMatchup
    from tests.test_bye_aware_weekly_simulation import PROV
    from fsffl.state.models import Team, TeamState
    additions = {
        'league': runtime.league_state.league.model_copy(update={'rules':
            runtime.league_state.league.rules.model_copy(update={'team_count': 3})}),
        'teams': (*runtime.league_state.teams, Team(team_id='c',
            league_id=runtime.league_state.league.league_id, display_name='C')),
        'team_states': (*runtime.league_state.team_states, TeamState(team_id='c', roster=())),
        'matchups': (LeagueMatchup(week=5, team_a_id='b', team_b_id='c', provenance=PROV),
            *[m for m in runtime.league_state.matchups if m.week != 5]),
    }
    state = runtime.league_state.model_copy(update=additions)
    changed = changed.model_copy(update={k: v for k, v in additions.items() if k != 'team_states'})
    changed = changed.model_copy(update={'team_states': (*changed.team_states, TeamState(team_id='c', roster=()))})
    evidence = replace(runtime.forecast_evidence, simulation_source_state_id=state.state_id)
    points = remaining_regular_points(replace(runtime, league_state=state,
        forecast_evidence=evidence), changed, team_ids=('b', 'a'))
    assert points['weeks_by_team'] == {'b': (5, 6), 'a': (6,)}
    assert points['deltas']['a'] == pytest.approx(-10 / 13)
