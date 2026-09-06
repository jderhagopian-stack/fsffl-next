const fsfflLeagueComparisonState={rows:[],sort:{key:'expected_wins',direction:'desc'}};

const fsfflLeagueMetrics=[
  {key:'expected_wins',label:'Expected wins',description:'Average regular-season wins from the governed season simulation.'},
  {key:'playoff_probability',label:'Playoff odds',description:'Probability of making the playoffs from the governed season simulation.'},
  {key:'optimized_expected_points',label:'Projected scoring',description:'Expected fantasy points from the optimized forecast lineup view.'},
  {key:'asset_portfolio_mean',label:'Market portfolio',description:'Descriptive multi-source market-position evidence across the current roster.'},
  {key:'draft_pick_count',label:'Pick inventory',description:'Raw count of currently owned draft picks; not a pick-value score.'}
];

function leagueComparisonPanel(){return document.querySelector('#generic-screen .panel')}
function lcEscape(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
function lcNumber(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'}
function lcPercent(value,digits=1){return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(digits)}%`:'—'}
function lcMetricValue(metric,value){if(value==null)return'—';if(metric==='playoff_probability')return lcPercent(value,1);if(metric==='expected_wins')return lcNumber(value,2);if(metric==='optimized_expected_points')return lcNumber(value,1);if(metric==='asset_portfolio_mean')return `${lcNumber(value*100,1)} pct`;if(metric==='draft_pick_count')return lcNumber(value,0);return lcNumber(value,2)}
function lcCompare(a,b){if(a==null&&b==null)return 0;if(a==null)return 1;if(b==null)return-1;if(typeof a==='number'&&typeof b==='number')return a-b;return String(a).localeCompare(String(b),undefined,{numeric:true,sensitivity:'base'})}
function lcSorted(rows,sort){return[...rows].sort((a,b)=>{const result=lcCompare(a[sort.key],b[sort.key]);return sort.direction==='asc'?result:-result})}
function lcSortButton(label,key){const sort=fsfflLeagueComparisonState.sort;const active=sort.key===key;const arrow=active?(sort.direction==='asc'?' ↑':' ↓'):'';return`<button type="button" class="text-button league-comparison-sort" data-sort-key="${key}">${lcEscape(label)}${arrow}</button>`}

function lcRank(metric,teamRef){const rows=[...fsfflLeagueComparisonState.rows].filter(row=>typeof row[metric]==='number').sort((a,b)=>b[metric]-a[metric]);const index=rows.findIndex(row=>row.team_ref===teamRef);return index>=0?index+1:null}
function lcTop(metric){return [...fsfflLeagueComparisonState.rows].filter(row=>typeof row[metric]==='number').sort((a,b)=>b[metric]-a[metric])[0]||null}

function renderLeagueMetricTile(metric){
  const top=lcTop(metric.key);
  const managedTeamId=state?.context?.team_id;
  const managed=fsfflLeagueComparisonState.rows.find(row=>row.team_ref===managedTeamId)||null;
  const rank=managed?lcRank(metric.key,managed.team_ref):null;
  return `<article class="league-comparison-tile">
    <span class="metric-label">${lcEscape(metric.label)}</span>
    <strong>${top?lcEscape(top.team):'—'}</strong>
    <small>${top?`League leader · ${lcMetricValue(metric.key,top[metric.key])}`:'Evidence unavailable'}</small>
    ${managed?`<div class="league-comparison-managed"><span>Your team</span><b>${lcMetricValue(metric.key,managed[metric.key])}</b><small>${rank?`Rank ${rank} of ${fsfflLeagueComparisonState.rows.length}`:'No rank available'}</small></div>`:''}
  </article>`;
}

function renderLeagueComparisonTable(){
  const body=document.querySelector('#league-comparison-body');
  if(!body)return;
  const query=(document.querySelector('#league-comparison-search')?.value||'').trim().toLowerCase();
  const rows=lcSorted(fsfflLeagueComparisonState.rows.filter(row=>!query||row.team.toLowerCase().includes(query)),fsfflLeagueComparisonState.sort);
  body.innerHTML=rows.map(row=>`<tr class="${row.team_ref===state?.context?.team_id?'managed-row':''}">
    <td><strong>${lcEscape(row.team)}</strong>${row.team_ref===state?.context?.team_id?'<br><small>Your team</small>':''}</td>
    <td>${lcMetricValue('expected_wins',row.expected_wins)}</td>
    <td>${lcMetricValue('playoff_probability',row.playoff_probability)}</td>
    <td>${lcMetricValue('optimized_expected_points',row.optimized_expected_points)}</td>
    <td>${lcMetricValue('asset_portfolio_mean',row.asset_portfolio_mean)}</td>
    <td>${lcMetricValue('draft_pick_count',row.draft_pick_count)}</td>
  </tr>`).join('')||'<tr><td colspan="6">No teams match that search.</td></tr>';
}

function renderLeagueComparison(){
  const panel=leagueComparisonPanel();if(!panel)return;
  panel.innerHTML=`<div class="panel-header"><div><p class="eyebrow">League Comparison</p><h2>See where every franchise stands</h2></div><span class="status-chip">Live analytics</span></div>
  <p class="lead">Scan the league at a glance, then sort the full table to answer the question you care about. All metrics are read-only views of authoritative State, Forecast, Value and Simulation outputs.</p>
  <div class="league-comparison-tiles">${fsfflLeagueMetrics.map(renderLeagueMetricTile).join('')}</div>
  <div class="league-comparison-toolbar"><input id="league-comparison-search" type="search" placeholder="Search team" aria-label="Search league teams"><small>Tap any column heading to sort</small></div>
  <div class="table-wrap"><table><thead><tr><th>${lcSortButton('Team','team')}</th><th>${lcSortButton('Expected wins','expected_wins')}</th><th>${lcSortButton('Playoff odds','playoff_probability')}</th><th>${lcSortButton('Projected scoring','optimized_expected_points')}</th><th>${lcSortButton('Market portfolio','asset_portfolio_mean')}</th><th>${lcSortButton('Pick inventory','draft_pick_count')}</th></tr></thead><tbody id="league-comparison-body"></tbody></table></div>
  <details class="league-comparison-evidence"><summary>What do these measures mean?</summary>${fsfflLeagueMetrics.map(metric=>`<p><strong>${lcEscape(metric.label)}:</strong> ${lcEscape(metric.description)}</p>`).join('')}<p><strong>Important:</strong> this view does not calculate new scores or rankings. It only sorts and presents backend-originated league metrics.</p></details>`;
  document.querySelector('#league-comparison-search')?.addEventListener('input',renderLeagueComparisonTable);
  panel.querySelectorAll('.league-comparison-sort').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.sortKey;const current=fsfflLeagueComparisonState.sort;fsfflLeagueComparisonState.sort=current.key===key?{key,direction:current.direction==='asc'?'desc':'asc'}:{key,direction:key==='team'?'asc':'desc'};renderLeagueComparison()}));
  renderLeagueComparisonTable();
}

async function loadFsfflLeagueComparison(){
  const panel=leagueComparisonPanel();if(!panel)return;
  if(!state?.context?.league_id){panel.innerHTML='<p class="eyebrow">League Comparison</p><h2>Connect a league first.</h2><p class="lead">Load a league from Home to compare franchises.</p>';return}
  panel.innerHTML='<p class="eyebrow">League Comparison</p><h2>Building the live league view…</h2><p class="lead">Loading current governed analytics.</p><div class="chart-empty"><p>Loading league metrics…</p></div>';
  try{
    const specs=await Promise.all(fsfflLeagueMetrics.map(metric=>api(`/api/league/chart?metric=${encodeURIComponent(metric.key)}`)));
    const byTeam=new Map();
    specs.forEach((spec,index)=>{const metric=fsfflLeagueMetrics[index].key;(spec.series?.[0]?.points||[]).forEach(point=>{const key=point.drilldown_ref||point.label;const row=byTeam.get(key)||{team_ref:key,team:point.label};row[metric]=typeof point.y==='number'?point.y:null;byTeam.set(key,row)})});
    fsfflLeagueComparisonState.rows=[...byTeam.values()];
    renderLeagueComparison();
  }catch(error){panel.innerHTML=`<p class="eyebrow">League Comparison</p><h2>Unable to load league comparison.</h2><p class="lead">${lcEscape(error.message)}</p>`}
}

function installLeagueComparisonStyles(){if(document.querySelector('#fsffl-league-comparison-style'))return;const style=document.createElement('style');style.id='fsffl-league-comparison-style';style.textContent=`
  .league-comparison-tiles{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:18px 0}
  .league-comparison-tile{border:1px solid var(--line);border-radius:14px;padding:14px;background:#0a1120;min-width:0}
  .league-comparison-tile>strong{display:block;margin:7px 0 2px;font-size:1rem;overflow-wrap:anywhere}
  .league-comparison-tile>small{color:var(--muted);line-height:1.35;display:block}
  .league-comparison-managed{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);display:grid;gap:3px}
  .league-comparison-managed span,.league-comparison-managed small{font-size:11px;color:var(--muted)}
  .league-comparison-managed b{font-size:1.05rem}
  .league-comparison-toolbar{display:flex;align-items:center;gap:12px;margin:14px 0 8px}
  .league-comparison-toolbar input{min-width:220px;flex:1}
  .league-comparison-toolbar small{color:var(--muted)}
  .managed-row{background:rgba(87,166,255,.06)}
  .league-comparison-evidence{margin-top:16px;color:var(--muted)}
  .league-comparison-evidence summary{cursor:pointer;color:var(--accent)}
  .league-comparison-evidence p{line-height:1.5}
  @media(max-width:1050px){.league-comparison-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @media(max-width:620px){.league-comparison-tiles{grid-template-columns:1fr}.league-comparison-toolbar{display:block}.league-comparison-toolbar input{width:100%;margin-bottom:8px}.league-comparison-toolbar small{display:block}}
`;document.head.appendChild(style)}

window.renderFsfflLeagueComparison=function(){installLeagueComparisonStyles();return loadFsfflLeagueComparison()};
