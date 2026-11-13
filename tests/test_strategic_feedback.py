from dataclasses import replace
from types import SimpleNamespace as NS

import pytest

from fsffl.forecast.models import ForecastDistribution
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.strategic_feedback import FeedbackVisits, repair_path, needs_second_step
from fsffl.product.webapp import _build_default_simulation
from fsffl.state.models import Player, PlayerState, RosterEntry, LineupRequirement
from tests.test_simulation_ros_inputs import fixture
from tests.test_bye_aware_weekly_simulation import PROV


def controlled_root(*, superflex=False):
    """Synthetic upstream packet for geometry/guard tests, never NFL evidence."""
    state, evidence = fixture()
    rules = state.league.rules.model_copy(update={'roster_size': 4,
        'lineup': (LineupRequirement(slot='QB', count=1),) + (
            (LineupRequirement(slot='SUPERFLEX', count=1),) if superflex else ())})
    additions = tuple(Player(player_id=pid, full_name=pid, position='QB', nfl_team='BUF')
                      for pid in ('second', 'reserve'))
    state = state.model_copy(update={
        'league': state.league.model_copy(update={'rules': rules}),
        'players': (*state.players, *additions),
        'player_states': (*state.player_states, *(PlayerState(player_id=p.player_id,
            as_of=state.as_of, nfl_team=p.nfl_team, provenance=PROV) for p in additions)),
        'team_states': (state.team_states[0].model_copy(update={'roster': (
            *state.team_states[0].roster, RosterEntry(player_id='second', slot='BENCH'),
            RosterEntry(player_id='reserve', slot='BENCH'))}), state.team_states[1])})
    template = evidence.simulation_forward_forecasts[-1]
    rows = (*evidence.simulation_forward_forecasts, *(template.model_copy(update={
        'player_id': pid, 'distribution': ForecastDistribution(mean=mean, stddev=0)})
        for pid, mean in (('second', 80), ('reserve', 30))))
    evidence = replace(evidence, simulation_source_state_id=state.state_id,
                       simulation_forward_forecasts=rows)
    baseline = _build_default_simulation(state, evidence, simulation_count=100)
    runtime = UserRuntimeContext(user_id='u', league_state=state, selected_team_id='a',
        forecast_evidence=evidence, simulation_analytics=baseline)
    root = {'point_id': 'root', 'counterparty_team_id': 'b',
        'send': [{'asset_ref': 'player:second'}, {'asset_ref': 'player:bench'}],
        'receive': [{'asset_ref': 'player:opp'}],
        'preliminary_decision_screen': {'current_points_basis': 'remaining_regular_season_weekly_mean',
            'focal': {'starter_points_delta': -5}},
        'objective_assessment': {
            'side_a': {'context': {'objectives': ['current_competitiveness']}, 'protected_players_lost': []},
            'side_b': {'context': {'objectives': ['three_year_contribution']},
                       'status': 'aligns_with_priorities', 'protected_players_lost': []}}}
    read = NS(values={'three_year': {'starter': 1, 'bench': 1000, 'reserve': 100},
                      'career': {'starter': 1, 'bench': 1000, 'reserve': 100}})
    return runtime, root, read


@pytest.mark.parametrize('superflex', [False, True])
def test_two_step_owned_replacement_keeps_target_and_counts_each_visit(superflex):
    runtime, root, read = controlled_root(superflex=superflex)
    visits = FeedbackVisits(8)
    path = list(repair_path(runtime, root, read, protected_player_ids=(), visits=visits))
    assert len(path) == 2 and visits.used == 2
    assert path[0][1]['depth'] == 1 and path[1][1]['depth'] == 2
    assert path[0][1]['root_point_id'] == root['point_id']
    assert path[1][1]['parent_point_id'] == path[0][0].point_id
    assert {a.player_id for a in path[1][0].focal_package.assets} == {'bench', 'reserve'}
    assert all([a.player_id for a in p.counterparty_package.assets] == ['opp'] for p, _ in path)
    assert all(len(p.focal_package.assets) <= 2 and line['hypothesis_only'] for p, line in path)
    assert runtime.league_state.state_id == runtime.forecast_evidence.simulation_source_state_id


def test_exhaustion_cannot_emit_uncounted_addition():
    runtime, root, read = controlled_root()
    visits = FeedbackVisits(1)
    path = list(repair_path(runtime, root, read, protected_player_ids=(), visits=visits))
    assert len(path) == 1 and visits.used == 1 and visits.exhausted
    visits = FeedbackVisits(0)
    assert not list(repair_path(runtime, root, read, protected_player_ids=(), visits=visits))
    assert visits.used == 0 and visits.exhausted


def test_protected_and_missing_coverage_assets_never_become_repair_sends():
    runtime, root, read = controlled_root()
    visits = FeedbackVisits(8)
    assert not list(repair_path(runtime, root, read,
        protected_player_ids=('reserve', 'starter'), visits=visits))
    assert visits.used == 0
    read.values['three_year'].clear()
    assert not list(repair_path(runtime, root, read, protected_player_ids=(), visits=FeedbackVisits(8)))


@pytest.mark.parametrize('mutation', ['source', 'future_goal', 'protected_cut', 'current_goal', 'missing_baseline'])
def test_unconfirmed_or_conflicting_evidence_stops_before_geometry(mutation):
    runtime, root, read = controlled_root()
    if mutation == 'source':
        runtime = replace(runtime, forecast_evidence=replace(runtime.forecast_evidence,
                          simulation_source_state_id='other'))
    elif mutation == 'future_goal': root['objective_assessment']['side_b']['status'] = 'incomplete'
    elif mutation == 'protected_cut': root['objective_assessment']['side_a']['protected_players_lost'] = ['starter']
    elif mutation == 'current_goal': root['objective_assessment']['side_a']['context']['objectives'] = ['career_contribution']
    else: runtime = replace(runtime, simulation_analytics=None)
    visits = FeedbackVisits(8)
    assert not list(repair_path(runtime, root, read, protected_player_ids=(), visits=visits))
    assert visits.used == 0


def test_second_step_is_not_forced_after_success_or_constraint_failure():
    row = {'evidence_status': 'pre_simulation_screened',
        'objective_assessment': {'side_a': {'protected_players_lost': []},
                                 'side_b': {'status': 'aligns_with_priorities'}},
        'preliminary_decision_screen': {'focal': {'starter_points_delta': 2}}}
    assert not needs_second_step(row)
    row['objective_assessment']['side_b']['status'] = 'conflicts_with_priorities'
    assert needs_second_step(row)
    row['objective_assessment']['side_a']['protected_players_lost'] = ['keep']
    assert not needs_second_step(row)
    assert not needs_second_step({'evidence_status': 'screen_unavailable'})


@pytest.mark.parametrize('mutation', ['foreign_send', 'foreign_receive', 'protected_root'])
def test_repair_revalidates_owned_and_protected_root_assets(mutation):
    runtime, root, read = controlled_root()
    protected = ()
    if mutation == 'foreign_send': root['send'][0]['asset_ref'] = 'player:opp'
    elif mutation == 'foreign_receive': root['receive'][0]['asset_ref'] = 'player:reserve'
    else: protected = ('second',)
    visits = FeedbackVisits(8)
    assert not list(repair_path(runtime, root, read, protected_player_ids=protected, visits=visits))
    assert visits.used == 0
