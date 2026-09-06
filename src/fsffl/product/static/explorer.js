const fsfflExplorerState={assetRows:[],teamRows:[],assetSort:{key:'value',direction:'desc'},teamSort:{key:'expected_wins',direction:'desc'}};

function explorerNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function explorerPercent(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function explorerValue(value){return typeof value==='number'&&Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:0}):'—'}
function explorerEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function explorerPanel(){return document.querySelector('#generic-screen .panel')}
function explorerCompare(a,b){if(a==null&&b==null)return 0;if(a==null)return 1;if(b==null)return-1;if(typeof a==='number'&&typeof b==='number')return a-b;return String(a).localeCompare(String(b),undefined,{numeric:true,sensitivity:'base'})}
function explorerSorted(rows,sort){return[...rows].sort((a,b)=>{const result=explorerCompare(a[sort.key],b[sort.key]);return sort.direction==='asc'?result:-result})}
function explorerSortButton(label,key,sort){const active=sort.key===key;const arrow=active?(sort.direction==='asc'?' ↑':' ↓'):'';return`<button type="button" class="text-button explorer-sort" data-sort-key="${key}">${explorerEscape(label)}${arrow}</button>`}
function explorerMetricValue(metric,value){if(value==null)return'—';if(metric==='playoff_probability')return explorerPercent(value,1);if(metric==='expected_wins')return explorerNumber(value,2);if(metric==='optimized_expected_points')return explorerNumber(value,1);if(metric==='asset_portfolio_mean')return typeof value==='number'?`${explorerNumber(value*100,1)} pct`:'—';if(metric==='draft_pick_count')return explorerNumber(value,0);return explorerNumber(value,2)}

function setExplorerLoading(eyebrow,title,copy){const panel=explorerPanel();if(!panel)return;panel.innerHTML=`<p class="eyebrow">${explorerEscape(eyebrow)}</p><h2>${explorerEscape(title)}</h2><p class="lead">${explorerEscape(copy)}</p><div class="chart-empty"><p>Loading current governed evidence…</p></div>`}
function setExplorerError(eyebrow,title,message){const panel=explorerPanel();if(!panel)return;panel.innerHTML=`<p class="eyebrow">${explorerEscape(eyebrow)}</p><h2>${explorerEscape(title)}</h2><p class="lead">${explorerEscape(message)}</p>`}

async function loadPlayersAssetsExplorer(){
  if(!state?.context?.league_id){setExplorerError('Players & Assets','Connect a league first.','Load a league from Home to browse its players and picks.');return}
  if(!state?.context?.team_id){setExplorerError('Players & Assets','Select a team to unlock the current league asset browser.','The present canonical ownership browser is team-context scoped. Select the team you manage; the explorer will still show assets from every franchise.');return}
  setExplorerLoading('Players & Assets','The league market, in one place.','Search, filter and sort canonical ownership plus authoritative NEXT-3 Value evidence.');
  try{
    const[browser,values]=await Promise.all([api('/api/trade-center/browser'),api('/api/values')]);
    const cardinal=new Map((values.fsffl_cardinal_values||[]).map(item=>[item.asset_id,item]));
    const percentiles=new Map((values.estimates||[]).map(item=>[item.asset_id,item]));
    const teams=[browser.focal_team,...(browser.counterparties||[])];
    fsfflExplorerState.assetRows=[];
    teams.forEach(team=>(team.assets||[]).forEach(asset=>{
      const assetId=asset.player_id||asset.pick_id;
      const cardinalRow=cardinal.get(assetId);
      const market=percentiles.get(assetId);
      fsfflExplorerState.assetRows.push({
        asset_ref:asset.asset_ref,asset_id:assetId,name:asset.label,kind:asset.asset_kind,detail:asset.detail||'',position:asset.asset_kind==='player'?asset.detail||'':'',slot:asset.roster_slot||'',owner:team.display_name,owner_team_id:team.team_id,value:cardinalRow?.score??null,market_percentile:market?.distribution?.mean??null,value_model:cardinalRow?.model_version||'',value_status:cardinalRow?.authority_status||'',value_source:cardinalRow?.evidence_source_id||'',value_scale:cardinalRow?.scale?.scale_id||'',market_sources:market?.source_ids||[]
      });
    }));
    renderPlayersAssetsExplorer(values);
  }catch(error){setExplorerError('Players & Assets','Unable to load the asset explorer.',error.message)}
}

function filteredAssetRows(){
  const query=(document.querySelector('#explorer-search')?.value||'').trim().toLowerCase();
  const type=document.querySelector('#explorer-type')?.value||'';
  const position=document.querySelector('#explorer-position')?.value||'';
  const owner=document.querySelector('#explorer-owner')?.value||'';
  return explorerSorted(fsfflExplorerState.assetRows.filter(row=>{
    if(query&&!`${row.name} ${row.detail} ${row.owner}`.toLowerCase().includes(query))return false;
    if(type&&row.kind!==type)return false;
    if(position&&row.position!==position)return false;
    if(owner&&row.owner_team_id!==owner)return false;
    return true;
  }),fsfflExplorerState.assetSort);
}

