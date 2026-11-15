"""Exercise real browser handoff/draft functions with large mixed packages."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_large_mixed_handoff_keeps_all_refs_priorities_and_rejects_stale_evidence():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const banners=[],requests=[];
const send=Array.from({length:8},(_,i)=>({asset_ref:(i<4?'player:':'pick:')+'a'+i,label:'Outgoing '+i}));
const receive=[{asset_ref:'player:b1',label:'Incoming player'},{asset_ref:'pick:b2',label:'Incoming pick'}];
const browser={state_id:'s',focal_team:{team_id:'a',assets:send},counterparties:[{team_id:'b',assets:receive}]};
const anchor={insertAdjacentElement:(_,node)=>banners.push(node)};
const document={head:{appendChild:()=>{}},documentElement:{},querySelector:selector=>selector.includes('trade-counterparty-row')?anchor:null,
createElement:()=>({querySelector:()=>null}),querySelectorAll:()=>[]};
const c={state:{route:'opportunities',context:{league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},
window:{},document,qs:()=>null,qsa:()=>[],Set,JSON,Promise,console,MutationObserver:class{observe(){}disconnect(){}},
setRoute:route=>c.state.route=route,api:async(path,options)=>{requests.push({path,options});if(path.endsWith('/browser'))return browser;return {state_id_before:'s',focal_team_id:'a',counterparty_team_id:'b'};}};
vm.createContext(c);vm.runInContext(fs.readFileSync('src/fsffl/product/static/trade_center.js','utf8'),c);
vm.runInContext(fs.readFileSync('src/fsffl/product/static/trade_workflow_handoff.js','utf8'),c);
const row={counterparty_team_id:'b',league_state_id:'s',publication_generation_id:'g',send,receive,
trade_center_request:{search_instructions:{objectives:['current_competitiveness','career_contribution'],protected_player_ids:['keep']}}};
(async()=>{
 await c.window.fsfflOpenOpportunityInTradeCenter(row);
 assert.equal(c.state.route,'trade_center');
 c.renderTradeAnalysis=()=>{};c.renderTradeSimulationResult=()=>{};c.renderTradeFrontierResult=()=>{};
 const payload=c.tradeDraftPayload();
 assert.deepEqual(Array.from(payload.focal_asset_refs),send.map(a=>a.asset_ref));
 assert.deepEqual(Array.from(payload.counterparty_asset_refs),receive.map(a=>a.asset_ref));
 assert.equal(JSON.stringify(payload.search_instructions),JSON.stringify(row.trade_center_request.search_instructions));
 assert(banners.at(-1).innerHTML.includes('8 sent · 2 received'));
 assert(banners.at(-1).innerHTML.includes('Win now · Career'));
 // Loading ownership, sorting the progressive draft, and subsequent edits must not truncate a package.
 const source=fs.readFileSync('src/fsffl/product/static/progressive_delivery.js','utf8');
 vm.runInContext(source.slice(source.indexOf('function stableDraft()'),source.indexOf('function draftKey()')),c);
 assert.equal(c.stableDraft().focal_asset_refs.length,8);
 assert.equal(JSON.stringify(c.stableDraft().search_instructions),JSON.stringify(payload.search_instructions));
 for(const action of ['analyzeTradeDraft','simulateTradeDraft','exploreTradeFrontier'])await c[action]();
 for(const request of requests.filter(r=>r.options)){const posted=JSON.parse(request.options.body);assert.equal(posted.focal_asset_refs.length,8);assert.equal(posted.counterparty_asset_refs.length,2);assert.equal(JSON.stringify(posted.search_instructions),JSON.stringify(payload.search_instructions));}
 assert.equal(requests.filter(r=>r.options).length,3);
 // The copy handed to Trade Center cannot be mutated by a later Explore change.
 row.trade_center_request.search_instructions.objectives.length=0;
 assert.equal(c.tradeDraftPayload().search_instructions.objectives.length,2);
 c.clearTradeDraft();
 for(const stale of [{league_state_id:'old'},{publication_generation_id:'old'}]){
   await c.window.fsfflOpenOpportunityInTradeCenter({...row,...stale});
   assert(!c.tradeDraftPayload().focal_asset_refs.length);
   assert(!c.tradeDraftPayload().search_instructions);
   assert(banners.at(-1).innerHTML.includes('This opportunity is no longer current'));
 }
 // A refreshed ownership response missing just one of the eight assets rejects the whole transfer.
 browser.focal_team.assets=send.slice(0,7);
 await c.window.fsfflOpenOpportunityInTradeCenter(row);
 assert(!c.tradeDraftPayload().focal_asset_refs.length);
 assert(!c.tradeDraftPayload().counterparty_asset_refs.length);
 assert(!c.tradeDraftPayload().search_instructions);
 assert(banners.at(-1).innerHTML.includes('This opportunity is no longer current'));
})().catch(e=>{console.error(e);process.exitCode=1});
"""
    result = subprocess.run([node, '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _assert_large_mixed_analysis(superflex):
    from fastapi.testclient import TestClient
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app
    from fsffl.product.trade_intrinsic_evidence import build_trade_intrinsic_evidence
    from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
    from tests.test_strategic_discovery import governed_runtime_fixture

    import os
    os.environ['FSFFL_BETA_AUTH'] = '0'
    runtime, record = governed_runtime_fixture(superflex=superflex)
    state = runtime.league_state
    before = state.model_dump_json()
    store = PrivateBetaRuntimeStore()
    store.set_league_state(runtime.user_id, state)
    store.select_team(runtime.user_id, 't0')
    store.set_forecast_evidence(runtime.user_id, runtime.forecast_evidence)
    runtime.value_evidence.league_state_id = state.state_id
    store.set_value_evidence(runtime.user_id, runtime.value_evidence)
    store.bind_publication_generation_id(runtime.user_id, runtime.publication_generation_id)

    def provider(context, proposal, result):
        return build_trade_intrinsic_evidence(context, proposal, record=record,
            publication_validator=lambda c, r: True,
            roster_resolutions=tuple(TeamRosterLegalityResolution.model_validate(r) for r in result['roster_legality']))

    client = TestClient(create_app(runtime_store=store, trade_horizon_evidence_provider=provider))
    body = {'counterparty_team_id': 't1',
        'focal_asset_refs': [f'player:t0-{i}' for i in range(7)] + ['pick:pick-t0'],
        'counterparty_asset_refs': ['player:t1-0', 'pick:pick-t1'],
        'search_instructions': {'objectives': ['current_competitiveness', 'career_contribution'],
            'protected_player_ids': ['t0-13']}}
    response = client.post('/api/trade-center/analyze', json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    context = result['objective_assessment']['side_a']['context']
    assert context['objectives'] == body['search_instructions']['objectives']
    assert context['protected_player_ids'] == ['t0-13']
    assert context['explicitly_directed']
    assert sum(r['required_cut_count'] for r in result['roster_legality']) == 6
    assert result['roster_adjusted_market_net']['side_b']['required_cut_count'] == 6
    assert result['decision_completeness']['simulation_backed'] is False
    # Missing native pick evidence in this fixture must remain unavailable, never zero-filled.
    assert result['horizon_asset_economics']['status'] != 'complete'
    # Exercise a mixed larger package actually emitted by discovery through the same API.
    from fsffl.product.strategic_discovery import build_strategic_discovery, StrategicDiscoveryRequest
    from fsffl.product.trade_intrinsic_evidence import read_published_trade_horizon_values
    read = read_published_trade_horizon_values(runtime,
        player_ids=frozenset(p.player_id for p in state.players), record=record,
        publication_validator=lambda c, r: True)
    discovery = build_strategic_discovery(runtime, StrategicDiscoveryRequest(
        max_candidates=80, evaluation_budget=0, search_instructions=body['search_instructions']), read=read)
    candidate = next(row for row in discovery['candidate_packages']
        if max(len(row['send']), len(row['receive'])) > 2
        and any(a['asset_ref'].startswith('pick:') for a in row['send'] + row['receive'])
        and any(a['asset_ref'].startswith('player:') for a in row['send'] + row['receive']))
    transferred = client.post('/api/trade-center/analyze', json=candidate['trade_center_request'])
    assert transferred.status_code == 200, transferred.text
    transferred_context = transferred.json()['objective_assessment']['side_a']['context']
    assert transferred_context['objectives'] == context['objectives']
    assert transferred_context['protected_player_ids'] == context['protected_player_ids']
    assert state.model_dump_json() == before


@pytest.mark.parametrize('superflex', [False, True])
def test_large_mixed_analysis_keeps_combined_priorities_and_complete_cut_accounting(superflex):
    # App/Forecast fixtures run in a fresh process: unrelated full-suite allocations
    # must not contaminate the production 512 MB admission guard exercised later.
    # The child still uses the real unchanged resource guard and analysis API.
    import sys
    result = subprocess.run([sys.executable, '-c',
        'from tests.test_compact_trade_workflow import _assert_large_mixed_analysis; '
        f'_assert_large_mixed_analysis({superflex!r})'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
