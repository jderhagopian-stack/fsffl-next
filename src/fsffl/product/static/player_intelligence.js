/* Player Intelligence North Star — presentation only.
 * Data authority: canonical State, governed Forecast, Broad Market and Shapley Intrinsic.
 */
(function(){
  'use strict';
  const VERSION='20260922-player-intelligence-trajectory-iqr1';
  const POLL_MS=1500,MAX_POLLS=80;
  let activeId=null,activeTab='overview',overview=null,history=null,generation=0,sheetScrollTop=0;
  const expandedSeasons=new Set();

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
  function close(){const root=ensure();root.hidden=true;document.body.classList.remove('pi-open');activeId=null;activeTab='overview';overview=null;history=null;sheetScrollTop=0;expandedSeasons.clear();generation+=1}
  function open(playerId){const id=normalizedPlayerId(playerId);if(!id)return;activeId=id;activeTab='overview';overview=null;history=null;sheetScrollTop=0;expandedSeasons.clear();generation+=1;const g=generation;const root=ensure();root.hidden=false;document.body.classList.add('pi-open');sheet().innerHTML='<div class="pi-loading"><i></i><strong>Loading Player Intelligence…</strong><span>Forecast, Value and History load independently.</span></div>';void loadOverview(g,id);void loadHistory(g,id)}

  async function loadOverview(g,id){
    try{
      let payload=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        if(g!==generation)return;
        payload=await api(`/api/player-intelligence/${encodeURIComponent(id)}`);
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

  async function loadHistory(g,id){
    try{
      let payload=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        if(g!==generation)return;
        payload=await api(`/api/player-intelligence/${encodeURIComponent(id)}/history`);
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
  function forecastBands(row){
    const u=row?.uncertainty||{};
    return {p10:finite(u.p10)?u.p10:null,p25:finite(u.p25)?u.p25:null,p50:finite(u.p50)?u.p50:null,p75:finite(u.p75)?u.p75:null,p90:finite(u.p90)?u.p90:null};
  }
  function trajectoryRows(){
    const actual=(history?.status==='ready'?history.seasons:[]).map(row=>({kind:'actual',season:row.season,expected:row.fantasy_points,median:null,p25:null,p75:null,p10:null,p90:null,ppg:row.fantasy_ppg,rank:row.position_rank}));
    const future=forecastRows().map(row=>{const bands=forecastBands(row);return{kind:'forecast',season:row.target_season,expected:row.fantasy_points,median:bands.p50,p25:bands.p25,p75:bands.p75,p10:bands.p10,p90:bands.p90,ppg:row.fantasy_ppg,rank:null}});
    return [...actual,...future].sort((a,b)=>a.season-b.season);
  }
  function chart(){
    const rows=trajectoryRows();if(!rows.length)return'<div class="pi-empty">Trajectory data is unavailable.</div>';
    const values=[];rows.forEach(row=>[row.expected,row.median,row.p25,row.p75,row.p10,row.p90].forEach(value=>{if(finite(value))values.push(value)}));
    const maximum=Math.max(...values,1),width=Math.max(540,96+rows.length*72),height=260,pad={left:44,right:20,top:24,bottom:40},plotW=width-pad.left-pad.right,plotH=height-pad.top-pad.bottom,step=rows.length>1?plotW/(rows.length-1):0;
    const x=index=>pad.left+(rows.length>1?index*step:plotW/2),y=value=>pad.top+plotH-(Math.max(0,value)/maximum)*plotH;
    const indexed=rows.map((row,index)=>({row,index})),actual=indexed.filter(item=>item.row.kind==='actual'),forecast=indexed.filter(item=>item.row.kind==='forecast');
    const points=(subset,key)=>subset.filter(item=>finite(item.row[key])).map(item=>`${x(item.index).toFixed(1)},${y(item.row[key]).toFixed(1)}`).join(' ');
    const band=(lower,upper,cls)=>{const eligible=forecast.filter(item=>finite(item.row[lower])&&finite(item.row[upper]));if(!eligible.length)return'';const upperPts=eligible.map(item=>`${x(item.index).toFixed(1)},${y(item.row[upper]).toFixed(1)}`),lowerPts=[...eligible].reverse().map(item=>`${x(item.index).toFixed(1)},${y(item.row[lower]).toFixed(1)}`);return `<polygon class="${cls}" points="${[...upperPts,...lowerPts].join(' ')}"></polygon>`};
    const firstForecast=forecast[0],boundary=firstForecast&&firstForecast.index>0?x(firstForecast.index)-step/2:null;
    const grid=[0,.25,.5,.75,1].map(f=>{const gy=pad.top+plotH-(f*plotH),label=maximum*f;return `<line class="pi-grid-line" x1="${pad.left}" x2="${width-pad.right}" y1="${gy.toFixed(1)}" y2="${gy.toFixed(1)}"></line><text class="pi-axis-label" x="${pad.left-8}" y="${(gy+4).toFixed(1)}" text-anchor="end">${num(label,0)}</text>`}).join('');
    const actualLine=actual.length?`<polyline class="pi-actual-line" points="${points(actual,'expected')}"></polyline>`:'';
    const expectedLine=forecast.length?`<polyline class="pi-expected-line" points="${points(forecast,'expected')}"></polyline>`:'';
    const medianLine=forecast.some(item=>finite(item.row.median))?`<polyline class="pi-median-line" points="${points(forecast,'median')}"></polyline>`:'';
    const dots=indexed.map(item=>{const row=item.row,px=x(item.index),py=y(row.expected),title=`${row.season} · ${row.kind==='actual'?'Actual':'Expected'} ${num(row.expected,1)} pts${finite(row.median)?` · Median ${num(row.median,1)}`:''}${finite(row.p25)&&finite(row.p75)?` · IQR ${num(row.p25,1)}–${num(row.p75,1)}`:''}`;return `<g><title>${esc(title)}</title><circle class="pi-chart-point ${row.kind}" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="4"></circle>${finite(row.median)&&Math.abs(row.median-row.expected)>.01?`<circle class="pi-chart-point median" cx="${px.toFixed(1)}" cy="${y(row.median).toFixed(1)}" r="3"></circle>`:''}<text class="pi-season-label" x="${px.toFixed(1)}" y="${height-14}" text-anchor="middle">${esc(row.season)}</text></g>`}).join('');
    return `<div class="pi-trajectory-scroll"><svg class="pi-trajectory-svg" viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-label="Career trajectory actual seasons followed by governed forecast seasons">${grid}${band('p10','p90','pi-outer-band')}${band('p25','p75','pi-iqr-band')}${boundary!==null?`<line class="pi-boundary" x1="${boundary.toFixed(1)}" x2="${boundary.toFixed(1)}" y1="${pad.top}" y2="${pad.top+plotH}"></line><text class="pi-phase-label-svg" x="${(boundary+8).toFixed(1)}" y="${pad.top+10}">FORECAST</text><text class="pi-phase-label-svg actual" x="${(boundary-8).toFixed(1)}" y="${pad.top+10}" text-anchor="end">ACTUAL</text>`:''}${actualLine}${expectedLine}${medianLine}${dots}</svg></div><div class="pi-chart-key"><span><i class="actual-line"></i>Actual</span><span><i class="expected-line"></i>Expected forecast</span><span><i class="median-line"></i>Median (P50)</span><span><i class="iqr"></i>IQR (P25–P75)</span><span><i class="outer"></i>P10–P90</span></div>`;
  }
  const statLabels={pass_att:'Pass att',pass_cmp:'Completions',pass_yd:'Pass yds',pass_td:'Pass TD',pass_int:'INT',rush_att:'Rush att',rush_yd:'Rush yds',rush_td:'Rush TD',rec_tgt:'Targets',rec:'Receptions',rec_yd:'Rec yds',rec_td:'Rec TD',fum:'Fumbles',fum_lost:'Fumbles lost'};
  function statGrid(stats){return Object.entries(stats||{}).filter(([,value])=>finite(value)).map(([key,value])=>`<span><small>${esc(statLabels[key]||key)}</small><b>${num(value,key.includes('yd')||key.includes('att')||key==='pass_cmp'||key==='rec_tgt'||key==='rec'?0:1)}</b></span>`).join('')}
  function positionStats(row){
    const primary=statGrid(row?.stats||{}),more=statGrid(row?.more_stats||{});
    return `${primary}${more?`<details class="pi-more-stats"><summary>More stats</summary><div class="pi-stat-grid pi-stat-grid-more">${more}</div></details>`:''}`;
  }
  function historyTable(){
    if(!history||history.status==='loading')return'<div class="pi-loading-inline"><i></i>Loading historical actuals…</div>';
    if(history.status!=='ready')return`<div class="pi-empty"><strong>Historical actuals unavailable.</strong><p>${esc(history.message||'No canonical history is available.')}</p></div>`;
    const rows=[...(history.seasons||[])].sort((a,b)=>b.season-a.season);if(!rows.length)return'<div class="pi-empty">No prior-season actuals were returned for this player.</div>';
    return `<div class="pi-history-list">${rows.map(row=>`<details class="pi-history-row" data-pi-season="${row.season}" ${expandedSeasons.has(String(row.season))?'open':''}><summary><span><strong>${row.season}</strong><small>${row.games_played} GP</small></span><span><small>Fantasy points</small><b>${num(row.fantasy_points,1)}</b></span><span><small>Fantasy PPG</small><b>${num(row.fantasy_ppg,1)}</b></span>${row.position_rank?`<span><small>Position rank</small><b>#${row.position_rank}</b></span>`:''}</summary><div class="pi-stat-grid">${positionStats(row)}</div><p class="pi-foot">${esc(row.scoring_basis)} · GP: ${esc(row.games_played_basis||'basis unavailable')} · ${esc(row.source)} / ${esc(row.source_version)}${row.rank_basis?` · ${esc(row.rank_basis)}`:''}</p></details>`).join('')}</div>`;
  }
  function forecastTable(){
    const rows=forecastRows();if(!rows.length)return'<div class="pi-empty">Governed Forecast trajectory unavailable.</div>';
    return `<div class="pi-forecast-list">${rows.map(row=>{const u=row.uncertainty||{},ppgAvailable=finite(row.fantasy_ppg),ppg=ppgAvailable?`${num(row.fantasy_ppg,1)} PPG`:'PPG unavailable',basis=String(row.ppg_basis||'').replace(/^unavailable:\s*/i,''),iqr=finite(u.p25)&&finite(u.p75)?`${num(u.p25,0)}–${num(u.p75,0)}`:'Unavailable',outer=finite(u.p10)&&finite(u.p90)?`${num(u.p10,0)}–${num(u.p90,0)}`:'Unavailable';return `<article><div class="pi-forecast-card-head"><small>${row.year_index===1?'Current season':`Year ${row.year_index}`} · ${row.target_season}</small><strong>${num(row.fantasy_points,1)} pts</strong><span>Expected · governed economic centerline</span><em>${ppg}${basis?` · ${esc(basis)}`:''}</em></div><div class="pi-forecast-metrics"><span><small>Median (P50)</small><b>${num(u.p50,0)}</b></span><span><small>IQR (P25–P75)</small><b>${iqr}</b></span><span><small>P10–P90</small><b>${outer}</b></span></div></article>`}).join('')}</div>`;
  }
  function intrinsicReason(v){
    if(finite(v?.intrinsic_value_index))return null;
    if(['queued','running'].includes(v?.intrinsic_status))return'Canonical Shapley Intrinsic is still preparing server-side.';
    return v?.intrinsic_error||v?.intrinsic_status_reason||'Governed FSFFL Intrinsic is unavailable for the current league state.';
  }
  function valueRead(){
    const v=overview?.value||{},gap=finite(v.intrinsic_value_index)&&finite(v.broad_market_value_index)?v.intrinsic_value_index-v.broad_market_value_index:null;
    if(!finite(gap)){const reason=intrinsicReason(v);return reason?`FSFFL Intrinsic unavailable: ${reason}`:'Comparison is unavailable until both governed lenses are ready.'}
    if(Math.abs(gap)<250)return'Broad Market and FSFFL Intrinsic are broadly aligned on the shared display ruler.';
    return gap>0?'FSFFL Intrinsic is higher than Broad Market — investigate whether market price understates the football economics.':'Broad Market is higher than FSFFL Intrinsic — investigate whether market demand exceeds the football-economic read.';
  }
  function intrinsicDisplay(v){if(finite(v?.intrinsic_value_index))return idx(v.intrinsic_value_index);if(['queued','running'].includes(v?.intrinsic_status))return'Preparing…';return'Unavailable'}
  function valueCards(){
    const v=overview?.value||{},reason=intrinsicReason(v);
    return `<div class="pi-value-grid"><article><small>Broad Market</small><strong>${idx(v.broad_market_value_index)}</strong><span>0–10,000 Value Index</span><em>${pct(v.broad_market_percentile)}</em></article><article><small>FSFFL Intrinsic</small><strong>${intrinsicDisplay(v)}</strong><span>0–10,000 Value Index</span><em class="pi-value-reason">${finite(v.intrinsic_percentile)?pct(v.intrinsic_percentile):esc(reason||'Governed value ready')}</em></article></div><div class="pi-value-read"><strong>${esc(valueRead())}</strong><p>Same presentation ruler; separate underlying authorities. This is not a buy/sell command.</p></div>`;
  }
  function forecastProvenance(){
    const f=overview?.forecast||{},basis=f.current_evidence_basis||'unavailable',fallback=basis==='preseason_baseline';
    return `<div class="pi-provenance ${fallback?'fallback':''}"><strong>${fallback?'Preserved Preseason Forecast fallback':'Current governed Forecast'}</strong><span>Evidence basis: ${esc(basis)} · as of ${esc(f.current_as_of||'—')}</span><span>Sources: ${esc((f.successful_source_ids||[]).join(', ')||'preserved / unavailable')}</span></div>`;
  }

  function captureViewState(){
    const host=sheet();sheetScrollTop=host.scrollTop;
    host.querySelectorAll('.pi-history-row[data-pi-season]').forEach(row=>{const season=String(row.dataset.piSeason||'');if(!season)return;if(row.open)expandedSeasons.add(season);else expandedSeasons.delete(season)});
  }
  function restoreViewState(){
    const host=sheet();host.querySelectorAll('.pi-history-row[data-pi-season]').forEach(row=>{row.open=expandedSeasons.has(String(row.dataset.piSeason||''));row.addEventListener('toggle',()=>{const season=String(row.dataset.piSeason||'');if(row.open)expandedSeasons.add(season);else expandedSeasons.delete(season)})});
    requestAnimationFrame(()=>{host.scrollTop=sheetScrollTop});
  }
  function render(){
    if(!overview)return;captureViewState();const p=overview.player,v=overview.value||{},first=y1();
    sheet().innerHTML=`<button class="pi-close" data-pi-close aria-label="Close">×</button>
      <header class="pi-player-head"><div class="pi-avatar">${esc((p.full_name||'?').split(' ').map(x=>x[0]).slice(0,2).join(''))}</div><div><p class="eyebrow">Player Intelligence</p><h2>${esc(p.full_name)}</h2><span>${esc(p.position)} · ${esc(p.nfl_team||'FA')} · age ${esc(p.age_years??'—')}</span></div></header>
      <nav class="pi-tabs" role="tablist"><button data-pi-tab="overview" class="${tabClass('overview')}">Overview</button><button data-pi-tab="career" class="${tabClass('career')}">Career & Forecast</button><button data-pi-tab="value" class="${tabClass('value')}">Value</button><button data-pi-tab="methods" class="${tabClass('methods')}">Methods / Evidence</button></nav>
      <div class="pi-tab ${tabClass('overview')}" data-pi-panel="overview">
        ${forecastProvenance()}
        <div class="pi-overview-grid"><article><small>Season Projection</small><strong>${num(first?.fantasy_points,1)}</strong><span>fantasy pts</span><em>${finite(first?.fantasy_ppg)?`${num(first.fantasy_ppg,1)} PPG`:'PPG unavailable'}</em></article><article><small>Broad Market</small><strong>${idx(v.broad_market_value_index)}</strong><span>Value Index</span><em>${pct(v.broad_market_percentile)}</em></article><article><small>FSFFL Intrinsic</small><strong>${intrinsicDisplay(v)}</strong><span>Value Index</span><em>${pct(v.intrinsic_percentile)}</em></article></div>
        <section class="pi-section"><div class="pi-section-head"><div><small>Career trajectory</small><h3>Actual → Forecast</h3></div></div>${chart()}</section>
      </div>
      <div class="pi-tab ${tabClass('career')}" data-pi-panel="career"><section class="pi-section"><div class="pi-section-head"><div><small>Career & Forecast</small><h3>Full career actuals through Year 3</h3></div></div>${chart()}</section><section class="pi-section"><h3>Forecast details</h3>${forecastTable()}</section><section class="pi-section"><h3>Historical actuals</h3>${historyTable()}</section></div>
      <div class="pi-tab ${tabClass('value')}" data-pi-panel="value">${valueCards()}<details class="pi-method"><summary>Why this value?</summary><p><strong>Raw Shapley:</strong> ${num(v.raw_shapley_marginal_points,1)} marginal fantasy-point units. This is audit detail, not projected points or market price.</p><p><strong>Display contract:</strong> ${esc(v.value_presentation?.contract_version||'unavailable')}. The shared Value Index is presentation-only and does not alter Broad Market, Intrinsic, Team Utility, or Trade Decision.</p><p><strong>League Market Value:</strong> unavailable by design.</p></details></div>
      <div class="pi-tab ${tabClass('methods')}" data-pi-panel="methods">${forecastProvenance()}<div class="pi-method-grid"><article><small>Current Forecast model</small><strong>${esc(overview.forecast?.current_model_version||'—')}</strong></article><article><small>Value presentation</small><strong>${esc(v.value_presentation?.contract_version||'Unavailable')}</strong></article><article><small>History scoring</small><strong>${esc(history?.scoring_basis||'Scored under current league rules when loaded')}</strong></article><article><small>Intrinsic readiness</small><strong>${esc(v.intrinsic_status||'unavailable')}</strong><span>${esc(intrinsicReason(v)||v.intrinsic_status_reason||'Governed value available')}</span></article></div><p class="pi-foot">Raw Market and raw Shapley quantities are never subtracted. Future Y2/Y3 points come directly from Forecast authority; they are not inferred from Intrinsic.</p></div>`;
    bindTabs();restoreViewState();
  }
  function bindTabs(){
    const host=sheet();host.querySelectorAll('[data-pi-tab]').forEach(button=>button.addEventListener('click',()=>{activeTab=button.dataset.piTab||'overview';host.querySelectorAll('[data-pi-tab]').forEach(x=>x.classList.toggle('active',x.dataset.piTab===activeTab));host.querySelectorAll('[data-pi-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.piPanel===activeTab))}));
  }
  document.addEventListener('click',event=>{const trigger=event.target.closest('[data-player-intelligence-id]');if(!trigger)return;const id=normalizedPlayerId(trigger.dataset.playerIntelligenceId);if(!id)return;event.preventDefault();event.stopPropagation();open(id)},true);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!ensure().hidden)close()});
  window.fsfflPlayerIntelligence={open,close,version:VERSION};
})();