function renderAssetTableBody(){const body=document.querySelector('#explorer-asset-body');const count=document.querySelector('#explorer-result-count');if(!body)return;const rows=filteredAssetRows();if(count)count.textContent=`${rows.length} of ${fsfflExplorerState.assetRows.length} assets`;body.innerHTML=rows.length?rows.map(row=>`<tr data-asset-ref="${explorerEscape(row.asset_ref)}"><td><strong>${explorerEscape(row.name)}</strong><br><small>${explorerEscape(row.detail)}</small></td><td>${explorerEscape(row.kind==='player'?(row.position||'Player'):'Pick')}</td><td>${explorerEscape(row.owner)}</td><td>${explorerEscape(row.slot||'—')}</td><td><strong>${explorerValue(row.value)}</strong></td><td>${row.market_percentile==null?'—':`${explorerNumber(row.market_percentile*100,1)} pct`}</td></tr>`).join(''):'<tr><td colspan="6">No assets match those filters.</td></tr>'}

function renderPlayersAssetsExplorer(values){
  const panel=explorerPanel();if(!panel)return;
  const positions=[...new Set(fsfflExplorerState.assetRows.map(row=>row.position).filter(Boolean))].sort();
  const owners=[...new Map(fsfflExplorerState.assetRows.map(row=>[row.owner_team_id,row.owner])).entries()].sort((a,b)=>a[1].localeCompare(b[1]));
  const successful=(values.successful_sources||[]).join(', ')||'—';const failed=(values.failed_sources||[]).join(', ')||'None';
  panel.innerHTML=`<div class="panel-header"><div><p class="eyebrow">Players & Assets</p><h2>The league market, in one place</h2></div><span class="status-chip">Authoritative Value</span></div><p class="lead">Find any rostered player or owned pick without digging through team pages. FSFFL Value and Market Percentile remain separate governed measures.</p><div class="explorer-controls" style="display:grid;grid-template-columns:minmax(180px,2fr) repeat(3,minmax(120px,1fr));gap:8px;margin:16px 0"><input id="explorer-search" type="search" placeholder="Search player, pick or team" aria-label="Search assets"><select id="explorer-type"><option value="">All assets</option><option value="player">Players</option><option value="pick">Picks</option></select><select id="explorer-position"><option value="">All positions</option>${positions.map(value=>`<option>${explorerEscape(value)}</option>`).join('')}</select><select id="explorer-owner"><option value="">All teams</option>${owners.map(([id,name])=>`<option value="${explorerEscape(id)}">${explorerEscape(name)}</option>`).join('')}</select></div><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px"><small id="explorer-result-count"></small><small>Tap column labels to sort</small></div><div class="table-wrap"><table><thead><tr><th>${explorerSortButton('Asset','name',fsfflExplorerState.assetSort)}</th><th>${explorerSortButton('Type / Pos','position',fsfflExplorerState.assetSort)}</th><th>${explorerSortButton('Team','owner',fsfflExplorerState.assetSort)}</th><th>${explorerSortButton('Roster slot','slot',fsfflExplorerState.assetSort)}</th><th>${explorerSortButton('FSFFL Value','value',fsfflExplorerState.assetSort)}</th><th>${explorerSortButton('Market percentile','market_percentile',fsfflExplorerState.assetSort)}</th></tr></thead><tbody id="explorer-asset-body"></tbody></table></div><details style="margin-top:16px"><summary style="cursor:pointer">Evidence & data sources</summary><div style="padding-top:10px"><p><strong>Value sources loaded:</strong> ${explorerEscape(successful)}</p><p><strong>Unavailable/partial sources:</strong> ${explorerEscape(failed)}</p><p><strong>FSFFL Value:</strong> governed NEXT-3 market-cardinal output supplied by the backend. <strong>Market percentile:</strong> separate multi-source market-position evidence.</p><p><strong>Value model:</strong> ${explorerEscape(values.model_version||'—')} · <strong>Cardinal coverage:</strong> ${values.cardinal_player_coverage==null?'—':explorerPercent(values.cardinal_player_coverage,1)}</p></div></details>`;
  panel.querySelectorAll('input,select').forEach(control=>control.addEventListener(control.tagName==='INPUT'?'input':'change',renderAssetTableBody));
  panel.querySelectorAll('.explorer-sort').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.sortKey;fsfflExplorerState.assetSort=fsfflExplorerState.assetSort.key===key?{key,direction:fsfflExplorerState.assetSort.direction==='asc'?'desc':'asc'}:{key,direction:key==='name'||key==='owner'||key==='position'||key==='slot'?'asc':'desc'};renderPlayersAssetsExplorer(values)}));
  renderAssetTableBody();
}

