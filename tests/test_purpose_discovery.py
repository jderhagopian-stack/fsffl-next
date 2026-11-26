from types import SimpleNamespace as NS
from dataclasses import replace
from datetime import timedelta
import pytest
from fsffl.state.models import PlayerAsset,PickAsset,Position
from fsffl.trade_decision.objectives import TradeObjective as G,OwnerObjectiveContext
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.opportunity.strategic_packages import StrategicPackageLane,StrategicSearchBounds,StrategicPurpose
from fsffl.opportunity.guided_strategic_packages import generate_guided_strategic_packages
from fsffl.behavioral.discovery_interests import ObservedAcquisitionInterest,observed_acquisition_interests
from fsffl.product.discovery_purposes import pair_purpose_lanes,review_purposes,matching_published_lineups
from fsffl.product.strategic_discovery import build_discovery_lanes,build_strategic_discovery,StrategicDiscoveryRequest
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
from tests.test_contextual_trade_precedents import example
from tests.test_strategic_discovery import governed_runtime_fixture
from tests.test_strategic_packages import NOW


def pair(**changes):
    # QB prefix hides the WR from the ordinary 12-ingredient window.
    qbs=tuple(PlayerAsset(player_id=f'q{i}') for i in range(12))
    wr=PlayerAsset(player_id='outside-wr');rb=PlayerAsset(player_id='target-rb');pick=PickAsset(pick_id='future')
    focal=TeamTradeInventory(team_id='a',assets=(*qbs,wr,pick));other=TeamTradeInventory(team_id='b',assets=(rb,pick.model_copy(update={'pick_id':'theirs'})))
    metrics={g:{} for g in G};metrics[G.CURRENT]={**{a:10. for a in qbs},wr:20.,rb:30.}
    metrics[G.CAREER]={a:100. for a in (*focal.assets,*other.assets)}
    context=lambda team:OwnerObjectiveContext(team_id=team,objectives=(G.CURRENT,),source='fixture')
    args=dict(state_id='state',focal=focal,other=other,context=context('a'),other_context=context('b'),
        strengths={},lineups={},metrics=metrics,positions={**{a.player_id:Position.QB for a in qbs},'outside-wr':Position.WR,'target-rb':Position.RB},
        ages={'target-rb':24},roster_fit=lambda assets,team:tuple(assets),required_send=None,required_receive=None,interests={})
    args.update(changes)
    return args,wr,rb


def test_positive_history_adds_an_asset_outside_ordinary_prefix_without_removing_base_paths():
    args,wr,rb=pair();base=StrategicPackageLane('ordinary',args['focal'],args['other'])
    no_history=pair_purpose_lanes(**args)
    assert not any(l.purpose.kind=='observed_acquisition' for l in no_history)
    args['interests']={'b':(ObservedAcquisitionInterest('position','WR',3,('event',)),)}
    extra=pair_purpose_lanes(**args)
    owner=next(l for l in extra if l.purpose.kind=='observed_acquisition')
    assert owner.focal.assets==(wr,) and owner.purpose.observed_trade_count==3
    values={a:100. for a in (*args['focal'].assets,*args['other'].assets)}
    bounds=StrategicSearchBounds(max_candidates=40,max_pair_visits=80)
    old,_=generate_guided_strategic_packages((base,*no_history),as_of=NOW,bounds=bounds,market_values=values,economic_tolerance=0)
    new,diag=generate_guided_strategic_packages((base,*extra),as_of=NOW,bounds=bounds,market_values=values,economic_tolerance=0)
    assert not any(wr in r.seed.proposal.side_a.sends for r in old)
    assert any(wr in r.seed.proposal.side_a.sends for r in new)
    assert diag['guided_path_visits']['ordinary']>0 and diag['guided_path_visits']['owner_history']>0
    assert diag['pair_visits']<=80 and len({r.seed.point_id for r in new})==len(new)
    assert args['other_context'].objectives==(G.CURRENT,)  # A contender is not barred from pick/WR routes.


def test_pick_history_adds_pick_led_offer_even_for_current_focused_counterparty():
    args,_,_=pair();args['interests']={'b':(ObservedAcquisitionInterest('pick',None,2,('one','two')),)}
    lanes=pair_purpose_lanes(**args)
    owner=next(l for l in lanes if l.purpose.kind=='observed_acquisition')
    assert all(isinstance(a,PickAsset) for a in owner.focal.assets)
    assert owner.purpose.action_authority=='hypothesis_only'


