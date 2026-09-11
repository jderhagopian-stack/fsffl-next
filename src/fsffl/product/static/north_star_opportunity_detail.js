/* North Star Opportunity Detail.
 * Presentation only: composes already-returned Market, Decision, Simulation, Value
 * and Behavioral evidence into a consumer-first hierarchy. It does not create
 * recommendation authority, acceptance probability, Search ordering, or Value truth.
 */
(function(){
  const SAVE_KEY='fsffl.market.savedOpportunities';
  const WATCH_KEY='fsffl.market.watchedPlayers';
  let queued=false;
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const words=value=>String(value||'').replaceAll('_',' ');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const signed=(value,digits=1,suffix='')=>finite(value)?`${value>0?'+':''}${value.toFixed(digits)}${suffix}`:'—';
  const pct=value=>finite(value)?`${(value*100).toFixed(0)}%`:'—';
  const pp=value=>finite(value)?signed(value*100,1,' pp'):'—';
  const assets=items=>(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean);
  const refs=items=>(items||[]).map(item=>item.asset_ref||item.label).filter(Boolean);
  function stateRef(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function tradeRows(){try{return typeof oppTradeRows==='function'?oppTradeRows():stateRef()?.payload?.trade_discovery?.candidates||[]}catch(_){return[]}}
  function key(row){try{return typeof oppTradeKey==='function'?oppTradeKey(row):`${row?.counterparty_team_id||''}:${refs(row?.send).join('+')}:${refs(row?.receive).join('+')}`}catch(_){return''}}
  function selected(){const s=stateRef();if(!s?.nsSelectedTradeKey)return null;return tradeRows().find(row=>key(row)===s.nsSelectedTradeKey)||null}
  function evaluationFor(row){const s=stateRef();return row&&s?.tradeEvaluationKey===key(row)?s.tradeEvaluation:null}
  function localSet(storageKey){try{return new Set(JSON.parse(localStorage.getItem(storageKey)||'[]'))}catch(_){return new Set()}}
  function saveSet(storageKey,set){try{localStorage.setItem(storageKey,JSON.stringify([...set]))}catch(_){}}
  function status(row,result){
    const authority=String(result?.action_authority||row?.action_authority||row?.recommendation_authority||'').toLowerCase();
    const disposition=String(result?.disposition?.disposition||'').toLowerCase();
    const shape=String(row?.decision_shape||row?.focal_decision_shape||'').toLowerCase();
    if(authority==='actionable'||authority==='recommended')return{key:'recommended',label:'Recommended',tone:'positive'};
    if(result&&authority==='market_test_only'&&disposition==='support')return{key:'investigate',label:'Worth investigating',tone:'positive'};
    if(result&&disposition==='counter_or_review')return{key:'investigate',label:'Worth investigating',tone:'neutral'};
    if(!result&&!row?.bilateral_decision_evaluated)return{key:'needs-eval',label:'Needs full evaluation',tone:'warning'};
    if(result&&disposition==='insufficient_evidence')return{key:'needs-eval',label:'Needs full evaluation',tone:'warning'};
    if(shape.includes('support')||shape.includes('counter')||shape.includes('review'))return{key:'investigate',label:'Worth investigating',tone:'neutral'};
    return{key:'match-only',label:'Market match only',tone:'muted'};
  }
  function plainFit(row,result){
    const out=[];
    if(row?.focal_position_strength_rank)out.push(`${row.target_position||'This position'} is a pressure point for your roster (#${row.focal_position_strength_rank} in the league).`);
    if(typeof row?.counterparty_receive_position_strength_index==='number')out.push(`${row.counterparty_name||'The other team'} can use something from the package you would send.`);
    if(typeof row?.market_gap_ratio==='number'||typeof row?.search_distance==='number')out.push('The package is close enough to current market value to merit a closer look.');
    if((row?.send||[]).length>1)out.push(`This consolidates ${row.send.length} outgoing assets into a smaller package.`);
    const fit=result?.behavioral_fit;
    if(fit?.direction&&fit.direction!=='unknown'&&Number(fit.observed_trade_count||0)>0)out.push(`The structure is ${words(fit.direction)} with ${Number(fit.observed_trade_count)} observed trade${Number(fit.observed_trade_count)===1?'':'s'} from this owner.`);
    if(!out.length)out.push('Search found a roster-and-market structure worth inspecting more closely.');
    return out.slice(0,4);
  }
  function focalDelta(result){return(result?.team_deltas||[]).find(item=>item.team_id===result?.focal_team_id)||{}}
  function baselineOutcome(){return stateRef()?.team?.utility?.competitive_outcome||null}
  function impactSpec(result){
    if(!result||result.error)return null;
    const delta=focalDelta(result),c=delta.competitive||{},r=delta.resilience||{},baseline=baselineOutcome();
    const rows=[];
    const add=(keyName,label,before,change,format,scale)=>{if(!finite(change))return;rows.push({key:keyName,label,before:finite(before)?before:null,after:finite(before)?before+change:null,change,format,scale})};
    add('wins','Expected wins',baseline?.expected_wins,c.expected_wins,v=>v.toFixed(1),null);
    add('playoffs','Playoff odds',baseline?.playoff_probability,c.playoff_probability,v=>pct(v),1);
    add('title','Title odds',baseline?.championship_probability??baseline?.first_place_probability,c.championship_probability,v=>pct(v),1);
    if(finite(r.largest_single_player_lineup_drop))rows.push({key:'fragility',label:'Lineup-loss exposure',before:null,after:null,change:r.largest_single_player_lineup_drop,format:v=>signed(v,1),scale:null});
    return rows;
  }
  function impactRow(item){
    const good=item.key==='fragility'?item.change<0:item.change>0,bad=item.key==='fragility'?item.change>0:item.change<0,tone=good?'good':bad?'bad':'neutral';
    let beforeWidth=42,afterWidth=58;
    if(finite(item.before)&&finite(item.after)){
      if(item.scale===1){beforeWidth=Math.max(3,Math.min(100,item.before*100));afterWidth=Math.max(3,Math.min(100,item.after*100))}
      else{const max=Math.max(Math.abs(item.before),Math.abs(item.after),1);beforeWidth=Math.max(6,Math.abs(item.before)/max*100);afterWidth=Math.max(6,Math.abs(item.after)/max*100)}
    }
    const values=finite(item.before)&&finite(item.after)?`<div class="nsod-values"><b>${esc(item.format(item.before))}</b><i>→</i><b>${esc(item.format(item.after))}</b><strong class="${tone}">${item.key==='playoffs'||item.key==='title'?pp(item.change):signed(item.change,1)}</strong></div>`:`<div class="nsod-values"><b>Change</b><strong class="${tone}">${item.key==='playoffs'||item.key==='title'?pp(item.change):signed(item.change,1)}</strong></div>`;
    const bars=finite(item.before)&&finite(item.after)?`<div class="nsod-bars"><span><i style="width:${beforeWidth}%"></i></span><span class="after"><i style="width:${afterWidth}%"></i></span></div>`:'';
    return `<article class="nsod-impact-row"><div><span>${esc(item.label)}</span>${values}</div>${bars}</article>`;
  }
  function impactMarkup(result,loading){
    if(loading)return `<section class="nsod-section nsod-impact"><div class="nsod-section-head"><span>3</span><div><small>Impact</small><h4>Seeing what changes…</h4></div></div><div class="nsod-loading"><i></i><p>Running the changed-roster evaluation.</p></div></section>`;
    const items=impactSpec(result);
    if(!items||!items.length)return `<section class="nsod-section nsod-impact"><div class="nsod-section-head"><span>3</span><div><small>Impact</small><h4>Competitive impact</h4></div></div><div class="nsod-unavailable"><strong>Not available yet</strong><p>Run the full evaluation to see wins, playoff odds, title odds and roster-risk changes.</p></div></section>`;
    return `<section class="nsod-section nsod-impact"><div class="nsod-section-head"><span>3</span><div><small>Impact</small><h4>What changes for your team</h4></div></div><div class="nsod-impact-list">${items.map(impactRow).join('')}</div></section>`;
  }
  function rawReasons(result){return(result?.candidate?.reasons||[]).map(words).filter(Boolean)}
  function blocker(result,row){
    if(!result)return{title:'Needs full bilateral evaluation',detail:'Search found the structure, but the complete changed-roster decision has not finished yet.',tone:'warning'};
    if(result.error)return{title:'Evaluation is unavailable',detail:'The full evaluation did not complete. Retry it or work the package in Trade Center.',tone:'warning'};
    const disposition=String(result?.disposition?.disposition||'').toLowerCase(),authority=String(result?.action_authority||'').toLowerCase(),text=[...rawReasons(result),words(result?.negotiation?.shape||'')].join(' ').toLowerCase();
    if(disposition==='insufficient_evidence')return{title:'Evidence is incomplete',detail:'A required decision input is still missing, so FSFFL is withholding an action call.',tone:'warning'};
    if(/counterparty|bilateral|other team|other_side|other side/.test(text))return{title:'Counterparty does not improve enough',detail:'The other side is the main obstacle at these terms.',tone:'warning'};
    if(/overpay|too expensive|expensive|price.*high|cost/.test(text))return{title:'The package is too expensive',detail:'Your side gives up too much relative to the benefit created.',tone:'warning'};
    if(/underpay|too light|price.*low|short|insufficient package/.test(text))return{title:'The package is too light',detail:'The offer needs more value before it is a credible bilateral structure.',tone:'warning'};
    if(/roster|lineup|fragil|depth/.test(text)&&disposition!=='support')return{title:'Roster construction gets worse',detail:'The package creates a roster or depth cost that is blocking stronger support.',tone:'warning'};
    if(authority==='market_test_only')return{title:'Acceptance context is still uncertain',detail:'The modeled trade can be worth testing, but FSFFL does not have calibrated acceptance authority.',tone:'neutral'};
    if(disposition==='decline')return{title:'The current terms do not help enough',detail:'The returned Decision result does not support pursuing this exact package.',tone:'warning'};
    if(disposition==='counter_or_review')return{title:'The structure needs work',detail:'There is something worth pursuing, but the package should be improved before you act.',tone:'neutral'};
    if(disposition==='no_clear_advantage')return{title:'There is no clear advantage',detail:'The modeled change is too small to make this exact package compelling.',tone:'neutral'};
    if(disposition==='support'&&authority==='actionable')return{title:'No major blocker remains',detail:'The current governed result supports action on this package.',tone:'good'};
    return{title:'Needs more work before action',detail:'The current result does not grant recommendation authority for this exact package.',tone:'neutral'};
  }
  function nextStep(result,row){
    if(!result)return{label:'Run full evaluation',kind:'evaluate',copy:'Finish the bilateral changed-roster evaluation before treating this as a recommendation.'};
    const disposition=String(result?.disposition?.disposition||''),authority=String(result?.action_authority||'');
    if(authority==='actionable')return{label:'Review recommendation',kind:'trade-center',copy:'Open the exact package in Trade Center to inspect the complete decision and make any final edits.'};
    if(disposition==='counter_or_review')return{label:'Restructure in Trade Center',kind:'trade-center',copy:'Work the same package and nearby counters without rebuilding it manually.'};
    if(disposition==='decline')return{label:'Compare alternatives',kind:'trade-center',copy:'Keep the target if you like it, but change the price or structure.'};
    if(disposition==='insufficient_evidence')return{label:'Retry full evaluation',kind:'evaluate',copy:'Re-run the exact package when the missing evidence is available.'};
    if(authority==='market_test_only')return{label:'Work this in Trade Center',kind:'trade-center',copy:'The package is interesting enough to work further, but acceptance is not predicted.'};
    return{label:'Open in Trade Center',kind:'trade-center',copy:'Use the exact candidate as the starting point for deeper bilateral work.'};
  }
  function methods(row,result){
    const reasons=rawReasons(result),fit=result?.behavioral_fit,sim=Number(result?.scenario_simulation_count||0),distance=finite(row?.search_distance)?Math.round(row.search_distance).toLocaleString():'Unavailable',gap=finite(row?.market_gap_ratio)?`${(row.market_gap_ratio*100).toFixed(1)}%`:'Unavailable';
    return `<details class="nsod-methods"><summary>Methods & evidence</summary><div class="nsod-methods-grid"><p><span>Decision disposition</span><strong>${esc(words(result?.disposition?.disposition||'not evaluated'))}</strong></p><p><span>Action authority</span><strong>${esc(words(result?.action_authority||'not evaluated'))}</strong></p><p><span>Simulation</span><strong>${sim?`${sim.toLocaleString()} runs`:'Not available'}</strong></p><p><span>Value context</span><strong>${esc(gap)} relative gap · ${esc(distance)} distance</strong></p><p><span>Behavioral coverage</span><strong>${fit?`${Number(fit.observed_trade_count||0)} observed trades · ${words(fit.evidence_level||'unknown')}`:'Unavailable'}</strong></p><p><span>Negotiation shape</span><strong>${esc(words(result?.negotiation?.shape||row?.package_shape||'unavailable'))}</strong></p></div>${reasons.length?`<div class="nsod-raw-reasons"><span>Exact returned reasons</span><ul>${reasons.map(reason=>`<li>${esc(reason)}</li>`).join('')}</ul></div>`:''}<p class="nsod-method-note">This screen only reorganizes returned Search, Value, Decision, Simulation and owner-history evidence. It does not calculate acceptance odds or upgrade recommendation authority.</p></details>`;
  }
  function render(){
    queued=false;const host=document.querySelector('.ns-market-opportunity-detail');const row=selected();if(!host||!row)return;
    const s=stateRef(),result=evaluationFor(row),loading=Boolean(s?.tradeEvaluationLoading&&s?.tradeEvaluationKey===key(row)),current=status(row,result),fit=plainFit(row,result),stop=blocker(result,row),next=nextStep(result,row),saved=localSet(SAVE_KEY).has(key(row)),watchRef=row.receive?.[0]?.asset_ref||'',watched=watchRef&&localSet(WATCH_KEY).has(watchRef),receive=assets(row.receive).join(' + ')||row.target_position||'Trade opportunity',send=assets(row.send).join(' + ')||'—';
    const renderKey=JSON.stringify([key(row),loading,saved,Boolean(watched),result?.action_authority||'',result?.disposition?.disposition||'',result?.scenario_simulation_count||0,result?.team_deltas||null,result?.candidate?.reasons||null]);
    if(host.dataset.nsodKey===renderKey)return;host.dataset.nsodKey=renderKey;
    host.classList.add('nsod');
    host.innerHTML=`<div class="nsod-top"><button type="button" class="nsod-back" data-nsod-back>‹ Market</button><span class="nsod-status ${current.key}">${esc(current.label)}</span></div>
      <section class="nsod-hero"><div><p class="eyebrow">Opportunity detail</p><h3>Acquire ${esc(receive)}</h3><p>Trade with ${esc(row.counterparty_name||'another franchise')}</p></div><div class="nsod-hero-actions"><button type="button" class="secondary-button" data-nsod-save>${saved?'Saved ✓':'Save'}</button>${watchRef?`<button type="button" class="secondary-button" data-nsod-watch>${watched?'Watching ✓':'Watch'}</button>`:''}<button type="button" class="primary-button" data-nsod-trade>Send to Trade Center</button></div></section>
      <section class="nsod-package"><div><small>You give</small><strong>${esc(send)}</strong></div><i>→</i><div><small>You get</small><strong>${esc(receive)}</strong></div></section>
      <section class="nsod-section nsod-fit"><div class="nsod-section-head"><span>2</span><div><small>Why this fits</small><h4>The roster case</h4></div></div><ul>${fit.map(item=>`<li>${esc(item)}</li>`).join('')}</ul></section>
      ${impactMarkup(result,loading)}
      <section class="nsod-section nsod-blocker ${stop.tone}"><div class="nsod-section-head"><span>4</span><div><small>What is stopping this?</small><h4>${esc(stop.title)}</h4></div></div><p>${esc(stop.detail)}</p></section>
      <section class="nsod-section nsod-next"><div class="nsod-section-head"><span>5</span><div><small>Next step</small><h4>${esc(next.label)}</h4></div></div><p>${esc(next.copy)}</p><button type="button" class="primary-button" data-nsod-next data-kind="${esc(next.kind)}">${esc(next.label)}</button></section>
      ${methods(row,result)}`;
    host.querySelector('[data-nsod-back]')?.addEventListener('click',()=>{s.nsSelectedTradeKey='';if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace()});
    host.querySelector('[data-nsod-save]')?.addEventListener('click',()=>{const set=localSet(SAVE_KEY),k=key(row);set.has(k)?set.delete(k):set.add(k);saveSet(SAVE_KEY,set);host.dataset.nsodKey='';queue()});
    host.querySelector('[data-nsod-watch]')?.addEventListener('click',()=>{if(!watchRef)return;const set=localSet(WATCH_KEY);set.has(watchRef)?set.delete(watchRef):set.add(watchRef);saveSet(WATCH_KEY,set);host.dataset.nsodKey='';queue()});
    const openTrade=()=>{if(typeof window.fsfflOpenOpportunityInTradeCenter==='function')window.fsfflOpenOpportunityInTradeCenter(row)};
    host.querySelector('[data-nsod-trade]')?.addEventListener('click',openTrade);
    host.querySelector('[data-nsod-next]')?.addEventListener('click',event=>{if(event.currentTarget.dataset.kind==='evaluate'&&typeof runTradeEvaluation==='function'){runTradeEvaluation(row);return}openTrade()});
  }
  function queue(){if(queued)return;queued=true;requestAnimationFrame(render)}
  window.addEventListener('fsffl:market-rendered',queue);
  window.addEventListener('fsffl:product-context-updated',queue);
  document.addEventListener('DOMContentLoaded',queue);
  const observer=new MutationObserver(()=>{if(document.querySelector('.ns-market-opportunity-detail'))queue()});
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
