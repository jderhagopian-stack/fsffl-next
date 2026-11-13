"""Live Explore constraints and browser workflow, without production league data."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from fsffl.product.strategic_discovery import StrategicDiscoveryRequest, build_strategic_discovery
from tests.test_strategic_discovery import governed_runtime_fixture, client_fixture


@pytest.mark.parametrize('superflex', [False, True])
def test_position_restriction_is_applied_before_bounded_generation(superflex):
    runtime, _ = governed_runtime_fixture(superflex=superflex)
    body = StrategicDiscoveryRequest(target_position='WR', counterparty_team_id='t1',
        search_instructions={'objectives': ['current_competitiveness'], 'protected_player_ids': ['t0-0']},
        evaluation_budget=0)
    result = build_strategic_discovery(runtime, body)
    rows = result['candidate_packages']
    positions = {p.player_id: p.position.value for p in runtime.league_state.players}
    assert rows
    assert all(r['counterparty_team_id'] == 't1' for r in rows)
    assert all(positions[a['asset_ref'].split(':')[1]] == 'WR' for r in rows for a in r['receive'])
    assert all(a['asset_ref'] != 'player:t0-0' for r in rows for a in r['send'])
    assert result['diagnostics']['pair_visits'] <= 640
    assert all(r['trade_center_request']['search_instructions'] == body.search_instructions.model_dump(mode='json') for r in rows)


def test_position_validation_uses_current_league_population_before_source_read(monkeypatch):
    client, runtime, _, calls = client_fixture(monkeypatch)
    assert client.post('/api/opportunities/strategic-discover', json={'target_position': 'NOT_A_POSITION'}).status_code == 422
    target = next(p for p in runtime.league_state.players if p.player_id == 'b1')
    wrong = 'WR' if target.position.value != 'WR' else 'QB'
    assert client.post('/api/opportunities/strategic-discover', json={
        'target_position': wrong, 'target_asset_ref': 'player:b1'}).status_code == 422
    assert calls == []


def test_live_explore_consumes_evidence_and_fences_stale_responses():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    harness = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const handlers={}, pending=[], requests=[],modeHandlers={};let goalHandler,protectHandler;
const goal={addEventListener:(event,fn)=>goalHandler=fn};
const protect={dataset:{seProtect:'keep'},checked:true,addEventListener:(event,fn)=>protectHandler=fn};
const host={id:'market-ns-body',isConnected:true,innerHTML:'',querySelector:s=>s==='[data-se-goal]'?goal:null,
querySelectorAll:s=>s==='[data-se-mode]'?['automatic','custom'].map(v=>({dataset:{seMode:v},addEventListener:(event,fn)=>modeHandlers[v]=fn})):s==='[data-se-protect]'?[protect]:[]};
const context={state:{route:'opportunities',context:{user_id:'u',league_id:'l',team_id:'a',state_id:'s',publication_generation_id:'g'}},
 console,Set,JSON,Promise,window:{fsfflMarketNorthStar:{activeTab:()=> 'for_you'},addEventListener:(n,f)=>handlers[n]=f},
 api:(url,options)=>{requests.push([url,options]);return new Promise((resolve,reject)=>pending.push({url,resolve,reject}));}};
vm.createContext(context);vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8'),context);
const ui=context.window.fsfflStrategicExplore;
const flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
 ui.render(host);ui.render(host);
 assert.equal(requests.filter(r=>r[0].endsWith('strategic-discover')).length,1);
 assert(!requests.some(r=>/simulate/.test(r[0])));
 assert(host.innerHTML.indexOf('Your Direction')<host.innerHTML.indexOf('Refine your search'));
 pending.find(p=>p.url.endsWith('/browser')).resolve({state_id:'s',focal_team:{team_id:'a',assets:[]},counterparties:[]});
 const old=pending.find(p=>p.url.endsWith('strategic-discover'));
 context.state.context.state_id='new';handlers['fsffl:product-context-updated']();ui.render(host);
 old.resolve({league_state_id:'s',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[{receive:[{label:'STALE'}]}]});
 await flush();assert(!host.innerHTML.includes('STALE'));
 const latest=pending.filter(p=>p.url.endsWith('strategic-discover')).at(-1);
 latest.resolve({league_state_id:'new',focal_team_id:'a',publication_generation_id:'g',candidate_packages:[]});
 await flush();assert(host.innerHTML.includes('No complete preliminary package yet'));
 ui.render(host);assert.equal(requests.filter(r=>r[0].endsWith('strategic-discover')).length,2);
 // A custom result must never become Automatic's goal source when protecting an asset.
 modeHandlers.custom();goalHandler({target:{value:'career_contribution'}});protectHandler();
 const custom=ui.run();let request=requests.at(-1);assert.equal(JSON.parse(request[1].body).search_instructions.objectives[0],'career_contribution');
 pending.filter(p=>p.url.endsWith('strategic-discover')).at(-1).resolve({league_state_id:'new',focal_team_id:'a',publication_generation_id:'g',priority_context:{objectives:['career_contribution'],explicitly_directed:true},candidate_packages:[]});await custom;
 modeHandlers.automatic();assert(!host.innerHTML.includes('Inferred direction: Build for the long term'));
 const automatic=ui.run();const autoBody=JSON.parse(requests.at(-1)[1].body);assert(!('objectives' in autoBody.search_instructions));assert.deepEqual(autoBody.search_instructions.protected_player_ids,['keep']);
 pending.filter(p=>p.url.endsWith('strategic-discover')).at(-1).resolve({league_state_id:'new',focal_team_id:'a',publication_generation_id:'g',priority_context:{objectives:['current_competitiveness'],explicitly_directed:false},candidate_packages:[]});await automatic;
 const retry=ui.run();pending.filter(p=>p.url.endsWith('strategic-discover')).at(-1).reject(Error('Intelligence work is busy'));
 await retry;assert(host.innerHTML.includes('Intelligence work is busy'));assert(host.innerHTML.includes('Your settings are preserved'));
 const next=ui.run();pending.filter(p=>p.url.endsWith('strategic-discover')).at(-1).resolve({league_state_id:'wrong',focal_team_id:'a'});
 await next;assert(host.innerHTML.includes('League intelligence changed'));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
    subprocess.run([node, '-e', harness], check=True, capture_output=True, text=True)


def test_trade_draft_preserves_instructions_for_progressive_analysis_and_clears_on_context():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    harness = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={state:{context:{league_id:'l',team_id:'a',state_id:'s'}},window:{},document:{},
qs:()=>null,qsa:()=>[],Set,JSON};vm.createContext(c);
vm.runInContext(fs.readFileSync('src/fsffl/product/static/trade_center.js','utf8'),c);
vm.runInContext(`tradeUiState.counterpartyTeamId='b';tradeUiState.focalSelected.add('player:x');tradeUiState.counterpartySelected.add('player:y');
tradeUiState.searchInstructions={objectives:['career_contribution'],protected_player_ids:['keep']};tradeUiState.searchInstructionsContextKey=tradeContextKey();`,c);
assert.equal(c.tradeDraftPayload().search_instructions.objectives[0],'career_contribution');
const before=c.tradeScopeKey();vm.runInContext(`tradeUiState.searchInstructions={objectives:['current_competitiveness']}`,c);assert.notEqual(c.tradeScopeKey(),before);
c.state.context.state_id='new';assert(!c.tradeDraftPayload().search_instructions);
const source=fs.readFileSync('src/fsffl/product/static/progressive_delivery.js','utf8');
const functionSource=source.slice(source.indexOf('function stableDraft()'),source.indexOf('function draftKey()'));
vm.runInContext(functionSource,c);c.state.context.state_id='s';assert.equal(c.stableDraft().search_instructions.objectives[0],'current_competitiveness');
c.clearTradeDraft();assert(!c.tradeDraftPayload().search_instructions);
"""
    subprocess.run([node, '-e', harness], check=True, capture_output=True, text=True)


