from copy import deepcopy
from fsffl.product.counter_review import review_counter


def effects(a=(-1,-80,-100),b=(2,80,100),basis='remaining_regular_season_weekly_mean'):
    return {'basis':basis,'teams':{t:dict(zip(('current','three_year','career'),values)) for t,values in [('a',a),('b',b)]}}


def test_counter_reduces_original_cost_without_weighting_horizons_or_changing_evidence():
    seed=effects();candidate=effects(a=(1,-50,-80),b=(1,50,80));original=deepcopy(candidate)
    review=review_counter(seed,candidate,display_group='priority_tradeoff')
    assert review['status']=='improves_terms'
    assert {r['metric'] for r in review['improved']}=={'current','three_year','career'}
    assert next(r for r in review['improved'] if r['metric']=='current')['resolved']
    assert candidate==original
    assert review['decision_effect']=='no_disposition_change' and not review['simulation_backed']


def test_new_or_deeper_cost_remains_visible_even_when_other_cost_is_repaired():
    seed=effects()
    review=review_counter(seed,effects(a=(1,-50,-80),b=(-1,50,80)),display_group='priority_tradeoff')
    assert review['status']=='tradeoff'
    assert review['new_losses']==[{'team_id':'b','metric':'current','before':2,'after':-1}]
    assert review_counter(seed,effects(a=(-2,-50,-80)),display_group='priority_tradeoff')['worsened']
    assert review_counter(seed,effects(a=(1,1,1)),display_group='priority_concern')['status']=='needs_work'


def test_missing_or_different_current_units_cannot_be_promoted_to_improved_terms():
    seed=effects()
    assert review_counter(seed,effects(a=(1,None,2)),display_group='preliminary_fit')['status']=='incomplete'
    assert review_counter(seed,effects(basis='optimized_horizon_lineup'),display_group='preliminary_fit')['status']=='incomplete'


def test_quick_and_deep_routes_reuse_one_published_read_and_existing_screen(monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app,_build_default_simulation
    from fsffl.product.quick_frontier_routes import install_quick_frontier_routes
    from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
    from fsffl.product.intrinsic_background import IntrinsicBuildStatus
    from tests.test_simulation_ros_inputs import fixture,market
    from tests.test_dynasty_position_room import _career_current_components
    from fsffl.state.models import Position
    import fsffl.product.frontier_runtime as frontier
    monkeypatch.setenv('FSFFL_BETA_AUTH','0')
    state,forecast=fixture()
    baseline=_build_default_simulation(state,forecast,simulation_count=100)
    contract=_career_current_components(state,{'starter':(10.,20.,30.),'bench':(20.,30.,40.),'opp':(30.,40.,50.)},positions={p.player_id:Position.QB for p in state.players})
    contract=contract.model_copy(update={'estimates':tuple(r.model_copy(update={'long_horizon_raw_y4_y7_reference':800.,'terminal_raw_y8_plus_reference':200.}) for r in contract.estimates)})
    record=SimpleNamespace(user_id='local-beta-user',league_state_id=state.state_id,status=IntrinsicBuildStatus.COMPLETED,contract=contract,intrinsic_input_fingerprint='fixture')
    store=PrivateBetaRuntimeStore();store.set_league_state(record.user_id,state);store.select_team(record.user_id,'a')
    store.set_forecast_evidence(record.user_id,forecast);store.set_simulation_analytics(record.user_id,baseline)
    store.set_value_evidence(record.user_id,market(state));store.bind_publication_generation_id(record.user_id,'g1')
    reads=[]
    def provider(runtime,ids):
        reads.append(ids)
        return read_published_trade_horizon_values(runtime,player_ids=ids,record=record,publication_validator=lambda c,r:True)
    def forbidden(*a,**k):raise AssertionError('Counter search must not run the old analysis or a new Simulation')
    monkeypatch.setattr(frontier,'build_private_beta_trade_analysis',forbidden)
    app=create_app(runtime_store=store,discovery_horizon_provider=provider,simulation_loader=forbidden)
    install_quick_frontier_routes(app,runtime_store=store,require_user=lambda:'local-beta-user',horizon_provider=provider)
    client=TestClient(app)
    payload={'counterparty_team_id':'b','focal_asset_refs':['player:starter'],'counterparty_asset_refs':['player:opp'],
        'search_instructions':{'objectives':['career_contribution']}}
    for route,bound in (('/api/trade-center/frontier/quick',4),('/api/trade-center/frontier',24)):
        response=client.post(route,json=payload)
        assert response.status_code==200,response.text
        body=response.json()
        assert body['evaluated_count']<=bound
        assert body['authority']['published_native_context']
        assert body['authority']['targeted_substitutions']
        assert body['policy']['include_substitutions']
        assert not body['authority']['search_hints_are_transaction_effects']
        assert all(any(a['asset'].get('player_id') == 'opp' for a in p['counterparty_assets']) for p in body['points'])
        assert any([a['asset'].get('player_id') for a in p['focal_assets']] == ['bench'] for p in body['points'])
        assert all(p['counter_review']['effects']['basis']=='remaining_regular_season_weekly_mean' for p in body['points'])
        assert all(p['objective_assessment']['side_a']['context']['explicitly_directed'] for p in body['points'])
        assert all(p['action_authority']=='diagnostic_only' for p in body['points'])
    protected = client.post('/api/trade-center/frontier/quick', json={**payload,
        'search_instructions':{'objectives':['career_contribution'],'protected_player_ids':['bench']}})
    assert protected.status_code == 200, protected.text
    assert all(all(a['asset'].get('player_id') != 'bench' for a in p['focal_assets'])
        for p in protected.json()['points'])
    assert len(reads)==3  # Once per request, not once per candidate.
    assert reads[0]==frozenset(p.player_id for p in state.players)


def test_current_roundoff_uses_existing_screen_tolerance_without_hiding_native_losses():
    result=review_counter(effects(a=(0,-80,-100)),effects(a=(-1e-12,-50,-80)),display_group='priority_tradeoff')
    assert result['status']=='improves_terms' and not result['new_losses']
    result=review_counter(effects(a=(0,0,-100)),effects(a=(0,-1e-12,-80)),display_group='priority_tradeoff')
    assert result['status']=='tradeoff' and result['new_losses'][0]['metric']=='three_year'
