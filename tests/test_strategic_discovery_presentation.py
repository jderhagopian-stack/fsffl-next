"""Known priority losses cannot lead Explore as a clear fit."""
from copy import deepcopy
import pytest
from fsffl.product.strategic_discovery_presentation import discovery_display_context


def row(goals_a=('current_competitiveness','three_year_contribution','career_contribution'),
        goals_b=('three_year_contribution',), current=(-5, 12), three=(-170, 95), career=(-320, 200)):
    def side(goals, i):
        return {'context': {'objectives': goals}, 'protected_players_lost': [], 'metrics': [
            {'objective': g, 'delta': d[i], 'authoritative': True, 'higher_is_better': True}
            for g,d in [('three_year_contribution',three),('career_contribution',career)]]}
    return {'evidence_status':'pre_simulation_screened','action_authority':'diagnostic_only',
        'objective_assessment': {'side_a':side(goals_a,0),'side_b':side(goals_b,1)},
        'preliminary_decision_screen': {'current_points_basis':'remaining_regular_season_weekly_mean',
            'focal':{'starter_points_delta':current[0]},'counterparty':{'starter_points_delta':current[1]}}}


def test_adverse_root_stays_a_concern_despite_market_gain_and_unresolved_final_outcomes():
    example=row();example['roster_adjusted_market_net']={'side_a':{'roster_adjusted_market_delta':2000}}
    before=deepcopy(example)
    display=discovery_display_context(example)
    assert display['group']=='priority_concern'
    assert 'no demonstrated offset' in display['reason']
    assert example==before  # Classification does not rewrite models or action truth.


def test_win_now_repair_can_lead_but_balanced_keeps_the_future_cost_visible():
    example=row(current=(9,-2))
    assert discovery_display_context(example)['group']=='priority_tradeoff'
    example['objective_assessment']['side_a']['context']['objectives']=['current_competitiveness']
    display=discovery_display_context(example)
    assert display['group']=='preliminary_fit'
    assert display['current_uses_lineup_proxy']
    assert display['decision_effect']=='no_disposition_change'


@pytest.mark.parametrize('side', ['side_a','side_b'])
def test_known_native_loss_is_visible_even_with_missing_current_outcomes(side):
    example=row(current=(None,None))
    example['objective_assessment'][side]['context']['objectives']=['current_competitiveness','three_year_contribution']
    example['objective_assessment'][side]['metrics'][0]['delta']=-10
    assert discovery_display_context(example)['group']=='priority_concern'


def test_missing_native_or_unrequested_market_gain_cannot_establish_fit():
    example=row(goals_a=('three_year_contribution',),three=(100,100))
    example['objective_assessment']['side_a']['metrics'][0]['authoritative']=False
    assert discovery_display_context(example)['group']=='needs_evidence'
    example=row(current=(None,None),three=(0,100),career=(0,100))
    assert discovery_display_context(example)['group']=='needs_evidence'


@pytest.mark.parametrize('side',['side_a','side_b'])
def test_protected_cut_is_never_a_fit(side):
    example=row(goals_a=('current_competitiveness',),current=(9,-2))
    example['objective_assessment'][side]['protected_players_lost']=['keep']
    assert discovery_display_context(example)['group']=='priority_concern'


def test_discovery_exposes_published_competitive_context_without_overriding_user_goals():
    from fsffl.product.strategic_discovery import build_strategic_discovery, StrategicDiscoveryRequest
    from fsffl.product.opportunity_posture import calculated_competitive_state
    from tests.test_strategic_feedback import controlled_root
    runtime, _, _ = controlled_root()
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(evaluation_budget=0,
        search_instructions={'objectives':['career_contribution']}))
    competitive=result['competitive_context']
    assert competitive['calculated_competitive_state']==calculated_competitive_state(runtime).value
    outcome=next(o for o in runtime.simulation_analytics.simulation_result.outcomes if o.team_id==runtime.selected_team_id)
    assert competitive['playoff_probability']==outcome.playoff_probability
    assert competitive['championship_probability']==outcome.championship_probability
    assert result['priority_context']['objectives']==['career_contribution']
    assert result['priority_context']['explicitly_directed']
    assert all(r['display_context']['group']=='needs_evidence' for r in result['candidate_packages'])
    assert result['diagnostics']['changed_state_simulation_calls']==0
