/* Player Intelligence North Star — presentation only.
 * Data authority: canonical State, governed Forecast, Broad Market and Shapley Intrinsic.
 */
(function(){
  'use strict';
  const VERSION='20260921-player-intelligence-corrective1';
  const POLL_MS=1500,MAX_POLLS=80;
  let activeId=null,activeTab='overview',overview=null,history=null,generation=0;

  const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'","&#039;");
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const num=(v,d=1)=>finite(v)?v.toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
  const idx=v=>finite(v)?Math.round(v).toLocaleString():'—';
  const pct=v=>finite(v)?`${Math.round(v*100)}th pct`:'—';
  const normalizedPlayerId=value=>{const id=String(value??'').trim();return id&&!['null','undefined','none'].includes(id.toLowerCase())?id:null};
  const tabClass=name=>activeTab===name?'active':'';

  function ensure(){
    let root=document.querySelector('#player-intelligence-root');
    if(root)return root;
    root=document.createElement('div');root.id='player-intelligence-root';root.hidden=true;
    root.innerHTML='<div class="pi-backdrop" data-pi-close></div><section class="pi-sheet" role="dialog" aria-modal="true" aria-label="Player Intelligence"><div class="pi-loading">Loading Player Intelligence…</div></section>';
    document.body.appendChild(root);
    root.addEventListener('click',event=>{if(event.target.closest('[data-pi-close]'))close()});
    return root;
  }
  function sheet(){return ensure().querySelector('.pi-sheet')}
  function close(){const root=ensure();root.hidden=true;document.body.classList.remove('pi-open');activeId=null;activeTab='overview';overview=null;history=null;generation+=1}
  function open(playerId){const id=normalizedPlayerId(playerId);if(!id)return;activeId=id;activeTab='overview';overview=null;history=null;generation+=1;const g=generation;const root=ensure();root.hidden=false;document.body.classList.add('pi-open');sheet().innerHTML='<div class="pi-loading"><i></i><strong>Loading Player Intelligence…</strong><span>Forecast, Value and History load independently.</span></div>';void loadOverview(g);void loadHistory(g)}

  async function loadOverview(g){
    try{
      let payload=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        payload=await api(`/api/player-intelligence/${encodeURIComponent(activeId)}`);
        if(g!==generation)return;
        overview=payload;render();
        if(!['queued','running'].includes(payload?.value?.intrinsic_status))break;
        await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||POLL_MS));
      }
      if(g!==generation)return;
    }catch(error){
      if(g!==generation)return;
      sheet().innerHTML=`<button class="pi-close" data-pi-close aria-label="Close">×</button><div class="pi-error"><strong>Player Intelligence unavailable.</strong><p>${esc(error.message||error)}</p></div>`;
    }
  }

  async function loadHistory(g){
    try{
      let payload=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        payload=await api(`/api/player-intelligence/${encodeURIComponent(activeId)}/history`);
        if(g!==generation)return;
        if(payload?.status!=='loading')break;
        history=payload;render();
        await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||POLL_MS));
      }
      if(g!==generation)return;
      history=payload;render();
    }catch(error){
      if(g!==generation)return;
      history={status:'unavailable',message:error.message||String(error),seasons:[]};render();
    }
  }

  function forecastRows(){return overview?.forecast?.rows||[]}
  function y1(){return forecastRows().find(row=>row.year_index===1)||null}
  function forecastRange(row){
    const u=row?.uncertainty||{};
    if(finite(u.p10)&&finite(u.p90))return[u.p10,u.p90];
    const scenarios=Array.isArray(u.scenarios)?u.scenarios:[];
    const values=scenarios.map(x=>x.fantasy_points).filter(finite);
    return values.length?[Math.min(...values),Math.max(...values)]:null;
  }
  function trajectoryRows(){
    const actual=(history?.status==='ready'?history.seasons:[]).map(row=>({kind:'actual',season:row.season,points:row.fantasy_points,ppg:row.fantasy_ppg,rank:row.position_rank,range:null}));
    const future=forecastRows().map(row=>({kind:'forecast',season:row.target_season,points:row.fantasy_points,ppg:row.fantasy_ppg,rank:null,range:forecastRange(row)}));
    return [...actual,...future].sort((a,b)=>a.season-b.season);
  }
  function chart(){
    const rows=trajectoryRows();if(!rows.length)return'<div class="pi-empty">Trajectory data is unavailable.</div>';
    const maximum=Math.max(...rows.map(row=>row.range?Math.max(row.points,row.range[1]):row.points),1);
    return `<div class="pi-chart" aria-label="Career trajectory">${rows.map((row,rowIndex)=>{const h=Math.max(3,row.points/maximum*100),range=row.range,lo=range?range[0]/maximum*100:null,hi=range?range[1]/maximum*100:null,forecastBoundary=row.kind==='forecast'&&rowIndex>0&&rows[rowIndex-1].kind==='actual';return `<button class="pi-bar-wrap ${forecastBoundary?'pi-forecast-boundary':''}" title="${esc(row.season)} · ${num(row.points,1)} pts${finite(row.ppg)?` · ${num(row.ppg,1)} PPG`:''}${row.rank?` · rank #${row.rank}`:''}">${forecastBoundary?'<i class="pi-phase-label">FORECAST</i>':''}<span class="pi-bar-zone">${range?`<i class="pi-range" style="bottom:${lo.toFixed(1)}%;height:${Math.max(1,hi-lo).toFixed(1)}%"></i>`:''}<b class="pi-bar ${row.kind}" style="height:${h.toFixed(1)}%"></b></span><strong>${esc(row.season)}</strong><small>${row.kind==='actual'?'Actual':'Forecast'}</small><em>${num(row.points,0)}</em></button>`}).join('')}</div><div class="pi-chart-key"><span><i class="actual"></i>Actual</span><span><i class="forecast"></i>Forecast</span><span><i class="range"></i>Governed uncertainty / scenario range</span></div>`;
  }
  function positionStats(row){
    const stats=row?.stats||{},labels={pass_yd:'Pass yds',pass_td:'Pass TD',pass_int:'INT',rush_yd:'Rush yds',rush_td:'Rush TD',rec:'Rec',rec_yd:'Rec yds',rec_td:'Rec TD'};
    return Object.entries(stats).filter(([,value])=>finite(value)).map(([key,value])=>`<span><small>${esc(labels[key]||key)}</small><b>${num(value,key.includes('yd')?0:1)}</b></span>`).join('');
  }
  function historyTable(){
    if(!history||history.status==='loading')return'<div class="pi-loading-inline"><i></i>Loading historical actuals…</div>';
    if(history.status!=='ready')return`<div class="pi-empty"><strong>Historical actuals unavailable.</strong><p>${esc(history.message||'No canonical history is available.')}</p></div>`;
    const rows=history.seasons||[];if(!rows.length)return'<div class="pi-empty">No prior-season actuals were returned for this player.</div>';
    return `<div class="pi-history-list">${rows.map(row=>`<details class="pi-history-row"><summary><span><strong>${row.season}</strong><small>${row.games_played} GP</small></span><span><small>Fantasy points</small><b>${num(row.fantasy_points,1)}</b></span><span><small>PPG</small><b>${num(row.fantasy_ppg,1)}</b></span><span><small>Position rank</small><b>${row.position_rank?`#${row.position_rank}`:'—'}</b></span></summary><div class="pi-stat-grid">${positionStats(row)}</div><p class="pi-foot">${esc(row.scoring_basis)} · ${esc(row.source)} / ${esc(row.source_version)}${row.rank_basis?` · ${esc(row.rank_basis)}`:''}</p></details>`).join('')}</div>`;
  }
  function forecastTable(){
    const rows=forecastRows();if(!rows.length)return'<div class="pi-empty">Governed Forecast trajectory unavailable.</div>';
    return `<div class="pi-forecast-list">${rows.map(row=>{const range=forecastRange(row),ppgAvailable=finite(row.fantasy_ppg),ppg=ppgAvailable?`${num(row.fantasy_ppg,1)} PPG`:'PPG unavailable',basis=String(row.ppg_basis||'').replace(/^unavailable:\s*/i,'');return `<article><div><small>${row.year_index===1?'Current season':`Year ${row.year_index}`} · ${row.target_season}</small><strong>${num(row.fantasy_points,1)} pts</strong><span>${ppg}${basis?` <i>${esc(basis)}</i>`:''}</span></div><div><small>Uncertainty</small><strong>${range?`${num(range[0],0)}–${num(range[1],0)} pts`:(finite(row.uncertainty?.stddev)?`σ ${num(row.uncertainty.stddev,1)}`:'Unavailable')}</strong><span>${esc(row.uncertainty?.kind||'none')}</span></div></article>`}).join('')}</div>`;
  }
  function valueRead(){
    const v=overview?.value||{},gap=finite(v.intrinsic_value_index)&&finite(v.broad_market_value_index)?v.intrinsic_value_index-v.broad_market_value_index:null;
    if(!finite(gap))return'Comparison is unavailable until both governed lenses are ready.';
    if(Math.abs(gap)<250)return'Broad Market and FSFFL Intrinsic are broadly aligned on the shared display ruler.';
    return gap>0?'FSFFL Intrinsic is higher than Broad Market — investigate whether market price understates the football economics.':'Broad Market is higher than FSFFL Intrinsic — investigate whether market demand exceeds the football-economic read.';
  }
  function intrinsicDisplay(v){if(finite(v?.intrinsic_value_index))return idx(v.intrinsic_value_index);if(['queued','running'].includes(v?.intrinsic_status))return'Preparing…';if(v?.intrinsic_status==='failed')return'Unavailable';return'—'}
  function valueCards(){
    const v=overview?.value||{};
    return `<div class="pi-value-grid"><article><small>Broad Market</small><strong>${idx(v.broad_market_value_index)}</strong><span>0–10,000 Value Index</span><em>${pct(v.broad_market_percentile)}</em></article><article><small>FSFFL Intrinsic</small><strong>${intrinsicDisplay(v)}</strong><span>0–10,000 Value Index</span><em>${pct(v.intrinsic_percentile)}</em></article></div><div class="pi-value-read"><strong>${esc(valueRead())}</strong><p>Same presentation ruler; separate underlying authorities. This is not a buy/sell command.</p></div>`;
  }
  function forecastProvenance(){
    const f=overview?.forecast||{},basis=f.current_evidence_basis||'unavailable',fallback=basis==='preseason_baseline';
    return `<div class="pi-provenance ${fallback?'fallback':''}"><strong>${fallback?'Preserved Preseason Forecast fallback':'Current governed Forecast'}</strong><span>Evidence basis: ${esc(basis)} · as of ${esc(f.current_as_of||'—')}</span><span>Sources: ${esc((f.successful_source_ids||[]).join(', ')||'preserved / unavailable')}</span></div>`;
  }

  function render(){
    if(!overview)return;const p=overview.player,v=overview.value||{},first=y1();
    sheet().innerHTML=`<button class="pi-close" data-pi-close aria-label="Close">×</button>
      <header class="pi-player-head"><div class="pi-avatar">${esc((p.full_name||'?').split(' ').map(x=>x[0]).slice(0,2).join(''))}</div><div><p class="eyebrow">Player Intelligence</p><h2>${esc(p.full_name)}</h2><span>${esc(p.position)} · ${esc(p.nfl_team||'FA')} · age ${esc(p.age_years??'—')}</span></div></header>
      <nav class="pi-tabs" role="tablist"><button data-pi-tab="overview" class="${tabClass('overview')}">Overview</button><button data-pi-tab="career" class="${tabClass('career')}">Career & Forecast</button><button data-pi-tab="value" class="${tabClass('value')}">Value</button><button data-pi-tab="methods" class="${tabClass('methods')}">Methods / Evidence</button></nav>
      <div class="pi-tab ${tabClass('overview')}" data-pi-panel="overview">
        ${forecastProvenance()}
        <div class="pi-overview-grid"><article><small>Season Projection</small><strong>${num(first?.fantasy_points,1)}</strong><span>fantasy pts</span><em>${finite(first?.fantasy_ppg)?`${num(first.fantasy_ppg,1)} PPG`:'PPG unavailable'}</em></article><article><small>Broad Market</small><strong>${idx(v.broad_market_value_index)}</strong><span>Value Index</span><em>${pct(v.broad_market_percentile)}</em></article><article><small>FSFFL Intrinsic</small><strong>${intrinsicDisplay(v)}</strong><span>Value Index</span><em>${pct(v.intrinsic_percentile)}</em></article></div>
        <section class="pi-section"><div class="pi-section-head"><div><small>Career trajectory</small><h3>Actual → Forecast</h3></div></div>${chart()}</section>
      </div>
      <div class="pi-tab ${tabClass('career')}" data-pi-panel="career"><section class="pi-section"><div class="pi-section-head"><div><small>Career & Forecast</small><h3>Historical actuals through Year 3</h3></div></div>${chart()}</section><section class="pi-section"><h3>Forecast details</h3>${forecastTable()}</section><section class="pi-section"><h3>Historical actuals</h3>${historyTable()}</section></div>
      <div class="pi-tab ${tabClass('value')}" data-pi-panel="value">${valueCards()}<details class="pi-method"><summary>Why this value?</summary><p><strong>Raw Shapley:</strong> ${num(v.raw_shapley_marginal_points,1)} marginal fantasy-point units. This is audit detail, not projected points or market price.</p><p><strong>Display contract:</strong> ${esc(v.value_presentation?.contract_version||'unavailable')}. The shared Value Index is presentation-only and does not alter Broad Market, Intrinsic, Team Utility, or Trade Decision.</p><p><strong>League Market Value:</strong> unavailable by design.</p></details></div>
      <div class="pi-tab ${tabClass('methods')}" data-pi-panel="methods">${forecastProvenance()}<div class="pi-method-grid"><article><small>Current Forecast model</small><strong>${esc(overview.forecast?.current_model_version||'—')}</strong></article><article><small>Value presentation</small><strong>${esc(v.value_presentation?.contract_version||'Unavailable')}</strong></article><article><small>History scoring</small><strong>${esc(history?.scoring_basis||'Scored under current league rules when loaded')}</strong></article><article><small>Intrinsic readiness</small><strong>${esc(v.intrinsic_status||'unavailable')}</strong></article></div><p class="pi-foot">Raw Market and raw Shapley quantities are never subtracted. Future Y2/Y3 points come directly from Forecast authority; they are not inferred from Intrinsic.</p></div>`;
    bindTabs();
  }
  function bindTabs(){
    const host=sheet();host.querySelectorAll('[data-pi-tab]').forEach(button=>button.addEventListener('click',()=>{activeTab=button.dataset.piTab||'overview';host.querySelectorAll('[data-pi-tab]').forEach(x=>x.classList.toggle('active',x.dataset.piTab===activeTab));host.querySelectorAll('[data-pi-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.piPanel===activeTab))}));
  }
  document.addEventListener('click',event=>{const trigger=event.target.closest('[data-player-intelligence-id]');if(!trigger)return;const id=normalizedPlayerId(trigger.dataset.playerIntelligenceId);if(!id)return;event.preventDefault();event.stopPropagation();open(id)},true);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!ensure().hidden)close()});
  window.fsfflPlayerIntelligence={open,close,version:VERSION};
})();
