/* North Star Market presentation.
 * Reads existing Opportunity Search / Decision / Behavioral outputs only.
 * It does not create candidate ordering, recommendation authority, or acceptance probability.
 */
(function(){
  let queued=false;
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const words=value=>String(value||'').replaceAll('_',' ');
  const initials=value=>String(value||'?').split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join('').toUpperCase();
  const assets=items=>(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean);
  const assetRefs=items=>(items||[]).map(item=>item.asset_ref||item.label).filter(Boolean);
  function opportunityState(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function onMarketRoute(){try{return typeof window.state!=='undefined'?window.state?.route==='opportunities':typeof state!=='undefined'&&state?.route==='opportunities'}catch(_){return false}}
  function rows(){try{return typeof oppTradeRows==='function'?oppTradeRows():opportunityState()?.payload?.trade_discovery?.candidates||[]}catch(_){return[]}}
  function ownerSignal(row){try{const profile=typeof oppBehaviorFor==='function'?oppBehaviorFor(row.counterparty_team_id):null;if(!profile)return null;return{trades:profile.trade_count??0,events:profile.event_count??0}}catch(_){return null}}
  function authorityState(row){
    const authority=String(row?.action_authority||row?.recommendation_authority||'').toLowerCase();
    const shape=String(row?.decision_shape||row?.focal_decision_shape||'').toLowerCase();
    if(authority==='actionable'||authority==='recommended')return{key:'recommended',label:'Recommended',short:'Act',glyph:'✓',detail:'Decision evidence supports action.'};
    if(!row?.bilateral_decision_evaluated)return{key:'needs-eval',label:'Needs full evaluation',short:'Evaluate',glyph:'?',detail:'This is a plausible market match, not yet a recommendation.'};
    if(shape.includes('support')||shape.includes('counter')||shape.includes('review')||authority==='market_test_only')return{key:'investigate',label:'Worth investigating',short:'Inspect',glyph:'↗',detail:'The structure is promising enough to inspect further.'};
    return{key:'match-only',label:'Market match only',short:'Match',glyph:'·',detail:'Search found a structural match, but Decision evidence does not support recommendation language.'};
  }
  function cleanReason(text){return String(text||'').replace(/governed/gi,'current').replace(/authoritative/gi,'current').replace(/decision enrichment/gi,'full evaluation').replace(/search distance/gi,'value distance').replace(/optimized[- ]starter/gi,'starting lineup').replace(/position[- ]strength index/gi,'position strength').replace(/package economics/gi,'package value').replace(/search retained/gi,'This surfaced because').replace(/diagnostic/gi,'initial').trim()}
  function primaryReason(row,authority){
    const target=row.target_position||'Roster';
    if(row.focal_position_strength_rank)return`${target} is a pressure point for you at #${row.focal_position_strength_rank} in the league.`;
    const context=(row.search_context||[]).map(cleanReason).find(Boolean);
    if(context)return context;
    if(typeof row.search_distance==='number')return'The package is close enough in current value to be worth checking.';
    return authority.detail;
  }
  function explanationBullets(row,authority){
    const bullets=[];const target=row.target_position||'This position';
    if(row.focal_position_strength_rank)bullets.push(`${target} is a roster pressure point for you (#${row.focal_position_strength_rank} in the league).`);
    (row.search_context||[]).map(cleanReason).filter(Boolean).forEach(reason=>{if(!bullets.includes(reason))bullets.push(reason)});
    if(typeof row.search_distance==='number')bullets.push('The package is close enough in current value to be worth checking.');
    if(authority.key==='needs-eval')bullets.push('This still needs a full bilateral evaluation.');
    if(authority.key==='match-only')bullets.push('Treat this as a market match, not a recommendation.');
    if(authority.key==='investigate')bullets.push('The current evidence says investigate further before sending anything.');
    if(authority.key==='recommended')bullets.push('The current Decision result supports action.');
    return bullets.slice(0,5);
  }
  function methodsMarkup(row){const distance=typeof row.search_distance==='number'?Math.round(row.search_distance).toLocaleString():'Unavailable';return `<details class="ns-market-methods"><summary>Methods & evidence</summary><p><strong>Current value distance:</strong> ${distance}</p><p>This view presents existing Search, Decision and owner-history evidence. It does not calculate an acceptance probability or create recommendation authority.</p></details>`}
  function packageLine(row){const send=assets(row.send),receive=assets(row.receive);return `<div class="ns-market-package-line"><span><small>Give</small><b>${esc(send.join(' + ')||'—')}</b></span><i aria-hidden="true">→</i><span><small>Get</small><b>${esc(receive.join(' + ')||row.target_position||'—')}</b></span></div>`}
  function card(row,index,featured=false){
    const receive=assets(row.receive),owner=ownerSignal(row),target=row.target_position||'Roster fit',authority=authorityState(row),bullets=explanationBullets(row,authority),reason=primaryReason(row,authority);
    return `<article class="ns-market-card authority-${authority.key}${featured?' featured':''}" data-ns-market-card="${index}">
      <button type="button" class="ns-market-card-main" data-ns-market-eval="${index}" aria-label="Evaluate opportunity for ${esc(receive.join(' and ')||target)}">
        <div class="ns-market-authority-orb" aria-label="${esc(authority.label)}"><strong>${esc(authority.glyph)}</strong><small>${esc(authority.short)}</small></div>
        <div class="ns-market-card-copy"><div class="ns-market-card-top"><span>${esc(target)}</span><b>${esc(authority.label)}</b></div><div class="ns-market-title"><span class="ns-market-identity">${esc(initials(receive[0]||target))}</span><div><small>Acquire</small><h3>${esc(receive.join(' + ')||target)}</h3><p>${esc(row.counterparty_name||'Another franchise')}</p></div></div>${packageLine(row)}<p class="ns-market-reason">${esc(reason)}</p><div class="ns-market-signals">${row.package_shape?`<span>${esc(words(row.package_shape))}</span>`:''}${owner?`<span>${owner.trades} observed trade${owner.trades===1?'':'s'}</span>`:''}</div></div><span class="ns-market-chevron" aria-hidden="true">›</span>
      </button>
      <details class="ns-market-detail"><summary>Why this surfaced</summary><div>${bullets.length?`<ul>${bullets.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:'<p>There is not enough explanatory evidence to summarize this match yet.</p>'}<p class="ns-market-authority-copy">${esc(authority.detail)}</p>${methodsMarkup(row)}</div></details>
    </article>`}
  function featureIndex(all){const lead=opportunityState()?.payload?.trade_discovery?.spotlights?.most_promising_evaluated;if(!lead)return 0;const leadTeam=lead.counterparty_team_id,leadSend=assetRefs(lead.send).join('|'),leadReceive=assetRefs(lead.receive).join('|');const found=all.findIndex(row=>row.counterparty_team_id===leadTeam&&assetRefs(row.send).join('|')===leadSend&&assetRefs(row.receive).join('|')===leadReceive);return found>=0?found:0}
  function radarMarkup(all){const counts={recommended:0,investigate:0,'needs-eval':0,'match-only':0};all.forEach(row=>counts[authorityState(row).key]++);return `<div class="ns-market-radar" aria-label="Market opportunity status"><div><strong>${counts.recommended}</strong><span>Recommended</span></div><div><strong>${counts.investigate}</strong><span>Investigate</span></div><div><strong>${counts['needs-eval']}</strong><span>Need evaluation</span></div><div><strong>${counts['match-only']}</strong><span>Matches only</span></div></div>`}
  function renderDeck(){
    const s=opportunityState(),body=document.querySelector('#opportunity-body');if(!onMarketRoute()||!s||s.tab!=='trades'||!body)return;const all=rows();let deck=body.querySelector('.ns-market-deck');if(!all.length){deck?.remove();return}
    const key=all.map(row=>`${row.counterparty_team_id}:${assetRefs(row.send).join('+')}:${assetRefs(row.receive).join('+')}:${authorityState(row).key}`).join('||');if(deck?.dataset.key===key)return;deck?.remove();deck=document.createElement('section');deck.className='ns-market-deck';deck.dataset.key=key;
    const featured=featureIndex(all);const ordered=[all[featured],...all.filter((_,index)=>index!==featured)].filter(Boolean).slice(0,6);
    deck.innerHTML=`<div class="ns-market-command"><div><p class="eyebrow">Your opportunity board</p><h3>What is worth your attention?</h3><p>Scan the status first. Open a move only when it earns a deeper look.</p></div>${radarMarkup(all)}</div><div class="ns-market-cards">${ordered.map((row,displayIndex)=>card(row,all.indexOf(row),displayIndex===0)).join('')}</div>`;body.prepend(deck);
    deck.querySelectorAll('[data-ns-market-eval]').forEach(button=>button.addEventListener('click',()=>{const index=Number(button.dataset.nsMarketEval),row=all[index];if(row&&typeof runTradeEvaluation==='function')runTradeEvaluation(row)}));
    const table=body.querySelector('.table-wrap');if(table&&!table.closest('.ns-market-exact')){const detail=document.createElement('details');detail.className='ns-market-exact';detail.innerHTML='<summary>View every market match</summary>';table.before(detail);detail.appendChild(table)}
  }
  function syncWaiverWorkflow(){const s=opportunityState(),select=document.querySelector('#opp-waiver-drop');if(!s||!select)return;const addKey=s.waiverAdd?.player_id||null;if(s.nsWaiverAddKey!==addKey){s.nsWaiverAddKey=addKey;s.nsWaiverDropSelection=''}if(select.value!==String(s.nsWaiverDropSelection||''))select.value=String(s.nsWaiverDropSelection||'');if(!select.dataset.nsPersisted){select.dataset.nsPersisted='true';select.addEventListener('change',()=>{s.nsWaiverDropSelection=select.value||''})}const evaluator=select.closest('.opp-waiver-evaluator');if(evaluator){const intro=evaluator.querySelector('.opp-result-head p');if(intro)intro.textContent='Choose who you would cut, then compare the changed roster.'}}
  function simplifyWaiverResult(){const result=document.querySelector('.opp-waiver-result');if(!result||result.classList.contains('ns-waiver-result'))return;result.classList.add('ns-waiver-result');const eyebrow=result.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='Waiver decision';const authority=result.querySelector('.opp-authority-note');if(authority&&!authority.closest('.ns-waiver-methods')){const details=document.createElement('details');details.className='ns-waiver-methods';details.innerHTML='<summary>Methods & evidence</summary>';authority.before(details);details.appendChild(authority)}const count=result.querySelector('.opp-result-head .status-chip');if(count){const methods=result.querySelector('.ns-waiver-methods');if(methods){const meta=document.createElement('p');meta.className='ns-waiver-sim-count';meta.textContent=count.textContent;methods.prepend(meta);count.remove()}}}
  function enhanceResult(){if(!onMarketRoute())return;const result=document.querySelector('.opp-trade-result');if(!result||result.classList.contains('ns-market-result'))return;result.classList.add('ns-market-result');const heading=result.querySelector('.opp-result-head h3');if(heading)heading.insertAdjacentHTML('beforebegin','<span class="ns-market-result-icon" aria-hidden="true">↗</span>');const metrics=result.querySelector('.opp-result-metrics');if(metrics)metrics.setAttribute('aria-label','Changed-roster outcome summary')}
  function simplifyShell(){const panel=document.querySelector('#generic-screen .panel');if(!panel)return;if(!onMarketRoute()||opportunityState()?.payload?.status!=='ready'){panel.classList.remove('ns-market-shell');return}panel.classList.add('ns-market-shell');const eyebrow=panel.querySelector('.panel-header .eyebrow');if(eyebrow)eyebrow.textContent='Opportunities';const title=panel.querySelector('.panel-header h2');if(title)title.textContent='Your market';const lead=panel.querySelector(':scope > .lead');if(lead)lead.textContent='The best current paths for improving this roster.';const summary=panel.querySelector('.opp-summary');if(summary)summary.classList.add('ns-market-summary');const note=panel.querySelector('#opportunity-body > .opp-note');if(note)note.classList.add('ns-market-supporting')}
  function enhance(){queued=false;simplifyShell();if(!onMarketRoute())return;renderDeck();syncWaiverWorkflow();simplifyWaiverResult();enhanceResult()}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  const observer=new MutationObserver(schedule);const start=()=>{observer.observe(document.body,{childList:true,subtree:true});schedule()};
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',start,{once:true});else start();window.addEventListener('fsffl:product-context-updated',schedule);
})();
