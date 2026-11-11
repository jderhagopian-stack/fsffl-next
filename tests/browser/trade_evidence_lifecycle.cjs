// Run the production scripts with deferred transport; no server/model replacements
// are used to decide whether a response belongs to the current draft.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../src/fsffl/product/static');
const flush = () => new Promise(resolve => setImmediate(resolve));
function fixture() {
  const nodes = new Map();
  const node = () => ({innerHTML: '', textContent: '', disabled: false,
    addEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    appendChild() {}, remove() {}, setAttribute() {}, classList: {add() {}}});
  for (const id of ['#analyze-trade', '#simulate-trade', '#explore-price',
    '#trade-analysis-empty', '#trade-simulation-result', '#trade-frontier-result', '#focal-assets']) nodes.set(id, node());
  const calls = [], renders = [];
  const c = vm.createContext({console, Set, Promise, setTimeout, clearTimeout,
    state: {context: {league_id: 'l', team_id: 'a', state_id: 's1', publication_generation_id: 'g1'}, route: 'trade_center'},
    qs: s => nodes.get(s) || null, qsa: () => [], escapeHtml: String,
    document: {querySelector: s => nodes.get(s) || null, querySelectorAll: () => [],
      createElement: node, addEventListener() {}, head: node(), documentElement: node()},
    MutationObserver: class {observe() {}}, requestAnimationFrame() {},
    api: (url, options) => new Promise((resolve, reject) => calls.push({url, options, resolve, reject})),
  });
  nodes.get('#trade-analysis-empty').querySelector = selector => ['#trade-simulation-result', ':scope > div'].includes(selector) ? node() : null;
  c.window = c;
  const run = source => vm.runInContext(source, c);
  const load = name => run(fs.readFileSync(path.join(root, name), 'utf8'));
  load('trade_center.js');
  run(`tradeUiState.browser={state_id:'s1',focal_team:{team_id:'a',assets:[{asset_ref:'p1'}]},counterparties:[{team_id:'b',assets:[{asset_ref:'p2'},{asset_ref:'p3'}]}]};
    tradeUiState.counterpartyTeamId='b';tradeUiState.focalSelected=new Set(['p1']);tradeUiState.counterpartySelected=new Set(['p2']);`);
  c.renderTradeSimulationResult = r => renders.push(['simulation', r.tag]);
  c.renderTradeAnalysis = r => renders.push(['analysis', r.tag]);
  c.renderTradeFrontierResult = r => renders.push(['frontier', r.tag]);
  for (const name of ['ensureTradeFilters', 'renderTradeCounterparties', 'renderTradeDraftSide', 'renderTradeAssetList']) c[name] = () => {};
  const result = tag => ({tag, state_id_before: 's1', focal_team_id: 'a', counterparty_team_id: 'b', scenario_simulation_count: 50000});
  return {c, run, load, nodes, calls, renders, result};
}
async function requests() {
  for (const action of ['simulateTradeDraft', 'analyzeTradeDraft', 'exploreTradeFrontier']) {
    for (const change of ["tradeUiState.counterpartySelected=new Set(['p3']);invalidateTradeScenario()",
      "state.context.team_id='c'", "state.context.state_id='s2'", "state.context.publication_generation_id='g2'",
      "tradeUiState.counterpartySelected=new Set(['p3']);invalidateTradeScenario();tradeUiState.counterpartySelected=new Set(['p2']);invalidateTradeScenario()"] ) {
      const f = fixture(), pending = f.c[action]();
      f.run(change); f.calls[0].resolve(f.result('stale')); await pending;
      assert.deepEqual(f.renders, [], `${action}: stale result after ${change}`);
    }
    const f = fixture(), old = f.c[action](), newer = f.c[action]();
    f.calls[1].resolve(f.result('new')); await newer;
    f.calls[0].reject(new Error('late failure')); await old;
    assert.deepEqual(f.renders, [[action === 'simulateTradeDraft' ? 'simulation' : action === 'analyzeTradeDraft' ? 'analysis' : 'frontier', 'new']]);
    const bad = fixture(), pending = bad.c[action]();
    bad.calls[0].resolve({...bad.result('wrong'), state_id_before: 's2'}); await pending;
    assert.deepEqual(bad.renders, []);
    assert.ok([...bad.nodes.values()].some(n => (n.innerHTML + n.textContent).includes('League data changed')));
  }
}
async function counters() {
  const f = fixture(); f.load('quick_counter_frontier.js');
  const first = f.c.exploreTradeFrontier(); f.calls[0].resolve({...f.result('quick'), deeper_search_available: true}); await first;
  assert.deepEqual(f.renders, [['frontier', 'quick']]);
  const deeper = f.c.fsfflExploreDeepFrontier();
  assert.equal(f.calls[1].url, '/api/trade-center/frontier');
  f.calls[1].resolve(f.result('deep')); await deeper;
  assert.deepEqual(f.renders.at(-1), ['frontier', 'deep']);
  for (const stage of ['quick', 'deep']) {
    const g = fixture(); g.load('quick_counter_frontier.js');
    let pending = g.c.exploreTradeFrontier();
    if (stage === 'deep') {g.calls[0].resolve(g.result('quick')); await pending; pending = g.c.fsfflExploreDeepFrontier();}
    const count = g.renders.length;
    g.run("tradeUiState.counterpartySelected=new Set(['p3']);invalidateTradeScenario()");
    g.calls.at(-1).resolve(g.result('stale')); await pending;
    assert.equal(g.renders.length, count);
    const before = g.calls.length; await g.c.fsfflExploreDeepFrontier(); assert.equal(g.calls.length, before);
  }
  const g = fixture(); g.load('quick_counter_frontier.js');
  const a = g.c.exploreTradeFrontier(), b = g.c.exploreTradeFrontier();
  g.calls[1].resolve(g.result('new')); await b; g.calls[0].reject(new Error('old')); await a;
  assert.deepEqual(g.renders, [['frontier', 'new']]);
}
async function browsers() {
  const f = fixture();
  const a = f.c.loadTradeCenter(); assert.equal(f.c.loadTradeCenter(), a, 'same-context load is joined');
  await flush();
  f.run("state.context.team_id='c';state.context.state_id='s2'");
  const b = f.c.loadTradeCenter(); await flush();
  const browser = {state_id: 's2', focal_team: {team_id: 'c', assets: []}, counterparties: []};
  f.calls[1].resolve(browser); await b;
  f.calls[0].resolve({state_id: 's1', focal_team: {team_id: 'a', assets: []}, counterparties: []}); await a;
  assert.equal(f.run('tradeUiState.browser.focal_team.team_id'), 'c');
  assert.equal(f.run('tradeUiState.loading'), false);
  const g = fixture(); g.run('tradeUiState.browser=null');
  const pending = g.c.loadTradeCenter(); await flush();
  g.calls[0].resolve(browser); await pending;
  assert.equal(g.run('tradeUiState.browser'), null);
  assert.match(g.nodes.get('#focal-assets').innerHTML, /League data changed/);
}
async function handoffs() {
  const f = fixture();
  // UI render functions remain spies; load/adopt the actual handoff controller.
  f.run("fsfflTradeWorkflowHandoff={packageKey:'b:p1:p2',stateId:'s1',contextKey:tradeContextKey()}");
  f.load('north_star_trade_center.js');
  assert.equal(f.c.fsfflAdoptHandoffSimulation({...f.result('bad'), state_id_before: 's2'}), false);
  assert.equal(f.c.fsfflAdoptHandoffSimulation({...f.result('missing'), state_id_before: undefined}), false);
  assert.equal(f.c.fsfflAdoptHandoffSimulation(f.result('valid')), true);
  f.run("state.context.publication_generation_id='g2'");
  assert.equal(f.c.fsfflAdoptHandoffSimulation(f.result('stale generation')), false);

  const g = fixture(); g.run('tradeUiState.browser=null');
  g.c.fsfflOpportunityState = {payload: {league_state_id: 's1'}, tradeEvaluationKey: 'b:p1:p2', tradeEvaluation: g.result('carried')};
  const adopted = []; g.c.fsfflAdoptHandoffSimulation = r => adopted.push(r.tag);
  g.load('trade_workflow_handoff.js');
  const row = {counterparty_team_id: 'b', send: [{asset_ref: 'p1'}], receive: [{asset_ref: 'p2'}]};
  // A prior navigation already owns a slow load. Opening two handoffs must join it.
  const load = g.c.loadTradeCenter(); await flush();
  const obsolete = g.c.fsfflOpenOpportunityInTradeCenter({...row, send: [{asset_ref: 'not-owned'}]});
  const current = g.c.fsfflOpenOpportunityInTradeCenter(row);
  let settled = false; current.then(() => settled = true);
  await new Promise(resolve => setTimeout(resolve, 2600));
  assert.equal(settled, false, 'handoff waits for actual load, not a polling timeout');
  assert.equal(g.calls.length, 1, 'browser load coalesced');
  g.calls[0].resolve({state_id: 's1', focal_team: {team_id: 'a', assets: [{asset_ref: 'p1'}]}, counterparties: [{team_id: 'b', assets: [{asset_ref: 'p2'}]}]});
  await Promise.all([load, obsolete, current]);
  assert.deepEqual(adopted, ['carried'], 'fresh Trade Center reuses the exact simulation once');
  assert.equal(g.run("tradeUiState.focalSelected.has('p1')"), true, 'obsolete handoff cannot clear new draft');
  assert.equal(g.calls.filter(c => c.url.includes('simulate')).length, 0);
}
(async () => {
  await requests(); await counters(); await browsers(); await handoffs();
  console.log('trade evidence lifecycle: passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
