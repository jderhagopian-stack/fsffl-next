let fsfflHomeChartSortDirection='desc';
let fsfflHomeLastChartSpec=null;

function homeChartValue(spec,value){
  if(typeof value!=='number'||!Number.isFinite(value))return'—';
  const unit=String(spec?.series?.[0]?.unit||'').toLowerCase();
  if(unit==='probability')return`${(value*100).toFixed(1)}%`;
  if(unit==='wins')return value.toFixed(2);
  if(unit==='picks')return value.toFixed(0);
  if(unit==='fantasy points')return value.toFixed(1);
  if(unit==='value'&&value>=0&&value<=1)return`${(value*100).toFixed(1)} pct`;
  return value.toLocaleString(undefined,{maximumFractionDigits:1});
}
function renderFsfflHomeLeagueChart(spec){
  const container=document.querySelector('#league-chart');
  if(!container||!spec?.series?.length)return;
  fsfflHomeLastChartSpec=spec;
  const title=document.querySelector('#league-chart-title');
  if(title)title.textContent=spec.title||'League comparison';
  const points=(spec.series[0].points||[]).filter(point=>typeof point.y==='number'&&Number.isFinite(point.y));
  if(!points.length){showChartMessage('This metric is waiting for its authoritative forecast/value/simulation evidence.');return}
  const direction=fsfflHomeChartSortDirection;
  const ordered=[...points].sort((a,b)=>direction==='asc'?a.y-b.y:b.y-a.y);
  const values=ordered.map(point=>point.y),max=Math.max(...values),min=Math.min(...values),span=Math.max(max-min,1e-9);
  container.className='home-league-leaderboard';
  container.innerHTML=`<div class="home-chart-toolbar"><span>${ordered.length} teams</span><button type="button" id="home-chart-sort" class="text-button">${direction==='desc'?'High → low':'Low → high'}</button></div><div class="home-chart-rows">${ordered.map((point,index)=>{const normalized=(point.y-min)/span;const width=points.length===1?100:18+82*normalized;const managed=point.key===state?.context?.team_id;return `<button type="button" class="home-chart-row${managed?' managed':''}" data-home-drilldown="${escapeHtml(point.drilldown_ref||'')}"><span class="home-chart-rank">${index+1}</span><span class="home-chart-team"><strong>${escapeHtml(point.label)}</strong>${managed?'<small>Your team</small>':''}</span><span class="home-chart-bar-track"><i style="width:${width.toFixed(1)}%"></i></span><strong class="home-chart-value">${escapeHtml(homeChartValue(spec,point.y))}</strong></button>`}).join('')}</div>`;
  container.querySelector('#home-chart-sort')?.addEventListener('click',()=>{fsfflHomeChartSortDirection=fsfflHomeChartSortDirection==='desc'?'asc':'desc';renderFsfflHomeLeagueChart(fsfflHomeLastChartSpec)});
  container.querySelectorAll('[data-home-drilldown]').forEach(row=>row.addEventListener('click',()=>{const ref=row.dataset.homeDrilldown;if(ref)window.dispatchEvent(new CustomEvent('fsffl:drilldown',{detail:ref}))}));
}
function installFsfflHomeChartRenderer(){
  window.renderBarChart=renderFsfflHomeLeagueChart;
  renderBarChart=renderFsfflHomeLeagueChart;
  if(state?.context?.league_id&&typeof loadLeagueMetric==='function')loadLeagueMetric(document.querySelector('#metric-select')?.value||'expected_wins');
}
function installFsfflHomeExperience(){
  const leagueScreen=document.querySelector('#league-screen');if(!leagueScreen)return;
  installFsfflHomeChartRenderer();
  if(document.querySelector('#home-quick-actions'))return;
  const hero=leagueScreen.querySelector('.hero-row');
  const lead=hero?.querySelector('.lead');if(lead)lead.textContent='Start with the question you want answered. FSFFL NEXT keeps the model complexity underneath and brings the useful result to the surface.';
  const actions=document.createElement('section');actions.id='home-quick-actions';actions.className='home-quick-actions';actions.innerHTML=`<div class="home-quick-header"><p class="eyebrow">What do you want to do?</p><h2>Jump straight to the answer</h2></div><div class="home-quick-grid"><button type="button" data-home-route="my_team"><strong>Review My Team</strong><span>Lineup, outlook, values and picks</span></button><button type="button" data-home-route="league_comparison"><strong>Compare the League</strong><span>See where every franchise stands</span></button><button type="button" data-home-route="players_assets"><strong>Browse Players & Assets</strong><span>Search and sort the whole market</span></button><button type="button" data-home-route="trade_center"><strong>Analyze a Trade</strong><span>Build a deal and see both sides</span></button><button type="button" data-home-route="opportunities"><strong>Find Opportunities</strong><span>Explore trade tests and available players</span></button><button type="button" data-home-route="analytics"><strong>Open Analytics Terminal</strong><span>League, players, Value Lab and evidence</span></button><button type="button" data-home-route="reports"><strong>Open Reports</strong><span>Readable team, league and evidence views</span></button></div>`;
  hero?.insertAdjacentElement('afterend',actions);
  actions.querySelectorAll('[data-home-route]').forEach(button=>button.addEventListener('click',()=>{const route=button.dataset.homeRoute;if(['my_team','trade_center','opportunities'].includes(route)&&!state?.context?.team_id){document.querySelector('#team-select')?.focus();return}setRoute(route)}));

  const runtime=document.querySelector('#runtime-status');const grid=document.querySelector('#runtime-stage-grid');if(runtime&&grid&&!runtime.querySelector('#runtime-detail-toggle')){
    grid.hidden=true;
    const toggle=document.createElement('button');toggle.id='runtime-detail-toggle';toggle.type='button';toggle.className='text-button';toggle.textContent='Show technical status';toggle.setAttribute('aria-expanded','false');toggle.addEventListener('click',()=>{grid.hidden=!grid.hidden;toggle.textContent=grid.hidden?'Show technical status':'Hide technical status';toggle.setAttribute('aria-expanded',String(!grid.hidden))});
    runtime.querySelector('.panel-header')?.appendChild(toggle);
    const eyebrow=runtime.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='System status';
  }
  const style=document.createElement('style');style.textContent=`.home-quick-actions{margin:16px 0 20px}.home-quick-header h2{margin-top:0}.home-quick-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.home-quick-grid button{border:1px solid var(--line);background:#0a1120;color:var(--text);border-radius:14px;padding:15px;text-align:left;cursor:pointer;display:flex;flex-direction:column;gap:5px;min-height:86px}.home-quick-grid button:hover{border-color:var(--accent)}.home-quick-grid strong{font-size:14px}.home-quick-grid span{color:var(--muted);font-size:12px;line-height:1.4}.home-league-leaderboard{display:block!important;min-height:0!important}.home-chart-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;color:var(--muted);font-size:12px}.home-chart-rows{display:grid;gap:7px}.home-chart-row{appearance:none;width:100%;border:1px solid var(--line);background:#0a1120;color:var(--text);border-radius:10px;padding:9px 10px;display:grid;grid-template-columns:28px minmax(120px,1.2fr) minmax(90px,2fr) auto;gap:9px;align-items:center;text-align:left;cursor:pointer}.home-chart-row.managed{border-color:var(--accent);background:rgba(87,166,255,.07)}.home-chart-rank{color:var(--muted);font-size:12px;text-align:center}.home-chart-team{display:grid;min-width:0}.home-chart-team strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.home-chart-team small{color:var(--accent);font-size:10px}.home-chart-bar-track{height:8px;background:var(--surface-2);border-radius:999px;overflow:hidden}.home-chart-bar-track i{display:block;height:100%;background:var(--accent);border-radius:999px}.home-chart-value{font-variant-numeric:tabular-nums;white-space:nowrap}@media(max-width:760px){.home-quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.home-chart-row{grid-template-columns:24px minmax(105px,1fr) minmax(55px,.8fr) auto;padding:9px 8px;gap:7px}.home-chart-value{font-size:12px}}@media(max-width:460px){.home-quick-grid{grid-template-columns:1fr}.home-quick-grid button{min-height:0}.home-chart-bar-track{display:none}.home-chart-row{grid-template-columns:22px minmax(0,1fr) auto}}`;document.head.appendChild(style);
}
window.installFsfflHomeExperience=installFsfflHomeExperience;