def test_upgrade_target_is_pinned_and_depth_is_not_called_surplus():
    args,wr,rb=pair()
    args['lineups']={'a':NS(assignments=(NS(player_id="existing-rb",position=Position.RB,expected_points=10.),),bench_player_ids=(wr.player_id,)),
                     'b':NS(assignments=(NS(player_id="existing-wr",position=Position.WR,expected_points=10.),),bench_player_ids=())}
    args['strengths']={'a':{Position.RB:NS(position=Position.RB,starter_count=1,strength_index=80.)}}
    lanes=pair_purpose_lanes(**args)
    upgrade=next(l for l in lanes if l.purpose.kind=='improve_lineup')
    conversion=next(l for l in lanes if l.purpose.kind=='test_depth_conversion')
    assert upgrade.required_receive==rb and conversion.required_send==wr
    row={'focal_team_id':'a','discovery_purposes':[conversion.purpose.model_dump(mode='json')],
        'evidence_status':'pre_simulation_screened','preliminary_decision_screen':{
            'current_points_basis':'remaining_regular_season_weekly_mean','focal':{'starter_points_delta':0}}}
    review_purposes(row)
    assert row['discovery_purposes'][0]['result']=='current_lineup_preserved'
    assert row['discovery_purposes'][0]['surplus_confirmed'] is False


def test_user_offer_and_target_cannot_be_relaxed_to_follow_history():
    args,wr,rb=pair();args['interests']={'b':(ObservedAcquisitionInterest('position','WR',1,('event',)),)}
    args['required_send']=args['focal'].assets[0]
    assert not any(l.purpose.kind=='observed_acquisition' for l in pair_purpose_lanes(**args))
    args['required_send']=None;args['required_receive']=args['other'].assets[-1]
    args['lineups']={'a':NS(assignments=(NS(player_id="existing-rb",position=Position.RB,expected_points=10.),),bench_player_ids=())}
    args['strengths']={'a':{Position.RB:NS(position=Position.RB,starter_count=1,strength_index=80.)}}
    assert not any(l.purpose.kind=='improve_lineup' for l in pair_purpose_lanes(**args))


def test_history_is_receipt_fenced_and_does_not_invent_youth_or_use_undated_position_counts():
    case,p,_,_,_=example()
    interests=observed_acquisition_interests(p,as_of=p.as_of)
    assert [(i.kind,i.position,i.trade_count) for i in interests]==[('position','RB',1)]
    assert not observed_acquisition_interests(p,as_of=p.as_of-timedelta(days=1))
    foreign=case.model_copy(update={'owner_id':'foreign'})
    assert not observed_acquisition_interests(p.model_copy(update={'historical_trade_cases':(foreign,)}),as_of=p.as_of)
    undated=p.model_copy(update={'historical_trade_cases':(),'acquired_positions':{'WR':100}})
    assert not observed_acquisition_interests(undated,as_of=p.as_of)


@pytest.mark.parametrize('superflex',[False,True])
def test_actual_generation_screen_and_filters_reuse_published_models(superflex):
    runtime,record=governed_runtime_fixture(superflex=superflex,team_count=4)
    # Controlled feasible prices isolate search coverage from pricing accuracy.
    # The published lineups and all subsequent replacement checks are real fixture
    # calculations, not mocked favorable trade outcomes.
    from fsffl.product.simulation_forecasts import current_forecast_coordinates
    from fsffl.team_utility import optimize_team_lineup
    from fsffl.team_utility.position_strength import build_league_relative_position_strengths
    positions={p.player_id:p.position for p in runtime.league_state.players}
    evidence=replace(runtime.forecast_evidence,league_scored_forecasts=tuple(
        f.model_copy(update={'position':positions[f.player_id]}) for f in runtime.forecast_evidence.league_scored_forecasts))
    runtime=replace(runtime,forecast_evidence=evidence,value_evidence=NS(fsffl_cardinal_values=tuple(
        v.model_copy(update={'score':500.}) for v in runtime.value_evidence.fsffl_cardinal_values)))
    forecasts,horizon,cutoff=current_forecast_coordinates(runtime.league_state,evidence)
    lineups=tuple(optimize_team_lineup(runtime.league_state,forecasts,team_id=t.team_id,
        as_of=cutoff,horizon=horizon,allow_unfilled_slots=True) for t in runtime.league_state.teams)
    strengths=build_league_relative_position_strengths(lineups)
    simulation=NS(league_view=NS(context=NS(league_state_id=runtime.league_state.state_id)),
        team_views=tuple(NS(team_id=l.team_id,optimized_lineup=l,position_strengths=tuple(
            s for s in strengths if s.team_id==l.team_id)) for l in lineups),
        simulation_result=NS(outcomes=()),scenario_preparation=None)
    runtime=replace(runtime,selected_team_id='t3',simulation_analytics=simulation)
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(p.player_id for p in runtime.league_state.players),
        record=record,publication_validator=lambda c,r:True)
    before=runtime.league_state.model_dump(mode='json')
    request=StrategicDiscoveryRequest(max_candidates=24,evaluation_budget=8,search_instructions={
        'objectives':['current_competitiveness','career_contribution'],'protected_player_ids':['t3-0']})
    result=build_strategic_discovery(runtime,request,read=read)
    assert result['diagnostics']['purpose_lane_count']>0
    assert result['diagnostics']['guided_path_visits']['ordinary']>0
    assert result['diagnostics']['guided_path_visits']['team_purpose']>0
    assert result['diagnostics']['preliminary_decision_attempts']==8
    assert result['diagnostics']['changed_state_simulation_calls']==0
    assert result['diagnostics']['preliminary_decision_errors']==0
    assert any(r['discovery_purposes'] for r in result['candidate_packages'])
    assert all(a['asset_ref']!='player:t3-0' for r in result['candidate_packages'] for a in r['send'])
    assert runtime.league_state.model_dump(mode='json')==before
    lineups=matching_published_lineups(runtime);assert lineups
    foreign=replace(runtime,league_state=runtime.league_state.model_copy(update={'as_of':runtime.league_state.as_of+timedelta(days=1)}))
    assert not matching_published_lineups(foreign)


