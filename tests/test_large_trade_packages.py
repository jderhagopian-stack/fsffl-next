from collections import Counter
from datetime import datetime, UTC
from itertools import islice

import pytest
from fastapi.testclient import TestClient

from fsffl.opportunity.strategic_packages import (
    StrategicPackageLane, StrategicSearchBounds, generate_strategic_packages, _diagonal_pairs,
)
from fsffl.opportunity.trade_universe import TeamTradeInventory
from fsffl.state.models import PlayerAsset, PickAsset, FaabAsset
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.product.strategic_discovery import StrategicDiscoveryRequest, build_strategic_discovery, _representative_indices
from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values, build_trade_intrinsic_evidence
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
from tests.test_strategic_discovery import governed_runtime_fixture

NOW=datetime(2026,11,14,tzinfo=UTC)


def inventory(team, *, players=20, picks=12):
    return TeamTradeInventory(team_id=team,assets=tuple(PlayerAsset(player_id=f'{team}:p{i}') for i in range(players))+
        tuple(PickAsset(pick_id=f'{team}:k{i}') for i in range(picks)))


def test_full_size_envelope_is_sampled_with_bounded_lazy_materialization(monkeypatch):
    import fsffl.opportunity.strategic_packages as module
    original=module._package_stream;built=[]
    def counted(inv,size,required):
        assert len(inv.assets)<=12
        for package in original(inv,size,required):
            built.append(package)
            yield package
    monkeypatch.setattr(module,'_package_stream',counted)
    def forbidden(*args,**kwargs):raise AssertionError('full package enumeration is prohibited')
    monkeypatch.setattr('fsffl.opportunity.trade_universe.enumerate_trade_packages',forbidden)
    lanes=tuple(StrategicPackageLane(name,inventory('a'),inventory(f'b{i}')) for name in ('fit','horizon','structure') for i in range(11))
    seeds,diagnostics=generate_strategic_packages(lanes,as_of=NOW,bounds=StrategicSearchBounds(max_candidates=640,max_pair_visits=640))
    shapes={(len(s.seed.proposal.side_a.sends),len(s.seed.proposal.side_b.sends)) for s in seeds}
    assert {(1,1),(2,2),(1,8),(8,1),(2,6),(6,2),(4,6),(6,4),(5,5)}<=shapes
    assert all(max(a,b)<=8 and a+b<=10 for a,b in shapes)
    assert diagnostics['pair_visits']<=640 and len(seeds)<=640
    assert len(built)<=2*diagnostics['pair_visits']
    assert diagnostics['package_enumeration']=='lazy_cardinality_streams'
    assert diagnostics['counterparties_visited']==11 and not diagnostics['exhaustive_league_search']


def test_large_required_assets_are_pinned_before_ingredient_limit():
    left,right=inventory('a'),inventory('b')
    required_send=left.assets[-1];required_receive=right.assets[-1]
    lanes=(StrategicPackageLane('target',left,right,required_send=required_send,required_receive=required_receive),)
    before=left.model_dump_json(),right.model_dump_json()
    seeds,diag=generate_strategic_packages(lanes,as_of=NOW,bounds=StrategicSearchBounds(max_candidates=160))
    assert seeds and all(required_send in s.seed.proposal.side_a.sends and required_receive in s.seed.proposal.side_b.sends for s in seeds)
    assert any(max(len(s.seed.proposal.side_a.sends),len(s.seed.proposal.side_b.sends))==8 for s in seeds)
    assert before==(left.model_dump_json(),right.model_dump_json())
    assert len({s.seed.point_id for s in seeds})==len(seeds)


def test_small_config_remains_available_and_diagonal_stream_does_not_eagerly_consume():
    made=[]
    def stream(prefix):
        for i in range(100000):
            made.append((prefix,i));yield (prefix,i)
    pairs=list(islice(_diagonal_pairs(stream('a'),stream('b')),4))
    assert len(pairs)==4 and len(made)==6
    assert set(_diagonal_pairs([1,2],[3,4,5]))=={(a,b) for a in (1,2) for b in (3,4,5)}
    seeds,diag=generate_strategic_packages((StrategicPackageLane('small',inventory('a'),inventory('b')),),as_of=NOW,
        bounds=StrategicSearchBounds(max_assets_per_side=2,max_total_assets=4))
    assert set(diag['shapes'])=={'1_for_1','1_for_2','2_for_1','2_for_2'}
    assert all(max(len(s.seed.proposal.side_a.sends),len(s.seed.proposal.side_b.sends))<=2 for s in seeds)


def test_large_packages_keep_faab_variants_mutually_exclusive():
    a=inventory('a',players=4,picks=2)
    a=a.model_copy(update={'assets':a.assets+tuple(FaabAsset(amount=x) for x in (5,10,15))})
    seeds,_=generate_strategic_packages((StrategicPackageLane('mixed',a,inventory('b')),),as_of=NOW,
        bounds=StrategicSearchBounds(max_candidates=160))
    assert all(sum(isinstance(x,FaabAsset) for x in s.seed.proposal.side_a.sends)<=1 for s in seeds)


def test_screen_diversity_does_not_override_economic_priority():
    def row(n,positive):
        return {'counterparty_team_id':'b','hypotheses':['same'],'send':[{'asset_ref':f'player:p{i}'} for i in range(n)],
            'receive':[{'asset_ref':'pick:k'}], 'pre_cut_horizon_complement_hypothesis':positive}
    rows=[row(1,True),row(8,False),row(4,True)]
    assert _representative_indices(rows,2)==[0,2]
    assert _representative_indices([row(1,True),row(1,True),row(8,True)],2)==[0,1]  # novelty of size does not earn priority


