/* Player Intelligence North Star — presentation only.
 * Data authority: canonical State, governed Forecast, Broad Market and Shapley Intrinsic.
 */
(function(){
  'use strict';
  const VERSION='20260922-player-intelligence-final-ia1';
  const POLL_MS=1500,MAX_POLLS=80;
  let activeId=null,activeTab='overview',overview=null,history=null,generation=0,sheetScrollTop=0,historyView=null,careerScrollLeft=null,marketContext=null;
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
  function close(){const root=ensure();root.hidden=true;document.body.classList.remove('pi-open');activeId=null;activeTab='overview';overview=null;history=null;historyView=null;careerScrollLeft=null;marketContext=null;sheetScrollTop=0;expandedSeasons.clear();generation+=1}
  function open(playerId,context=null){const id=normalizedPlayerId(playerId);if(!id)return;activeId=id;activeTab='overview';overview=null;history=null;historyView=null;careerScrollLeft=null;marketContext=context&&typeof context==='object'?{...context}:null;sheetScrollTop=0;expandedSeasons.clear();generation+=1;const g=generation;const root=ensure();root.hidden=false;document.body.classList.add('pi-open');sheet().innerHTML='<div class="pi-loading"><i></i><strong>Loading Player Intelligence…</strong><span>Forecast, value lenses, and stats load independently.</span></div>';void loadOverview(g,id);void loadHistory(g,id)}

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
  function chart(preview=false){
    const allRows=trajectoryRows();if(!allRows.length)return'<div class="pi-empty">Trajectory data is unavailable.</div>';
    const actualAll=allRows.filter(row=>row.kind==='actual'),forecastAll=allRows.filter(row=>row.kind==='forecast');
    const rows=preview?[...actualAll.slice(-2),...forecastAll]:allRows;
    const values=[];rows.forEach(row=>[row.expected,row.median,row.p25,row.p75,row.p10,row.p90].forEach(value=>{if(finite(value))values.push(value)}));
    const maximum=Math.max(...values,1),width=Math.max(preview?500:620,100+rows.length*(preview?58:72)),height=260,pad={left:44,right:20,top:24,bottom:40},plotW=width-pad.left-pad.right,plotH=height-pad.top-pad.bottom,step=rows.length>1?plotW/(rows.length-1):0;
    const x=index=>pad.left+(rows.length>1?index*step:plotW/2),y=value=>pad.top+plotH-(Math.max(0,value)/maximum)*plotH;
    const indexed=rows.map((row,index)=>({row,index})),actual=indexed.filter(item=>item.row.kind==='actual'),forecast=indexed.filter(item=>item.row.kind==='forecast');
    const bridge=forecast.length&&actual.length?[actual[actual.length-1],...forecast]:forecast;
    const points=(subset,key)=>subset.filter(item=>finite(item.row[key])).map(item=>`${x(item.index).toFixed(1)},${y(item.row[key]).toFixed(1)}`).join(' ');
    const band=(lower,upper,cls)=>{const eligible=forecast.filter(item=>finite(item.row[lower])&&finite(item.row[upper]));if(!eligible.length)return'';const upperPts=eligible.map(item=>`${x(item.index).toFixed(1)},${y(item.row[upper]).toFixed(1)}`),lowerPts=[...eligible].reverse().map(item=>`${x(item.index).toFixed(1)},${y(item.row[lower]).toFixed(1)}`);return `<polygon class="${cls}" points="${[...upperPts,...lowerPts].join(' ')}"></polygon>`};
    const firstForecast=forecast[0],boundary=firstForecast&&firstForecast.index>0?x(firstForecast.index)-step/2:null;
    const grid=[0,.25,.5,.75,1].map(f=>{const gy=pad.top+plotH-(f*plotH),label=maximum*f;return `<line class="pi-grid-line" x1="${pad.left}" x2="${width-pad.right}" y1="${gy.toFixed(1)}" y2="${gy.toFixed(1)}"></line><text class="pi-axis-label" x="${pad.left-8}" y="${(gy+4).toFixed(1)}" text-anchor="end">${num(label,0)}</text>`}).join('');
    const actualLine=actual.length?`<polyline class="pi-actual-line" points="${points(actual,'expected')}"></polyline>`:'';
    const expectedLine=bridge.length?`<polyline class="pi-expected-line" points="${points(bridge,'expected')}"></polyline>`:'';
    const medianLine=forecast.some(item=>finite(item.row.median))?`<polyline class="pi-median-line" points="${points(forecast,'median')}"></polyline>`:'';
    const dots=indexed.map(item=>{const row=item.row,px=x(item.index),py=y(row.expected),title=`${row.season} · ${row.kind==='actual'?'Actual':'Expected'} ${num(row.expected,1)} pts${finite(row.median)?` · Median ${num(row.median,1)}`:''}${finite(row.p25)&&finite(row.p75)?` · IQR ${num(row.p25,1)}–${num(row.p75,1)}`:''}`;return `<g><title>${esc(title)}</title><circle class="pi-chart-point ${row.kind}" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="4"></circle>${finite(row.median)&&Math.abs(row.median-row.expected)>.01?`<circle class="pi-chart-point median" cx="${px.toFixed(1)}" cy="${y(row.median).toFixed(1)}" r="3"></circle>`:''}<text class="pi-season-label" x="${px.toFixed(1)}" y="${height-14}" text-anchor="middle">${esc(row.season)}</text></g>`}).join('');
    const mode=preview?'preview':'full';
    return `<div class="pi-trajectory-frame ${preview?'preview':''}"><div class="pi-trajectory-scroll" data-pi-trajectory="${mode}"><svg class="pi-trajectory-svg" viewBox="0 0 ${width} ${height}" style="min-width:${width}px" role="img" aria-label="Continuous career trajectory from historical actuals into current-season forecast, Year 2, and Year 3">${grid}${band('p10','p90','pi-outer-band')}${band('p25','p75','pi-iqr-band')}${boundary!==null?`<line class="pi-boundary" x1="${boundary.toFixed(1)}" x2="${boundary.toFixed(1)}" y1="${pad.top}" y2="${pad.top+plotH}"></line><text class="pi-phase-label-svg" x="${(boundary+8).toFixed(1)}" y="${pad.top+10}">FORECAST</text><text class="pi-phase-label-svg actual" x="${(boundary-8).toFixed(1)}" y="${pad.top+10}" text-anchor="end">ACTUAL</text>`:''}${actualLine}${expectedLine}${medianLine}${dots}</svg></div><div class="pi-chart-key"><span><i class="actual-line"></i>Actual</span><span><i class="expected-line"></i>Expected</span><span><i class="median-line"></i>Median (P50)</span><span><i class="iqr"></i>IQR (P25–P75)</span><span><i class="outer"></i>P10–P90</span></div></div>`;
  }
  const statLabels={pass_att:'Pass att',pass_cmp:'Completions',pass_yd:'Pass yds',pass_td:'Pass TD',pass_int:'INT',rush_att:'Rush att',rush_yd:'Rush yds',rush_td:'Rush TD',rec_tgt:'Targets',rec:'Receptions',rec_yd:'Rec yds',rec_td:'Rec TD',fum:'Fumbles',fum_lost:'Fumbles lost'};
  function statGrid(stats){return Object.entries(stats||{}).filter(([,value])=>finite(value)).map(([key,value])=>`<span><small>${esc(statLabels[key]||key)}</small><b>${num(value,key.includes('yd')||key.includes('att')||key==='pass_cmp'||key==='rec_tgt'||key==='rec'?0:1)}</b></span>`).join('')}
  function positionStats(row){
    const primary=statGrid(row?.stats||{}),more=statGrid(row?.more_stats||{});
    return `${primary}${more?`<details class="pi-more-stats"><summary>More stats</summary><div class="pi-stat-grid pi-stat-grid-more">${more}</div></details>`:''}`;
  }
  const historyDefinitions={
    passing:{label:'Passing',columns:[['pass_att','Pass att'],['pass_cmp','Comp'],['pass_yd','Pass yds'],['pass_td','Pass TD'],['pass_int','INT']]},
    rushing:{label:'Rushing',columns:[['rush_att','Rush att'],['rush_yd','Rush yds'],['rush_td','Rush TD']]},
    receiving:{label:'Receiving',columns:[['rec_tgt','Targets'],['rec','Rec'],['rec_yd','Rec yds'],['rec_td','Rec TD']]},
    fantasy:{label:'Fantasy',columns:[['fantasy_points','FPTS'],['fantasy_ppg','PPG']]},
  };
  function historicalRows(){return history?.status==='ready'?[...(history.seasons||[])].sort((a,b)=>b.season-a.season):[]}
  function projectedRow(){const row=overview?.forecast?.current_projected_stats;if(!row)return null;return{kind:'projected',...row}}
  function statValue(row,key){
    if(key==='fantasy_points'||key==='fantasy_ppg')return row?.[key];
    return row?.stats?.[key];
  }
  function positionViews(){
    const pos=overview?.player?.position;
    if(pos==='QB')return['passing','rushing','fantasy'];
    if(pos==='RB')return['rushing','receiving','fantasy'];
    if(pos==='WR'||pos==='TE')return['receiving','rushing','fantasy'];
    return['fantasy'];
  }
  function availableStatViews(rows){
    const projected=projectedRow(),candidateRows=projected?[projected,...rows]:rows,views=[];
    for(const key of positionViews()){
      if(key==='fantasy'){views.push(key);continue}
      const def=historyDefinitions[key];
      if(candidateRows.some(row=>def.columns.some(([field])=>finite(statValue(row,field)))))views.push(key);
    }
    return views.length?views:['fantasy'];
  }
  function statsTable(){
    const actual=historicalRows(),projected=projectedRow(),views=availableStatViews(actual);
    if(!historyView||!views.includes(historyView))historyView=views[0];
    const def=historyDefinitions[historyView],rows=[...(projected?[projected]:[]),...actual];
    const segments=`<div class="pi-history-segments" role="tablist" aria-label="Player stat category">${views.map(view=>`<button type="button" data-pi-history-view="${view}" class="${view===historyView?'active':''}">${historyDefinitions[view].label}</button>`).join('')}</div>`;
    const head=`<tr><th>Season</th><th>GP</th>${def.columns.map(([,label])=>`<th>${esc(label)}</th>`).join('')}</tr>`;
    const body=rows.map(row=>{const isProjected=row.kind==='projected',gp=isProjected?row.games_played:row.games_played;return `<tr class="${isProjected?'projected':''}"><td><strong>${row.season}</strong>${isProjected?'<span class="pi-projected-badge">PROJECTED</span>':''}</td><td>${num(gp,0)}</td>${def.columns.map(([key])=>`<td>${num(statValue(row,key),key==='fantasy_ppg'?1:0)}</td>`).join('')}</tr>`}).join('');
    const projectedNote=projected?`<p class="pi-projected-note"><strong>${projected.season} PROJECTED</strong> uses governed Y1 Forecast evidence (${esc(projected.evidence_basis||'basis unavailable')}). Unsupported projected fields remain unavailable; no football stats are inferred from fantasy points.</p>`:'<p class="pi-projected-note unavailable">Current-season governed projected football stats are unavailable.</p>';
    const loading=!history||history.status==='loading'?'<div class="pi-loading-inline"><i></i>Loading historical actuals…</div>':history.status!=='ready'?`<div class="pi-empty pi-empty-compact"><strong>Historical actuals unavailable.</strong><p>${esc(history.message||'No canonical history is available.')}</p></div>`:'';
    return `${projectedNote}${segments}<div class="pi-history-table-wrap"><table class="pi-history-table"><thead>${head}</thead><tbody>${body}</tbody></table></div>${loading}<p class="pi-foot">Historical fantasy scoring uses current league rules. Historical rows are actuals; the cyan current-season row is Forecast authority only.</p>`;
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
    if(Math.abs(gap)<250)return'Broad Market and FSFFL Intrinsic are closely aligned on the shared display ruler.';
    return gap>0?'FSFFL Intrinsic above Broad Market.':'FSFFL Intrinsic below Broad Market.';
  }
  function intrinsicDisplay(v){if(finite(v?.intrinsic_value_index))return idx(v.intrinsic_value_index);if(['queued','running'].includes(v?.intrinsic_status))return'Preparing…';return'Unavailable'}
  function valueGauge(value){const ratio=finite(value)?Math.max(0,Math.min(1,value/10000)):0;return `<span class="pi-value-gauge" aria-hidden="true">${[.2,.4,.6,.8,1].map((threshold,index)=>`<i class="${ratio>=threshold-.12?'on':''}" style="height:${8+index*4}px"></i>`).join('')}</span>`}
  function valueCard(label,value,percentile){
    const shown=finite(value)?idx(value):label==='FSFFL Intrinsic'?intrinsicDisplay(overview?.value||{}):'—';
    const support=finite(percentile)?pct(percentile):label==='FSFFL Intrinsic'?esc(intrinsicReason(overview?.value||{})||'Governed value ready'):'—';
    return `<article class="pi-value-card"><div class="pi-value-card-copy"><small>${esc(label)}</small><strong>${shown}</strong><span>0–10,000 Value Index</span><em>${support}</em></div>${valueGauge(value)}</article>`;
  }
  function valueComparison(){
    const v=overview?.value||{},market=v.broad_market_value_index,intrinsic=v.intrinsic_value_index;
    if(!finite(market)||!finite(intrinsic))return `<div class="pi-compare-card unavailable"><span class="pi-compare-icon">!</span><div><strong>Value comparison unavailable</strong><p>${esc(intrinsicReason(v)||'Both governed lenses must be ready before comparison.')}</p></div></div>`;
    const gap=intrinsic-market,relative=Math.abs(gap)/Math.max(1,(intrinsic+market)/2),aligned=relative<.04,up=gap>0;
    const headline=aligned?'Broad Market and FSFFL Intrinsic are closely aligned.':`FSFFL Intrinsic ${up?'above':'below'} Broad Market.`;
    return `<div class="pi-compare-card"><span class="pi-compare-icon">${aligned?'↔':up?'↑':'↓'}</span><div><strong>${esc(headline)}</strong><p>Both values use the shared 0–10,000 presentation ruler while remaining separate governed lenses. This is not a buy/sell command.</p></div></div>`;
  }
  function projectionCard(){
    const row=y1();
    return `<article class="pi-summary-card"><div><small>Season Projection</small><strong>${num(row?.fantasy_points,1)}</strong><span>fantasy points</span><em>${finite(row?.fantasy_ppg)?`${num(row.fantasy_ppg,1)} PPG`:'PPG unavailable'}</em></div></article>`;
  }
  function overviewCards(){const v=overview?.value||{};return `<div class="pi-summary-grid">${projectionCard()}${valueCard('Broad Market',v.broad_market_value_index,v.broad_market_percentile)}${valueCard('FSFFL Intrinsic',v.intrinsic_value_index,v.intrinsic_percentile)}</div>`}
  function forecastProvenance(){
    const f=overview?.forecast||{},basis=f.current_evidence_basis||'unavailable',fallback=basis==='preseason_baseline';
    return `<div class="pi-provenance ${fallback?'fallback':''}"><strong>${fallback?'Preserved Preseason Forecast fallback':'Current governed Forecast'}</strong><span>Evidence basis: ${esc(basis)} · as of ${esc(f.current_as_of||'—')}</span><span>Sources: ${esc((f.successful_source_ids||[]).join(', ')||'preserved / unavailable')}</span></div>`;
  }

  function captureViewState(){
    const host=sheet();sheetScrollTop=host.scrollTop;
    const trajectory=host.querySelector('[data-pi-trajectory="full"]');
    if(trajectory&&trajectory.scrollWidth>trajectory.clientWidth)careerScrollLeft=trajectory.scrollLeft;
  }
  function positionCareerTrajectory(forceDefault=false){
    const scroller=sheet().querySelector('[data-pi-trajectory="full"]');if(!scroller)return;
    requestAnimationFrame(()=>{const max=Math.max(0,scroller.scrollWidth-scroller.clientWidth);if(forceDefault||careerScrollLeft===null)scroller.scrollLeft=max;else scroller.scrollLeft=Math.min(max,careerScrollLeft);});
  }
  function restoreViewState(){
    const host=sheet();
    host.querySelectorAll('[data-pi-history-view]').forEach(button=>button.addEventListener('click',()=>{historyView=button.dataset.piHistoryView||historyView;captureViewState();render()}));
    const full=host.querySelector('[data-pi-trajectory="full"]');if(full)full.addEventListener('scroll',()=>{careerScrollLeft=full.scrollLeft},{passive:true});
    requestAnimationFrame(()=>{host.scrollTop=sheetScrollTop});
    positionCareerTrajectory(false);
  }
  function marketActions(){
    const ctx=marketContext||{},id=activeId;if(!id)return"";
    const actions=[];
    if(ctx.rosterStatus==="available")actions.push(["waiver","Evaluate add/drop"]);
    else if(ctx.managed===true)actions.push(["shop","Shop in Trade Finder"]);
    else if(ctx.ownerTeamId)actions.push(["target","Target in Trade Finder"],["owner","Open current owner"]);
    if(!actions.length)return"";
    return "<section class='pi-market-actions'><small>Market actions</small><div>"+actions.map(([key,label])=>"<button type='button' class='secondary-button' data-pi-market-action='"+key+"'>"+label+"</button>").join("")+"</div></section>";
  }
  function runMarketAction(action){
    const id=activeId,ctx=marketContext?{...marketContext}:{};if(!id)return;
    close();
    if(action==="waiver"){window.fsfflMarketNorthStar?.openFreeAgent?.(id);return}
    if(action==="shop"){window.fsfflMarketNorthStar?.openTradeFinder?.("shop","player:"+id);return}
    if(action==="target"){window.fsfflMarketNorthStar?.openTradeFinder?.("target","player:"+id);return}
    if(action==="owner"&&ctx.ownerTeamId){window.fsfflMarketNorthStar?.openOwner?.(ctx.ownerTeamId)}
  }

  function render(){
    if(!overview)return;captureViewState();const p=overview.player,v=overview.value||{},projected=overview.forecast?.current_projected_stats||{};
    sheet().innerHTML=`<button class="pi-close" data-pi-close aria-label="Close Player Intelligence">×</button>
      <header class="pi-player-head"><div class="pi-avatar">${esc((p.full_name||'?').split(' ').map(x=>x[0]).slice(0,2).join(''))}</div><div class="pi-player-identity"><p class="eyebrow">Player Intelligence</p><h2>${esc(p.full_name)}</h2><span>${esc(p.position)} · ${esc(p.nfl_team||'FA')} · age ${esc(p.age_years??'—')}</span></div></header>
      <nav class="pi-tabs" role="tablist"><button data-pi-tab="overview" class="${tabClass('overview')}">Overview</button><button data-pi-tab="career" class="${tabClass('career')}">Career & Forecast</button><button data-pi-tab="stats" class="${tabClass('stats')}">Stats</button><button data-pi-tab="methods" class="${tabClass('methods')}">Methods / Evidence</button></nav>
      <div class="pi-tab ${tabClass('overview')}" data-pi-panel="overview">
        ${overviewCards()}
        ${marketActions()}
        ${finite(v.broad_market_value_index)&&finite(v.intrinsic_value_index)?valueComparison():''}
        <details class="pi-method pi-overview-why"><summary>Why this value?</summary><p>Broad Market and FSFFL Intrinsic use the same 0–10,000 presentation ruler but remain separate governed lenses. Percentiles are secondary context; this is not a buy/sell command.</p></details>
        <section class="pi-section pi-trajectory-section"><div class="pi-section-head"><div><small>Trajectory preview</small><h3>Recent actuals → Forecast</h3></div><button type="button" class="pi-drill-button" data-pi-jump="career">Open detail</button></div>${chart(true)}</section>
      </div>
      <div class="pi-tab ${tabClass('career')}" data-pi-panel="career"><section class="pi-section pi-career-hero"><div class="pi-section-head"><div><small>Career & Forecast</small><h3>Career trajectory: Actual → Forecast</h3></div></div>${chart(false)}</section><section class="pi-section"><div class="pi-section-head"><div><small>Forecast details</small><h3>Current season + Y2 / Y3</h3></div></div>${forecastTable()}</section></div>
      <div class="pi-tab ${tabClass('stats')}" data-pi-panel="stats"><section class="pi-section pi-stats-hero"><div class="pi-section-head"><div><small>Stats</small><h3>Projected current season + historical actuals</h3></div></div>${statsTable()}</section></div>
      <div class="pi-tab ${tabClass('methods')}" data-pi-panel="methods">${forecastProvenance()}<div class="pi-method-grid"><article><small>Current Forecast model</small><strong>${esc(overview.forecast?.current_model_version||'—')}</strong><span>Y1 uses the governed current evidence coordinate; Y2/Y3 remain governed vNext outputs.</span></article><article><small>Projected stat evidence</small><strong>${esc((projected.model_versions||[]).join(', ')||'Unavailable')}</strong><span>Sources: ${esc((projected.source_ids||[]).join(', ')||'none')} · basis: ${esc(projected.evidence_basis||'unavailable')}</span></article><article><small>Value presentation</small><strong>${esc(v.value_presentation?.contract_version||'Unavailable')}</strong><span>Shared ruler; Broad Market and Intrinsic remain separate authorities.</span></article><article><small>History scoring</small><strong>${esc(history?.scoring_basis||'Scored under current league rules when loaded')}</strong><span>Historical actuals remain source-backed.</span></article><article><small>Intrinsic readiness</small><strong>${esc(v.intrinsic_status||'unavailable')}</strong><span>${esc(intrinsicReason(v)||v.intrinsic_status_reason||'Governed value available')}</span></article><article><small>Raw Shapley audit</small><strong>${num(v.raw_shapley_marginal_points,1)}</strong><span>Marginal fantasy-point units; not projected points or market price.</span></article></div><p class="pi-foot">Raw Market and raw Shapley quantities are never subtracted. Future Y2/Y3 points come directly from Forecast authority; they are not inferred from Intrinsic. League Market Value remains unavailable by design.</p></div>`;
    bindTabs();restoreViewState();
  }
  function bindTabs(){
    const host=sheet();host.querySelectorAll('[data-pi-tab]').forEach(button=>button.addEventListener('click',()=>{captureViewState();activeTab=button.dataset.piTab||'overview';host.querySelectorAll('[data-pi-tab]').forEach(x=>x.classList.toggle('active',x.dataset.piTab===activeTab));host.querySelectorAll('[data-pi-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.piPanel===activeTab));host.scrollTop=0;if(activeTab==='career')positionCareerTrajectory(careerScrollLeft===null)}));
    const drill=host.querySelector('[data-pi-jump="career"]');if(drill)drill.addEventListener('click',()=>{captureViewState();activeTab='career';sheetScrollTop=0;render();positionCareerTrajectory(careerScrollLeft===null)});host.querySelectorAll('[data-pi-market-action]').forEach(button=>button.addEventListener('click',()=>runMarketAction(button.dataset.piMarketAction)));
  }
  document.addEventListener('click',event=>{const trigger=event.target.closest('[data-player-intelligence-id]');if(!trigger)return;const id=normalizedPlayerId(trigger.dataset.playerIntelligenceId);if(!id)return;const ctx={ownerTeamId:trigger.dataset.piOwnerTeamId||null,ownerTeamName:trigger.dataset.piOwnerTeamName||null,rosterStatus:trigger.dataset.piRosterStatus||null,managed:trigger.dataset.piManaged==='true'||state?.route==='my_team'};event.preventDefault();event.stopPropagation();open(id,ctx)},true);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!ensure().hidden)close()});
  window.fsfflPlayerIntelligence={open,close,version:VERSION};
})();