def test_all_three_paths_receive_bounded_turns_without_value_or_size_changes():
    from tests.test_strategic_packages import inventory
    a,b=inventory('a',12),inventory('b',12)
    def purpose(kind):return StrategicPurpose(kind=kind,team_id='a',partner_team_id='b',source_state_id='s')
    lanes=(StrategicPackageLane('ordinary',a,b),StrategicPackageLane('purpose',a,b,purpose=purpose('acquire_future_assets')),
           StrategicPackageLane('owner',a,b,purpose=purpose('observed_acquisition')))
    values={x:100. for x in (*a.assets,*b.assets)};before=dict(values)
    seeds,diag=generate_guided_strategic_packages(lanes,as_of=NOW,
        bounds=StrategicSearchBounds(max_candidates=80,max_pair_visits=64),market_values=values,economic_tolerance=0)
    assert diag['guided_path_visits']=={'ordinary':28,'team_purpose':14,'owner_history':14}
    assert diag['pair_visits']<=64 and values==before
    assert all(len(r.seed.proposal.side_a.sends)+len(r.seed.proposal.side_b.sends)<=10 for r in seeds)


def test_owner_evidence_adds_lanes_without_changing_ordinary_inventory_or_user_context(monkeypatch):
    runtime,_=governed_runtime_fixture(team_count=4)
    request=StrategicDiscoveryRequest(search_instructions={'objectives':['current_competitiveness'],'protected_player_ids':['t0-0']})
    ordinary=build_discovery_lanes(runtime,request,None)
    # A controlled evidence packet isolates composition; reader admission is
    # tested independently above. It cannot alter Value or competitive context.
    monkeypatch.setattr('fsffl.behavioral.discovery_interests.observed_acquisition_interests',
        lambda profile,as_of:(ObservedAcquisitionInterest('position','WR',3,('controlled-event',)),))
    expanded=build_discovery_lanes(runtime,request,None)
    assert tuple(l for l in ordinary[0] if l.purpose is None)==tuple(l for l in expanded[0] if l.purpose is None)
    assert ordinary[1]==expanded[1]
    assert any(l.purpose and l.purpose.kind=='observed_acquisition' for l in expanded[0])
    assert all(a.player_id!='t0-0' for l in expanded[0] for a in l.focal.assets if isinstance(a,PlayerAsset))


def test_current_receipt_must_be_observed_and_does_not_supply_historical_positions():
    from tests.test_owner_current_season import profiles,NOW as CURRENT_CUTOFF
    a,b=profiles()
    assert not observed_acquisition_interests(a,as_of=CURRENT_CUTOFF)
    assert any(i.kind=='pick' for i in observed_acquisition_interests(a,as_of=CURRENT_CUTOFF+timedelta(days=3)))
    activity=b.current_season_activity;move=activity.trade_examples[0]
    labels=tuple(asset.model_copy(update={'position':'WR'}) for asset in move.event.acquired)
    move=move.model_copy(update={'event':move.event.model_copy(update={'acquired':labels})})
    b=b.model_copy(update={'current_season_activity':activity.model_copy(update={'trade_examples':(move,)})})
    assert not observed_acquisition_interests(b,as_of=CURRENT_CUTOFF+timedelta(days=3))
