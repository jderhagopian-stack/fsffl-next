const fsfflSimulatorState={selected:new Set(),team:null,result:null,loading:false};

function simulatorFmtNumber(value,digits=2){
  if(typeof value!=='number'||!Number.isFinite(value))return'—';
  const text=value.toFixed(digits);
  return value>0?`+${text}`:text;
}
function simulatorFmtPctPoint(value){return typeof value==='number'&&Number.isFinite(value)?`${simulatorFmtNumber(value*100,1)} pp`:'—'}
function simulatorPlayers(){
  const team=fsfflSimulatorState.team;
  if(!team)return[];
  return (team.players||[]).filter(row=>!['ir','taxi'].includes(String(row.roster_slot||'').toLowerCase()));
}
function simulatorToggle(playerId){
  fsfflSimulatorState.selected.has(playerId)?fsfflSimulatorState.selected.delete(playerId):fsfflSimulatorState.selected.add(playerId);
  fsfflSimulatorState.result=null;
  renderFsfflSimulator();
}
function simulatorMetricCard(label,value,note=''){
  return `<div class="metric-card"><span class="metric-label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${note?`<small>${escapeHtml(note)}</small>`:''}</div>`;
}
function simulatorScenarioResult(result){
  if(!result)return'';
  const competitive=result.team_delta?.competitive||{};
  const resilience=result.team_delta?.resilience||{};
  const names=(result.player_names||result.players?.map(item=>item.player_name)||[]).join(', ');
  const cacheLabel=result.scenario_cache_hit?'Exact scenario reused':'Fresh scenario run';
  return `<article class="panel" style="margin-top:16px">
    <div class="panel-header"><div><p class="eyebrow">Scenario result</p><h2>${escapeHtml(names||'Availability stress test')}</h2><p class="lead">Compared with the current authoritative baseline.</p></div><div style="display:flex;gap:8px;flex-wrap:wrap"><span class="status-chip">${escapeHtml(cacheLabel)}</span><span class="status-chip">${Number(result.scenario_simulation_count||0).toLocaleString()} simulations</span></div></div>
    <div class="metric-grid">
      ${simulatorMetricCard('Expected wins',simulatorFmtNumber(competitive.expected_wins,2),'Scenario minus baseline')}
      ${simulatorMetricCard('Playoff odds',simulatorFmtPctPoint(competitive.playoff_probability),'Scenario minus baseline')}
      ${simulatorMetricCard('Championship odds',simulatorFmtPctPoint(competitive.championship_probability),'Scenario minus baseline')}
      ${simulatorMetricCard('Largest lineup-loss exposure',simulatorFmtNumber(resilience.largest_single_player_lineup_drop,2),'Scenario minus baseline')}
    </div>
    <div class="panel" style="margin-top:14px;background:var(--surface-2)"><strong>Calculated state</strong><p style="margin:6px 0 0">${escapeHtml(result.calculated_state_before||'—')} → <strong>${escapeHtml(result.calculated_state_after||'—')}</strong></p></div>
    <p style="color:var(--muted);font-size:12px;margin:12px 0 0">Ownership and FSFFL Value remain unchanged. State owns the hypothetical availability change; NEXT-4 Simulation owns competitive outcomes. Cache reuse is exact-result performance reuse only.</p>
  </article>`;
}
async function runFsfflSimulator(){
  const playerIds=[...fsfflSimulatorState.selected];
  if(!playerIds.length||fsfflSimulatorState.loading)return;
  fsfflSimulatorState.loading=true;renderFsfflSimulator();
  try{
    const envelope=`simulator:${playerIds.join(',')}`;
    fsfflSimulatorState.result=await api('/api/what-if/player-unavailable',{method:'POST',body:JSON.stringify({player_id:envelope})});
  }catch(error){fsfflSimulatorState.result={error:error.message}}
  finally{fsfflSimulatorState.loading=false;renderFsfflSimulator()}
}
async function loadFsfflSimulator(){
  if(!state?.context?.team_id){fsfflSimulatorState.team=null;renderFsfflSimulator();return}
  try{fsfflSimulatorState.team=await api('/api/my-team')}catch(_error){fsfflSimulatorState.team=null}
  renderFsfflSimulator();
}
function renderFsfflSimulator(){
  const panel=document.querySelector('#generic-screen .panel');
  if(!panel)return;
  if(!state?.context?.team_id){panel.innerHTML='<p class="eyebrow">Simulator</p><h2>Select your team first.</h2><p class="lead">The Simulator runs governed hypothetical States for the franchise you manage.</p>';return}
  const players=simulatorPlayers();
  const selected=fsfflSimulatorState.selected;
  const result=fsfflSimulatorState.result;
  panel.innerHTML=`<p class="eyebrow">Simulator</p><h2>Stress-test multiple roster losses.</h2><p class="lead">Choose one or more active-roster players to make unavailable simultaneously. FSFFL creates one hypothetical State and runs the exact scenario through authoritative 50,000-run Simulation.</p>
    <div class="panel" style="margin-top:16px"><div class="panel-header"><div><strong>Players unavailable in scenario</strong><p style="color:var(--muted);font-size:12px;margin:5px 0 0">${selected.size} selected</p></div><button id="run-simulator" class="primary-button" ${!selected.size||fsfflSimulatorState.loading?'disabled':''}>${fsfflSimulatorState.loading?'Simulating…':'Run scenario'}</button></div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-top:14px">${players.map(row=>`<button type="button" class="asset-option${selected.has(row.player_id)?' selected':''}" data-sim-player="${escapeHtml(row.player_id)}"><span><strong>${escapeHtml(row.display_name||row.player_name||row.player_id)}</strong><small>${escapeHtml(row.position||'')} · ${escapeHtml(row.roster_slot||'active')}</small></span></button>`).join('')}</div></div>
    ${result?.error?`<div class="chart-empty" style="margin-top:14px"><p>Simulator is unavailable: ${escapeHtml(result.error)}</p></div>`:simulatorScenarioResult(result)}`;
  panel.querySelectorAll('[data-sim-player]').forEach(button=>button.addEventListener('click',()=>simulatorToggle(button.dataset.simPlayer)));
  panel.querySelector('#run-simulator')?.addEventListener('click',runFsfflSimulator);
}
window.renderFsfflSimulator=function(){renderFsfflSimulator();if(state?.context?.team_id&&!fsfflSimulatorState.team)loadFsfflSimulator()};