def test_new_assets_and_integration_are_versioned_and_loaded_before_consumer():
    static = Path('src/fsffl/product/static')
    html = (static/'index.html').read_text()
    assert html.index('strategic_explore.js') < html.index('north_star_market.js')
    assert 'strategic_explore.css?v=' in html
    assert 'window.fsfflStrategicExplore.render(body,payload)' in (static/'north_star_market.js').read_text()


def test_guided_payload_passes_quick_analysis_and_bounded_frontier(monkeypatch):
    from fastapi.testclient import TestClient
    from fsffl.product.progressive_delivery_routes import install_progressive_delivery_routes
    from fsffl.product.quick_frontier_routes import install_quick_frontier_routes
    from fsffl.product.runtime import PrivateBetaRuntimeStore
    from fsffl.product.webapp import create_app, require_beta_user
    from tests.test_strategic_discovery import read_fixture
    monkeypatch.setenv('FSFFL_BETA_AUTH', '0')
    runtime, _, _, _ = read_fixture()
    store = PrivateBetaRuntimeStore()
    store.set_league_state('local-beta-user', runtime.league_state)
    store.select_team('local-beta-user', 'alpha')
    app = create_app(runtime_store=store)
    install_progressive_delivery_routes(app, runtime_store=store, require_user=require_beta_user,
        workspace_builder=lambda *a, **kw: {})
    install_quick_frontier_routes(app, runtime_store=store, require_user=require_beta_user)
    client = TestClient(app)
    body = {'counterparty_team_id': 'beta', 'focal_asset_refs': ['player:a1'],
        'counterparty_asset_refs': ['player:b1'], 'search_instructions': {
            'objectives': ['career_contribution'], 'protected_player_ids': ['a2']}}
    for route in ('quick', 'analyze', 'frontier/quick', 'frontier'):
        response = client.post('/api/trade-center/'+route, json=body)
        assert response.status_code == 200, response.text
        if 'frontier' in route:
            result = response.json()
            assert result['evaluated_count'] <= (4 if route.endswith('quick') else 24)
            assert all(a['asset'].get('player_id') != 'a2' for p in result['points'] for a in p['focal_assets'])
            assert all(p['objective_assessment']['side_a']['context']['explicitly_directed'] for p in result['points'])
        invalid = {**body, 'search_instructions': {**body['search_instructions'], 'protected_player_ids': ['a1']}}
        assert client.post('/api/trade-center/'+route, json=invalid).status_code == 422
    assert store.get('local-beta-user').league_state == runtime.league_state


def test_protection_only_api_remains_inferred_through_discovery_and_analysis(monkeypatch):
    client, runtime, _, calls = client_fixture(monkeypatch)
    response = client.post('/api/opportunities/strategic-discover', json={
        'max_candidates': 4, 'evaluation_budget': 2,
        'search_instructions': {'protected_player_ids': ['a2']}})
    assert response.status_code == 200, response.text
    result = response.json()
    assert not result['priority_context']['explicitly_directed']
    assert result['priority_context']['protected_player_ids'] == ['a2']
    for row in result['candidate_packages']:
        request = row['trade_center_request']
        assert request['search_instructions']['objectives'] is None
        assert request['search_instructions']['protected_player_ids'] == ['a2']
        assert 'player:a2' not in request['focal_asset_refs']
    analysis = client.post('/api/trade-center/analyze', json=result['candidate_packages'][0]['trade_center_request'])
    assert analysis.status_code == 200, analysis.text
    assert not analysis.json()['objective_assessment']['side_a']['context']['explicitly_directed']
