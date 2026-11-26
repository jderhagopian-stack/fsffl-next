"""Search quality guards: existing economics, purposeful size, honest benefits."""
from copy import deepcopy
from datetime import datetime, UTC

import pytest

from fsffl.opportunity.guided_strategic_packages import generate_guided_strategic_packages
from fsffl.opportunity.strategic_packages import StrategicSearchBounds, StrategicPackageLane
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.state.models import PlayerAsset, PickAsset
from fsffl.product.strategic_discovery import _representative_indices
from fsffl.product.strategic_discovery_presentation import discovery_display_context
from tests.test_strategic_discovery_presentation import row

NOW=datetime(2026,11,15,tzinfo=UTC)


def test_economics_precede_counterparty_asset_and_shape_novelty():
    def example(team, band, count, joint=False):
        return {'counterparty_team_id':team,'preliminary_economic_band':band,
            'pre_cut_horizon_complement_hypothesis':joint,
            'send':[{'asset_ref':f'player:{i}'} for i in range(count)],
            'receive':[{'asset_ref':'pick:target'}],'hypotheses':[team]}
    rows=[example('new','counterparty_economic_strain',8,True),
          example('same','robust_or_ordinary',1),example('same','bounded_uncertainty',2)]
    assert _representative_indices(rows,2)==[1,2]
    assert rows[0]['preliminary_economic_band']=='counterparty_economic_strain'


def test_package_construction_preserves_hypothesis_order_instead_of_price_closeness():
    a,b,target=PlayerAsset(player_id='priority'),PlayerAsset(player_id='closer'),PlayerAsset(player_id='target')
    lane=StrategicPackageLane('need',TeamTradeInventory(team_id='a',assets=(a,b)),
        TeamTradeInventory(team_id='b',assets=(target,)))
    seeds,diag=generate_guided_strategic_packages((lane,),as_of=NOW,
        bounds=StrategicSearchBounds(max_candidates=12,max_pair_visits=24),
        market_values={a:900.,b:1000.,target:1000.},economic_tolerance=150.)
    assert seeds[0].seed.proposal.side_a.sends==(a,)
    assert diag['pair_visits']<=24
    assert all(s.seed.proposal.side_a.team_id=='a' for s in seeds)


def test_large_pick_bundle_is_earned_by_negotiating_envelope_and_stops_when_met():
    picks=tuple(PickAsset(pick_id=f'p{i}') for i in range(12))
    target=PlayerAsset(player_id='target')
    lane=StrategicPackageLane('spend',TeamTradeInventory(team_id='a',assets=picks),
        TeamTradeInventory(team_id='b',assets=(target,)),required_send=picks[-1],required_receive=target)
    seeds,diag=generate_guided_strategic_packages((lane,),as_of=NOW,
        bounds=StrategicSearchBounds(max_candidates=160,max_pair_visits=160),
        market_values={**{a:10. for a in picks},target:80.},economic_tolerance=0.)
    assert len(seeds[0].seed.proposal.side_a.sends)==8
    assert picks[-1] in seeds[0].seed.proposal.side_a.sends
    assert all(picks[-1] in s.seed.proposal.side_a.sends and target in s.seed.proposal.side_b.sends for s in seeds)
    assert all(max(len(s.seed.proposal.side_a.sends),len(s.seed.proposal.side_b.sends))<=8 for s in seeds)
    assert diag['pair_visits']<=160
    assert len({s.seed.point_id for s in seeds})==len(seeds)


def test_unknown_market_evidence_keeps_bounded_exploration_without_zero_filling():
    a,b=PlayerAsset(player_id='a'),PickAsset(pick_id='b')
    lane=StrategicPackageLane('unknown',TeamTradeInventory(team_id='a',assets=(a,)),
        TeamTradeInventory(team_id='b',assets=(b,)))
    seeds,diag=generate_guided_strategic_packages((lane,),as_of=NOW,
        bounds=StrategicSearchBounds(max_candidates=8,max_pair_visits=8),
        market_values={a:100.},economic_tolerance=10.)
    assert seeds and seeds[0].seed.proposal.side_b.sends==(b,)
    assert diag['guided_pair_visits']==0
    assert diag['pair_visits']<=8


@pytest.mark.parametrize('band',['focal_economic_strain','counterparty_economic_strain'])
def test_economic_strain_cannot_lead_as_a_beneficial_card(band):
    example=row(current=(10,10),three=(100,100),career=(100,100))
    example['preliminary_economic_band']=band;before=deepcopy(example)
    assert discovery_display_context(example)['group']=='priority_concern'
    assert example==before


def test_post_cut_dominated_side_cannot_be_promoted_by_a_positive_component():
    example=row(current=(0,10),three=(100,100),career=(-200,100))
    example['preliminary_decision_screen']['focal']['shape']='dominated'
    assert discovery_display_context(example)['group']=='priority_concern'


def test_neutral_current_rounding_cannot_manufacture_a_fit():
    example=row(goals_a=('current_competitiveness',),goals_b=('current_competitiveness',),current=(1e-14,10))
    assert discovery_display_context(example)['group']=='needs_evidence'


def test_calendar_only_tradeoff_stays_secondary_when_current_is_requested():
    example=row(current=(1e-14,0),three=(-30,40),career=(100,-100))
    assert discovery_display_context(example)['group']=='needs_evidence'
    # A deliberate long-term direction still has access to the same transaction.
    example['objective_assessment']['side_a']['context']['objectives']=['career_contribution']
    assert discovery_display_context(example)['group']=='preliminary_fit'


def test_real_current_upgrade_with_future_sacrifice_remains_an_explicit_tradeoff():
    example=row(current=(8,4),three=(1,-1),career=(-80,80),goals_b=('career_contribution',))
    example['preliminary_economic_band']='robust_or_ordinary'
    assert discovery_display_context(example)['group']=='priority_tradeoff'


def test_second_same_size_price_match_is_not_lost_before_bilateral_screen():
    from fsffl.opportunity.guided_strategic_packages import _lane_stream
    starter,bench,wr,target=(PlayerAsset(player_id=x) for x in ('starter','bench','wr','target'))
    lane=StrategicPackageLane('upgrade',TeamTradeInventory(team_id='a',assets=(starter,bench,wr)),
        TeamTradeInventory(team_id='b',assets=(target,)),required_receive=target)
    values={starter:200.,bench:350.,wr:2800.,target:3150.}
    options=list(_lane_stream(lane,bounds=StrategicSearchBounds(),values=values,tolerance=240.))
    assert any(set(send)=={starter,wr} for send,receive in options)
    assert any(set(send)=={bench,wr} for send,receive in options)
    assert all(receive==(target,) for send,receive in options)


def test_requested_directions_and_small_funded_shapes_receive_search_coverage():
    def r(key,goal,hint,size):
        return {'point_id':key,'focal_team_id':'a','counterparty_team_id':'b',
            'preliminary_economic_band':'robust_or_ordinary','joint_priority_gain_hypothesis':True,
            'search_objectives':['current_competitiveness','career_contribution'],
            'priority_gain_hints':{goal:hint},'requested_native_compatibility':goal=='career_contribution',
            'send':[{'asset_ref':key+str(i)} for i in range(size-1)],'receive':[{'asset_ref':'target'}],
            'hypotheses':[]}
    rows=[r('tiny_future','career_contribution',1,2),r('current','current_competitiveness',10,2),
          r('funded','current_competitiveness',20,3),r('later','career_contribution',10,3)]
    selected=_representative_indices(rows,4)
    assert selected[0]==1  # Current is not suppressed by future-compatible offers.
    assert set(selected)=={0,1,2,3}