@pytest.mark.parametrize('superflex',[False,True])
def test_large_trade_center_api_accounts_for_all_mandatory_cuts(monkeypatch,superflex):
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    runtime,record=governed_runtime_fixture(superflex=superflex)
    state=runtime.league_state;before=state.model_dump_json()
    store=PrivateBetaRuntimeStore();store.set_league_state(runtime.user_id,state);store.select_team(runtime.user_id,'t0')
    # Populate the same already-owned Forecast/Value evidence used by the fixture.
    store.set_forecast_evidence(runtime.user_id,runtime.forecast_evidence)
    runtime.value_evidence.league_state_id=state.state_id
    store.set_value_evidence(runtime.user_id,runtime.value_evidence)
    store.bind_publication_generation_id(runtime.user_id,runtime.publication_generation_id)
    def provider(context,proposal,result):
        return build_trade_intrinsic_evidence(context,proposal,record=record,publication_validator=lambda c,r:True,
            roster_resolutions=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality']))
    client=TestClient(create_app(runtime_store=store,trade_horizon_evidence_provider=provider))
    response=client.post('/api/trade-center/analyze',json={'counterparty_team_id':'t1',
        'focal_asset_refs':[f'player:t0-{i}' for i in range(8)],'counterparty_asset_refs':[f'player:t1-{i}' for i in range(2)]})
    assert response.status_code==200,response.text
    result=response.json()
    assert sum(r['required_cut_count'] for r in result['roster_legality'])==6
    raw=result['horizon_asset_economics']
    assert raw['status']=='complete'
    assert raw['career']['roster_adjusted']['side_b']['status']=='complete'
    side=raw['career']['roster_adjusted']['side_b']
    assert len(side['cut_player_ids'])==6
    assert side['roster_adjusted_intrinsic_delta']==pytest.approx(side['raw_trade_intrinsic_delta']-side['mandatory_cut_intrinsic_cost'])
    assert result['decision_completeness']['simulation_backed'] is False
    assert state.model_dump_json()==before


def test_large_search_preserves_protection_targets_and_bounded_screens():
    runtime,record=governed_runtime_fixture()
    read=read_published_trade_horizon_values(runtime,player_ids=frozenset(p.player_id for p in runtime.league_state.players),
        record=record,publication_validator=lambda c,r:True)
    request=StrategicDiscoveryRequest(counterparty_team_id='t1',target_position='WR',offered_asset_ref='player:t0-2',
        max_candidates=40,evaluation_budget=4,search_instructions={'objectives':['three_year_contribution'],'protected_player_ids':['t0-0']})
    result=build_strategic_discovery(runtime,request,read=read)
    rows=result['candidate_packages'];positions={p.player_id:p.position.value for p in runtime.league_state.players}
    assert rows and any(len(r['send'])>2 or len(r['receive'])>2 for r in rows)
    for row in rows:
        assert 'player:t0-2' in [a['asset_ref'] for a in row['send']]
        assert 'player:t0-0' not in [a['asset_ref'] for a in row['send']]
        assert all(a['asset_ref'].startswith('player:') and positions[a['asset_ref'][7:]]=='WR' for a in row['receive'])
    diag=result['diagnostics']
    assert diag['pair_visits']<=diag['max_pair_visits']<=640
    assert diag['preliminary_decision_attempts']==4 and diag['preliminary_decision_errors']==0
    assert diag['changed_state_simulation_calls']==0


def test_pick_bundle_lanes_can_reach_eight_picks_for_one_player():
    from dataclasses import replace
    from fsffl.product.strategic_discovery import build_discovery_lanes
    from fsffl.state.models import DraftPick,PickOwnership
    runtime,_=governed_runtime_fixture();state=runtime.league_state
    picks=tuple(DraftPick(pick_id=f'{t.team_id}:{year}:{round_number}',league_id='fixture',season=year,
        round=round_number,original_team_id=t.team_id) for t in state.teams for year in (2027,2028,2029) for round_number in (1,2,3))
    state=state.model_copy(update={'draft_picks':picks,'pick_ownership':tuple(
        PickOwnership(pick_id=p.pick_id,owner_team_id=p.original_team_id) for p in picks)})
    runtime=replace(runtime,league_state=state)
    lanes,*_=build_discovery_lanes(runtime,StrategicDiscoveryRequest(counterparty_team_id='t1'),None)
    bundle_lanes=tuple(l for l in lanes if l.name in ('spend_draft_capital','acquire_draft_capital'))
    assert len(bundle_lanes)==2
    seeds,_=generate_strategic_packages(bundle_lanes,as_of=state.as_of,bounds=StrategicSearchBounds(max_candidates=160))
    assert any(len(s.seed.proposal.side_a.sends)==1 and len(s.seed.proposal.side_b.sends)==8
        and all(isinstance(a,PickAsset) for a in s.seed.proposal.side_b.sends) for s in seeds)
    assert any(len(s.seed.proposal.side_a.sends)==8 and len(s.seed.proposal.side_b.sends)==1
        and all(isinstance(a,PickAsset) for a in s.seed.proposal.side_a.sends) for s in seeds)


def test_pick_coverage_diagnostics_follow_actual_published_native_evidence():
    from tests.test_future_pick_provisional_prior import fixture,read
    runtime,record,_,release=fixture();projection=read(runtime,record,release)
    result=build_strategic_discovery(runtime,StrategicDiscoveryRequest(max_candidates=4,evaluation_budget=0,
        target_asset_ref='pick:pick:2029:beta',search_instructions={'objectives':['career_contribution']}),read=projection)
    assert result['diagnostics']['native_pick_intrinsic_coverage']=='complete'
    assert result['diagnostics']['native_pick_intrinsic_covered_count']>=1
