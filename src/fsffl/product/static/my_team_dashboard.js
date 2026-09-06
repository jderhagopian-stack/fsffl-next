const fsfflMyTeamState={view:null,values:null};

function myTeamEsc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function myTeamNum(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function myTeamPct(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function myTeamAge(value){if(typeof value!=='number')return'—';return Number.isInteger(value)?String(value):value.toFixed(1)}
function myTeamPanel(){return document.querySelector('#generic-screen .panel')}
function myTeamCardinalMap(){return new Map((fsfflMyTeamState.values?.fsffl_cardinal_values||[]).map(item=>[item.asset_id,item]))}
function myTeamValue(id){const row=myTeamCardinalMap().get(id);return typeof row?.score==='number'?row.score.toLocaleString(undefined,{maximumFractionDigits:0}):'—'}
function myTeamProjection(player){const obs=(player.forecasts||[]).find(item=>item.metric==='fantasy_points');return typeof obs?.distribution?.mean==='number'?obs.distribution.mean.toFixed(1):'—'}
function myTeamMarket(player){const estimate=player.value_profile?.market_price;return estimate?.scale?.scale_id==='dynasty-market-percentile'&&typeof estimate?.distribution?.mean==='number'?`${(estimate.distribution.mean*100).toFixed(1)} pct`:'—'}
function myTeamPickLabel(row){const pick=row.pick||{};const season=pick.season??'Future';const round=pick.round!=null?`R${pick.round}`:'';const original=pick.original_team_id?` · ${pick.original_team_id}`:'';return `${season} ${round}${original}`.trim()}
function myTeamRosterRows(players){return [...(players||[])].sort((a,b)=>{const aStart=a.projected_starter?0:1,bStart=b.projected_starter?0:1;if(aStart!==bStart)return aStart-bStart;return String(a.roster_slot).localeCompare(String(b.roster_slot))||a.full_name.localeCompare(b.full_name)})}

function renderMyTeamCommandCenter(){
  const panel=myTeamPanel();if(!panel)return;
  const view=fsfflMyTeamState.view;
  if(!view){panel.innerHTML='<p class="eyebrow">My Team</p><h2>Unable to load your team.</h2>';return}
  const outcome=view.utility?.competitive_outcome;
  const roster=myTeamRosterRows(view.players);
  const starters=roster.filter(player=>player.projected_starter);
  const reserves=roster.filter(player=>!player.projected_starter);
  const picks=view.draft_picks||[];
  const stateLabel=view.utility?.calculated_competitive_state&&view.utility.calculated_competitive_state!=='unknown'?view.utility.calculated_competitive_state.replaceAll('_',' '):'Not classified';
  const playerRows=roster.map(player=>`<tr><td>${myTeamEsc(player.projected_starter?(player.projected_lineup_slot||'Starter'):player.roster_slot)}</td><td><strong>${myTeamEsc(player.full_name)}</strong></td><td>${myTeamEsc(player.position)}</td><td>${myTeamAge(player.age_years)}</td><td>${myTeamProjection(player)}</td><td><strong>${myTeamValue(player.player_id)}</strong></td><td>${myTeamMarket(player)}</td></tr>`).join('');
  const pickRows=picks.length?picks.map(row=>`<tr><td><strong>${myTeamEsc(myTeamPickLabel(row))}</strong></td><td>${myTeamEsc(row.pick?.pick_id||'')}</td><td>${myTeamValue(row.pick?.pick_id)}</td></tr>`).join(''):'<tr><td colspan="3">No owned draft picks are exposed in the current team view.</td></tr>';
  panel.innerHTML=`
    <div class="panel-header"><div><p class="eyebrow">My Team</p><h2>${myTeamEsc(view.display_name)}</h2></div><span class="status-chip">Current canonical state</span></div>
    <p class="lead">Your team command center. Competitive outcomes, lineup assignments, forecasts and values below are supplied by their authoritative backend modules; this screen only organizes them.</p>
    <div class="my-team-action-row"><button type="button" class="secondary-button" data-my-team-route="trade_center">Build a trade</button><button type="button" class="secondary-button" data-my-team-route="league_comparison">Compare league</button><button type="button" class="secondary-button" data-my-team-route="analytics">Open analytics</button><button type="button" class="secondary-button" data-my-team-route="what_if">Run What-If</button></div>
    <div class="my-team-metrics">
      <div><span>Expected wins</span><strong>${myTeamNum(outcome?.expected_wins,2)}</strong><small>${outcome?`${outcome.simulation_count.toLocaleString()} simulations`:'Simulation evidence unavailable'}</small></div>
      <div><span>Playoff odds</span><strong>${myTeamPct(outcome?.playoff_probability,1)}</strong><small>First place ${myTeamPct(outcome?.first_place_probability,1)}</small></div>
      <div><span>Competitive state</span><strong class="capitalize">${myTeamEsc(stateLabel)}</strong><small>Owner posture remains separate from calculated state</small></div>
      <div><span>Projected starters</span><strong>${starters.length}</strong><small>${reserves.length} reserve / taxi / IR players shown below</small></div>
    </div>
    <div class="my-team-section"><div><p class="eyebrow">Roster & optimized lineup</p><h3>Who starts, what they project for, and what they are worth</h3></div><div class="table-wrap"><table><thead><tr><th>Role</th><th>Player</th><th>Pos</th><th>Age</th><th>Projection</th><th>FSFFL Value</th><th>Market percentile</th></tr></thead><tbody>${playerRows||'<tr><td colspan="7">No rostered players.</td></tr>'}</tbody></table></div></div>
    <div class="my-team-section"><div><p class="eyebrow">Pick inventory</p><h3>Owned draft picks</h3></div><div class="table-wrap"><table><thead><tr><th>Pick</th><th>Canonical ID</th><th>FSFFL Value</th></tr></thead><tbody>${pickRows}</tbody></table></div></div>
    <details class="technical-evidence"><summary>Evidence & model lineage</summary><div class="my-team-evidence"><p><strong>Team view:</strong> ${myTeamEsc(view.view_model_version||'—')}</p><p><strong>Utility:</strong> ${myTeamEsc(view.utility?.model_version||'—')}</p><p><strong>Simulation:</strong> ${myTeamEsc(outcome?.simulation_model_version||'—')}</p><p><strong>Value:</strong> ${myTeamEsc(fsfflMyTeamState.values?.model_version||'—')}</p><p><strong>State:</strong> ${myTeamEsc(view.context?.league_state_id||'—')}</p></div></details>`;
  panel.querySelectorAll('[data-my-team-route]').forEach(button=>button.addEventListener('click',()=>setRoute(button.dataset.myTeamRoute)));
}

async function loadMyTeamCommandCenter(){
  const panel=myTeamPanel();if(!state?.context?.team_id){if(panel)panel.innerHTML='<p class="eyebrow">My Team</p><h2>Select a team first.</h2><p class="lead">Choose the franchise you manage from the top bar.</p>';return}
  if(panel)panel.innerHTML='<p class="eyebrow">My Team</p><h2>Building your command center…</h2><p class="lead">Loading current State, Forecast, Value and Simulation evidence.</p>';
  try{const[view,values]=await Promise.all([api('/api/my-team'),state.context?.value_ready?api('/api/values').catch(()=>null):Promise.resolve(null)]);fsfflMyTeamState.view=view;fsfflMyTeamState.values=values;renderMyTeamCommandCenter()}catch(error){if(panel)panel.innerHTML=`<p class="eyebrow">My Team</p><h2>Unable to load your team.</h2><p class="lead">${myTeamEsc(error.message)}</p>`}
}

window.renderFsfflMyTeam=loadMyTeamCommandCenter;

(function installMyTeamStyles(){const style=document.createElement('style');style.textContent=`.my-team-action-row{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.my-team-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:16px 0 20px}.my-team-metrics>div{border:1px solid var(--line);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:5px}.my-team-metrics span{color:var(--muted);font-size:12px}.my-team-metrics strong{font-size:1.35rem}.my-team-metrics small{color:var(--muted);line-height:1.35}.capitalize{text-transform:capitalize}.my-team-section{margin-top:22px}.my-team-section h3{margin-top:0}.my-team-evidence{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 18px;padding-top:8px}.my-team-evidence p{overflow-wrap:anywhere}@media(max-width:760px){.my-team-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.my-team-action-row .secondary-button{flex:1 1 45%}.my-team-evidence{grid-template-columns:1fr}}@media(max-width:460px){.my-team-metrics{grid-template-columns:1fr}.my-team-action-row .secondary-button{flex:1 1 100%}}`;document.head.appendChild(style)})();