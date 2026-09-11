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
  function state(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function onMarketRoute(){try{return typeof window.state!=='undefined'?window.state?.route==='opportunities':typeof state!=='undefined'&&state?.route==='opportunities'}catch(_){return false}}
  function rows(){try{return typeof oppTradeRows==='function'?oppTradeRows():state()?.payload?.trade_discovery?.candidates||[]}catch(_){return[]}}
  function assetMarkup(items,kind){const list=assets(items);return list.length?`<div class="ns-market-assets ${kind}">${list.map(label=>`<span><i>${esc(initials(label))}</i><b>${esc(label)}</b></span>`).join('')}</div>`:'<span class="ns-market-empty">No asset exposed</span>'}
  function decisionTone(row){if(!row?.bilateral_decision_evaluated)return'diagnostic';const shape=String(row.decision_shape||'').toLowerCase();if(shape.includes('support'))return'support';if(shape.includes('decline'))return'decline';return'review'}
  function decisionLabel(row){if(!row?.bilateral_decision_evaluated)return'Needs full evaluation';return words(row.decision_shape||'Decision evaluated')}
  function ownerSignal(row){try{const profile=typeof oppBehaviorFor==='function'?oppBehaviorFor(row.counterparty_team_id):null;if(!profile)return null;return{trades:profile.trade_count??0,events:profile.event_count??0}}catch(_){return null}}
  function card(row,index,featured=false){const receive=assets(row.receive),tone=decisionTone(row),owner=ownerSignal(row),target=row.target_position||'Roster fit';return `<article class="ns-market-card ${tone}${featured?' featured':''}" data-ns-market-card="${index}">
    <button type="button" class="ns-market-card-main" data-ns-market-eval="${index}" aria-label="Evaluate opportunity for ${esc(receive.join(' and ')||target)}">
      <div class="ns-market-card-top"><span class="ns-market-target">${esc(target)}</span><span class="ns-market-decision">${esc(decisionLabel(row))}</span></div>
      <div class="ns-market-title"><span class="ns-market-identity">${esc(initials(receive[0]||target))}</span><div><small>Acquire</small><h3>${esc(receive.join(' + ')||target)}</h3><p>From ${esc(row.counterparty_name||'another franchise')}</p></div><b aria-hidden="true">›</b></div>
      <div class="ns-market-package"><div><small>You send</small>${assetMarkup(row.send,'send')}</div><div><small>You receive</small>${assetMarkup(row.receive,'receive')}</div></div>
      <div class="ns-market-signals"><span>${row.package_shape?esc(words(row.package_shape)):'Trade structure'}</span>${row.focal_position_strength_rank?`<span>${esc(target)} need #${row.focal_position_strength_rank}</span>`:''}${owner?`<span>${owner.trades} observed trade${owner.trades===1?'':'s'}</span>`:'<span>Owner history unavailable</span>'}</div>
    </button>
    <details class="ns-market-detail"><summary>Why this surfaced</summary><div>${(row.search_context||[]).length?`<ul>${row.search_context.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:'<p>Search context is not available for this candidate.</p>'}<p><strong>Value distance:</strong> ${typeof row.search_distance==='number'?Math.round(row.search_distance).toLocaleString():'—'} · diagnostic Search evidence, not an acceptance score.</p></div></details>
  </article>`}
  function featureIndex(all){const lead=state()?.payload?.trade_discovery?.spotlights?.most_promising_evaluated;if(!lead)return 0;const leadTeam=lead.counterparty_team_id,leadSend=assetRefs(lead.send).join('|'),leadReceive=assetRefs(lead.receive).join('|');const found=all.findIndex(row=>row.counterparty_team_id===leadTeam&&assetRefs(row.send).join('|')===leadSend&&assetRefs(row.receive).join('|')===leadReceive);return found>=0?found:0}
  function renderDeck(){const s=state(),body=document.querySelector('#opportunity-body');if(!onMarketRoute()||!s||s.tab!=='trades'||!body)return;const all=rows();let deck=body.querySelector('.ns-market-deck');if(!all.length){deck?.remove();return}const key=all.map(row=>`${row.counterparty_team_id}:${assetRefs(row.send).join('+')}:${assetRefs(row.receive).join('+')}`).join('||');if(deck?.dataset.key===key)return;deck?.remove();deck=document.createElement('section');deck.className='ns-market-deck';deck.dataset.key=key;const featured=featureIndex(all);const ordered=[all[featured],...all.filter((_,index)=>index!==featured)].filter(Boolean).slice(0,8);deck.innerHTML=`<div class="ns-market-head"><div><p class="eyebrow">Personalized market</p><h3>Moves worth your attention.</h3><p>Start with the opportunity. Open the evidence only when you need it.</p></div><span>${all.length} current trade test${all.length===1?'':'s'}</span></div><div class="ns-market-cards">${ordered.map((row,displayIndex)=>card(row,all.indexOf(row),displayIndex===0)).join('')}</div>`;body.prepend(deck);
    deck.querySelectorAll('[data-ns-market-eval]').forEach(button=>button.addEventListener('click',()=>{const index=Number(button.dataset.nsMarketEval),row=all[index];if(row&&typeof runTradeEvaluation==='function')runTradeEvaluation(row)}));
    const table=body.querySelector('.table-wrap');if(table&&!table.closest('.ns-market-exact')){const detail=document.createElement('details');detail.className='ns-market-exact';detail.innerHTML='<summary>See every candidate and exact Search evidence</summary>';table.before(detail);detail.appendChild(table)}
  }
  function enhanceResult(){if(!onMarketRoute())return;const result=document.querySelector('.opp-trade-result');if(!result||result.classList.contains('ns-market-result'))return;result.classList.add('ns-market-result');const heading=result.querySelector('.opp-result-head h3');if(heading)heading.insertAdjacentHTML('beforebegin','<span class="ns-market-result-icon" aria-hidden="true">↗</span>');const metrics=result.querySelector('.opp-result-metrics');if(metrics)metrics.setAttribute('aria-label','Changed-roster outcome summary')}
  function simplifyShell(){const panel=document.querySelector('#generic-screen .panel');if(!panel)return;if(!onMarketRoute()||state()?.payload?.status!=='ready'){panel.classList.remove('ns-market-shell');return}panel.classList.add('ns-market-shell');const title=panel.querySelector('.panel-header h2');if(title&&title.textContent!=='Your market')title.textContent='Your market';const lead=panel.querySelector(':scope > .lead'),leadCopy='Trade ideas shaped by your roster, the other franchise, and current FSFFL evidence.';if(lead&&lead.textContent!==leadCopy)lead.textContent=leadCopy;const summary=panel.querySelector('.opp-summary');if(summary&&!summary.classList.contains('ns-market-summary'))summary.classList.add('ns-market-summary');const note=panel.querySelector('#opportunity-body > .opp-note');if(note&&!note.classList.contains('ns-market-supporting'))note.classList.add('ns-market-supporting')}
  function enhance(){queued=false;simplifyShell();if(!onMarketRoute())return;renderDeck();enhanceResult()}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  const observer=new MutationObserver(schedule);
  const start=()=>{observer.observe(document.body,{childList:true,subtree:true});schedule()};
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('fsffl:product-context-updated',schedule);
})();