async function loadAnalyticsExplorer(){
  if(!state?.context?.league_id){setExplorerError('Analytics Explorer','Connect a league first.','Load a league from Home to explore its governed analytics.');return}
  setExplorerLoading('Analytics Explorer','Compare the whole league.','Building a sortable table from the same authoritative metrics used by League Comparison.');
  const metrics=['expected_wins','playoff_probability','optimized_expected_points','asset_portfolio_mean','draft_pick_count'];
  try{
    const specs=await Promise.all(metrics.map(metric=>api(`/api/league/chart?metric=${encodeURIComponent(metric)}`)));
    const byTeam=new Map();
    specs.forEach((spec,index)=>{const metric=metrics[index];(spec.series?.[0]?.points||[]).forEach(point=>{const key=point.drilldown_ref||point.label;const row=byTeam.get(key)||{team_ref:key,team:point.label};row[metric]=typeof point.y==='number'?point.y:null;byTeam.set(key,row)})});
    fsfflExplorerState.teamRows=[...byTeam.values()];renderAnalyticsExplorer();
  }catch(error){setExplorerError('Analytics Explorer','Unable to load league analytics.',error.message)}
}

function filteredTeamRows(){const query=(document.querySelector('#analytics-search')?.value||'').trim().toLowerCase();return explorerSorted(fsfflExplorerState.teamRows.filter(row=>!query||row.team.toLowerCase().includes(query)),fsfflExplorerState.teamSort)}
function renderAnalyticsTableBody(){const body=document.querySelector('#analytics-team-body');const count=document.querySelector('#analytics-result-count');if(!body)return;const rows=filteredTeamRows();if(count)count.textContent=`${rows.length} teams`;body.innerHTML=rows.map(row=>`<tr><td><strong>${explorerEscape(row.team)}</strong></td><td>${explorerMetricValue('expected_wins',row.expected_wins)}</td><td>${explorerMetricValue('playoff_probability',row.playoff_probability)}</td><td>${explorerMetricValue('optimized_expected_points',row.optimized_expected_points)}</td><td>${explorerMetricValue('asset_portfolio_mean',row.asset_portfolio_mean)}</td><td>${explorerMetricValue('draft_pick_count',row.draft_pick_count)}</td></tr>`).join('')}
function renderAnalyticsExplorer(){
  const panel=explorerPanel();if(!panel)return;
  const s=fsfflExplorerState.teamSort;
  panel.innerHTML=`<div class="panel-header"><div><p class="eyebrow">Analytics Explorer</p><h2>Compare the league without hunting for answers</h2></div><span class="status-chip">Read-only analytics</span></div><p class="lead">Search and sort the current authoritative league outputs. These numbers come from State, Forecast, Value and Simulation; this screen only organizes them.</p><div style="display:flex;gap:10px;align-items:center;margin:16px 0;flex-wrap:wrap"><input id="analytics-search" type="search" placeholder="Search team" aria-label="Search teams" style="min-width:220px;flex:1"><small id="analytics-result-count"></small></div><div class="table-wrap"><table><thead><tr><th>${explorerSortButton('Team','team',s)}</th><th>${explorerSortButton('Expected wins','expected_wins',s)}</th><th>${explorerSortButton('Playoff odds','playoff_probability',s)}</th><th>${explorerSortButton('Projected scoring','optimized_expected_points',s)}</th><th>${explorerSortButton('Market portfolio','asset_portfolio_mean',s)}</th><th>${explorerSortButton('Pick inventory','draft_pick_count',s)}</th></tr></thead><tbody id="analytics-team-body"></tbody></table></div><details style="margin-top:16px"><summary style="cursor:pointer">What am I looking at?</summary><p style="padding-top:10px">Expected wins and playoff odds come from the governed season simulation when available. Projected scoring comes from the optimized forecast lineup view. Market portfolio is descriptive market-position evidence. Pick Inventory is a raw count until richer authoritative pick economics are attached.</p></details>`;
  document.querySelector('#analytics-search')?.addEventListener('input',renderAnalyticsTableBody);
  panel.querySelectorAll('.explorer-sort').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.sortKey;fsfflExplorerState.teamSort=fsfflExplorerState.teamSort.key===key?{key,direction:fsfflExplorerState.teamSort.direction==='asc'?'desc':'asc'}:{key,direction:key==='team'?'asc':'desc'};renderAnalyticsExplorer()}));
  renderAnalyticsTableBody();
}

window.renderFsfflExplorer=function(route){if(route==='players_assets')return loadPlayersAssetsExplorer();if(route==='analytics')return loadAnalyticsExplorer()};
