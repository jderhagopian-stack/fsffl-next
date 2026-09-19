/* North Star Market presentation.
 * Reads existing Opportunity Search / Decision / Behavioral outputs only.
 * It does not create candidate ordering, recommendation authority, acceptance probability,
 * Value truth, or competitive-state truth. Presentation filters and sort controls operate
 * only on evidence already returned by the governed Market workspace.
 */
(function(){
  let queued=false;
  const SAVE_KEY='fsffl.market.savedOpportunities';
  const WATCH_KEY='fsffl.market.watchedPlayers';
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const words=value=>String(value||'').replaceAll('_',' ');
  const initials=value=>String(value||'?').split(/\s+/).filter(Boolean).slice(0,2).map(part=>part[0]).join('').toUpperCase();
  const assets=items=>(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean);
  const assetRefs=items=>(items||[]).map(item=>item.asset_ref||item.label).filter(Boolean);
  const unique=items=>[...new Set(items.filter(Boolean))];
  function opportunityState(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function onMarketRoute(){try{return typeof window.state!=='undefined'?window.state?.route==='opportunities':typeof state!=='undefined'&&state?.route==='opportunities'}catch(_){return false}}
  function rows(){try{return typeof oppTradeRows==='function'?oppTradeRows():opportunityState()?.payload?.trade_discovery?.candidates||[]}catch(_){return[]}}
  function ownerSignal(row){try{const profile=typeof oppBehaviorFor==='function'?oppBehaviorFor(row.counterparty_team_id):null;if(!profile)return null;return{trades:profile.trade_count??0,events:profile.event_count??0}}catch(_){return null}}
  function rowKey(row){try{return typeof oppTradeKey==='function'?oppTradeKey(row):`${row.counterparty_team_id}:${assetRefs(row.send).join('+')}:${assetRefs(row.receive).join('+')}`}catch(_){return''}}
  function storageSet(key){try{return new Set(JSON.parse(localStorage.getItem(key)||'[]'))}catch(_){return new Set()}}
  function persistSet(key,set){try{localStorage.setItem(key,JSON.stringify([...set]))}catch(_){}}
  function authorityState(row){
    const authority=String(row?.action_authority||row?.recommendation_authority||'').toLowerCase();
    const shape=String(row?.decision_shape||row?.focal_decision_shape||'').toLowerCase();
    if(authority==='actionable'||authority==='recommended')return{key:'recommended',label:'Recommended',short:'Act',glyph:'✓',detail:'Decision evidence supports action.',cta:'Open recommendation'};
    if(!row?.bilateral_decision_evaluated)return{key:'needs-eval',label:'Needs full evaluation',short:'Evaluate',glyph:'?',detail:'This is a plausible market match, not yet a recommendation.',cta:'Run full evaluation'};
    if(shape.includes('support')||shape.includes('counter')||shape.includes('review')||authority==='market_test_only')return{key:'investigate',label:'Worth investigating',short:'Inspect',glyph:'↗',detail:'The structure is promising enough to inspect further.',cta:'Inspect this move'};
    return{key:'match-only',label:'Market match only',short:'Match',glyph:'·',detail:'Search found a structural match, but Decision evidence does not support recommendation language.',cta:'Inspect market match'};
  }
  function plainReasons(row,authority){
    const bullets=[],target=row.target_position||'This position';
    if(row.focal_position_strength_rank)bullets.push(`Targets ${target}, currently #${row.focal_position_strength_rank} on your league-relative position profile.`);
    if(typeof row.counterparty_receive_position_strength_index==='number')bullets.push('What you send includes a position that can help the other roster.');
    if(typeof row.market_gap_ratio==='number'||typeof row.search_distance==='number')bullets.push('The package is close enough in current FSFFL Value to be worth checking.');
    if((row.send||[]).length>1)bullets.push(`This is a consolidation structure: ${row.send.length} assets for one target.`);
    if(authority.key==='needs-eval')bullets.push('It still needs a full bilateral evaluation before FSFFL can recommend action.');
    if(authority.key==='match-only')bullets.push('Treat this as a market match, not a recommendation.');
    if(authority.key==='investigate')bullets.push('The current Decision evidence says investigate further before sending anything.');
    if(authority.key==='recommended')bullets.push('The current Decision result supports action.');
    return unique(bullets).slice(0,5);
  }
  function primaryReason(row,authority){return plainReasons(row,authority)[0]||authority.detail}
  function methodsMarkup(row){
    const distance=typeof row.search_distance==='number'?Math.round(row.search_distance).toLocaleString():'Unavailable';
    const gap=typeof row.market_gap_ratio==='number'?`${(row.market_gap_ratio*100).toFixed(1)}%`:'Unavailable';
    return `<details class="ns-market-methods"><summary>Methods & evidence</summary><p><strong>FSFFL Value distance:</strong> ${distance} · <strong>Relative gap:</strong> ${gap}</p><p>This view presents existing Search, Decision and owner-history evidence. It does not calculate an acceptance probability or create recommendation authority.</p></details>`;
  }
  function packageLine(row){const send=assets(row.send),receive=assets(row.receive);return `<div class="ns-market-package-line"><span><small>You give</small><b>${esc(send.join(' + ')||'—')}</b></span><i aria-hidden="true">→</i><span><small>You get</small><b>${esc(receive.join(' + ')||row.target_position||'—')}</b></span></div>`}
  function card(row,index,featured=false){
    const receive=assets(row.receive),owner=ownerSignal(row),target=row.target_position||'Roster fit',authority=authorityState(row),reason=primaryReason(row,authority),saved=storageSet(SAVE_KEY).has(rowKey(row));
    return `<article class="ns-market-card authority-${authority.key}${featured?' featured':''}" data-ns-market-card="${index}" data-authority="${authority.key}">
      <button type="button" class="ns-market-card-main" data-ns-market-open="${index}" aria-label="${esc(authority.cta)} for ${esc(receive.join(' and ')||target)}">
        <div class="ns-market-authority-orb" aria-label="${esc(authority.label)}"><strong>${esc(authority.glyph)}</strong><small>${esc(authority.short)}</small></div>
        <div class="ns-market-card-copy"><div class="ns-market-card-top"><span>${esc(target)}</span><b>${esc(authority.label)}</b></div><div class="ns-market-title"><span class="ns-market-identity">${esc(initials(receive[0]||target))}</span><div><small>Acquire</small><h3>${esc(receive.join(' + ')||target)}</h3><p>${esc(row.counterparty_name||'Another franchise')}</p></div></div>${packageLine(row)}<p class="ns-market-reason">${esc(reason)}</p><div class="ns-market-card-footer"><div class="ns-market-signals">${row.package_shape?`<span>${esc(words(row.package_shape))}</span>`:''}${owner?`<span>${owner.trades} observed trade${owner.trades===1?'':'s'}</span>`:''}${saved?'<span>Saved</span>':''}</div><strong>${esc(authority.cta)} <i aria-hidden="true">›</i></strong></div></div>
      </button>
    </article>`;
  }
  function featureIndex(all){const lead=opportunityState()?.payload?.trade_discovery?.spotlights?.most_promising_evaluated;if(!lead)return 0;const leadTeam=lead.counterparty_team_id,leadSend=assetRefs(lead.send).join('|'),leadReceive=assetRefs(lead.receive).join('|');const found=all.findIndex(row=>row.counterparty_team_id===leadTeam&&assetRefs(row.send).join('|')===leadSend&&assetRefs(row.receive).join('|')===leadReceive);return found>=0?found:0}
  function radarMarkup(all,active){
    const counts={recommended:0,investigate:0,'needs-eval':0,'match-only':0};all.forEach(row=>counts[authorityState(row).key]++);
    const cells=[['recommended','Recommended'],['investigate','Worth investigating'],['needs-eval','Needs full evaluation'],['match-only','Market match only']];
    return `<div class="ns-market-radar" aria-label="Filter by opportunity status">${cells.map(([key,label])=>`<button type="button" data-ns-status="${key}" class="${active===key?'active':''}"><strong>${counts[key]}</strong><span>${label}</span></button>`).join('')}</div>`;
  }
  function intentFilter(all){
    let intent={intent:'',value:''};try{intent=window.fsfflMarketIntent?.selected?.()||intent}catch(_){ }
    if(!intent.intent)return all;
    if(intent.intent==='consolidate')return all.filter(row=>(row.send||[]).length>1);
    if(!intent.value)return all;
    if(intent.intent==='position')return all.filter(row=>String(row.target_position||'')===String(intent.value));
    if(intent.intent==='shop')return all.filter(row=>(row.send||[]).some(item=>String(item.asset_ref)===String(intent.value)));
    if(intent.intent==='target')return all.filter(row=>(row.receive||[]).some(item=>String(item.asset_ref)===String(intent.value)));
    return all;
  }
  function filterState(s){if(!s.nsFilters)s.nsFilters={position:'',team:'',status:'',deal:'',asset:'',sort:'best-fit'};return s.nsFilters}
  function filteredRows(all,s){
    const f=filterState(s);let result=intentFilter(all);
    if(f.position)result=result.filter(row=>row.target_position===f.position);
    if(f.team)result=result.filter(row=>String(row.counterparty_team_id)===f.team);
    if(f.status)result=result.filter(row=>authorityState(row).key===f.status);
    if(f.deal==='one')result=result.filter(row=>(row.send||[]).length===1);
    if(f.deal==='multi')result=result.filter(row=>(row.send||[]).length>1);
    if(f.asset==='players-only')result=result.filter(row=>[...(row.send||[]),...(row.receive||[])].every(item=>item.asset_kind==='player'));
    if(f.asset==='includes-picks')result=result.filter(row=>[...(row.send||[]),...(row.receive||[])].some(item=>item.asset_kind==='pick'));
    const original=new Map(all.map((row,index)=>[rowKey(row),index]));
    if(f.sort==='most-actionable')result=[...result].sort((a,b)=>({recommended:0,investigate:1,'needs-eval':2,'match-only':3}[authorityState(a).key]-({recommended:0,investigate:1,'needs-eval':2,'match-only':3}[authorityState(b).key])||(original.get(rowKey(a))??0)-(original.get(rowKey(b))??0)));
    if(f.sort==='closest-market')result=[...result].sort((a,b)=>((a.market_gap_ratio??Infinity)-(b.market_gap_ratio??Infinity))||((a.search_distance??Infinity)-(b.search_distance??Infinity)));
    if(f.sort==='biggest-need')result=[...result].sort((a,b)=>((a.focal_position_strength_index??Infinity)-(b.focal_position_strength_index??Infinity))||((b.focal_position_strength_rank??0)-(a.focal_position_strength_rank??0)));
    return result;
  }
  function optionMarkup(items,value){return items.map(item=>`<option value="${esc(item.value)}"${String(item.value)===String(value)?' selected':''}>${esc(item.label)}</option>`).join('')}
  function filtersMarkup(all,s){
    const f=filterState(s),positions=unique(all.map(row=>row.target_position)).sort().map(value=>({value,label:value})),teams=unique(all.map(row=>row.counterparty_team_id)).map(id=>{const row=all.find(item=>String(item.counterparty_team_id)===String(id));return{value:id,label:row?.counterparty_name||id}}).sort((a,b)=>a.label.localeCompare(b.label));
    return `<div class="ns-market-filterbar"><label><span>Position</span><select data-ns-filter="position"><option value="">All</option>${optionMarkup(positions,f.position)}</select></label><label><span>Team / owner</span><select data-ns-filter="team"><option value="">All</option>${optionMarkup(teams,f.team)}</select></label><label><span>Status</span><select data-ns-filter="status"><option value="">All</option>${optionMarkup([{value:'recommended',label:'Recommended'},{value:'investigate',label:'Worth investigating'},{value:'needs-eval',label:'Needs full evaluation'},{value:'match-only',label:'Market match only'}],f.status)}</select></label><label><span>Deal size</span><select data-ns-filter="deal"><option value="">Any</option>${optionMarkup([{value:'one',label:'1-for-1'},{value:'multi',label:'Consolidation'}],f.deal)}</select></label><label><span>Assets</span><select data-ns-filter="asset"><option value="">Any</option>${optionMarkup([{value:'players-only',label:'Players only'},{value:'includes-picks',label:'Includes picks'}],f.asset)}</select></label><label class="ns-market-sort"><span>Sort</span><select data-ns-filter="sort">${optionMarkup([{value:'best-fit',label:'Best fit / current Search order'},{value:'most-actionable',label:'Most actionable'},{value:'closest-market',label:'Closest market match'},{value:'biggest-need',label:'Biggest need addressed'}],f.sort)}</select></label></div>`;
  }
  function detailMarkup(row,index){
    if(!row)return'';const authority=authorityState(row),owner=ownerSignal(row),bullets=plainReasons(row,authority),key=rowKey(row),saved=storageSet(SAVE_KEY).has(key),watchRef=row.receive?.[0]?.asset_ref||'',watched=watchRef&&storageSet(WATCH_KEY).has(watchRef);
    return `<section class="ns-market-opportunity-detail" data-detail-key="${esc(key)}"><div class="ns-market-detail-head"><button type="button" class="ns-market-back" data-ns-close-detail>‹ Back to opportunities</button><span class="ns-market-status authority-${authority.key}">${esc(authority.label)}</span></div><div class="ns-market-detail-hero"><div><p class="eyebrow">Opportunity detail</p><h3>${esc(assets(row.receive).join(' + ')||row.target_position||'Trade opportunity')}</h3><p>${esc(row.counterparty_name||'Counterparty')} · ${esc(authority.detail)}</p></div><div class="ns-market-detail-actions"><button type="button" class="secondary-button" data-ns-save="${index}">${saved?'Saved ✓':'Save'}</button>${watchRef?`<button type="button" class="secondary-button" data-ns-watch="${index}">${watched?'Watching ✓':'Watch target'}</button>`:''}<button type="button" class="primary-button" data-ns-trade-center="${index}">Send to Trade Center</button></div></div>${packageLine(row)}<div class="ns-market-detail-grid"><div><small>Roster fit</small><strong>${esc(primaryReason(row,authority))}</strong></div><div><small>Decision status</small><strong>${esc(authority.label)}</strong></div><div><small>Counterparty context</small><strong>${owner?`${owner.trades} observed trade${owner.trades===1?'':'s'}`:'Owner history unavailable'}</strong></div><div><small>Market context</small><strong>${typeof row.market_gap_ratio==='number'?`${(row.market_gap_ratio*100).toFixed(1)}% relative value gap`:'Value gap unavailable'}</strong></div></div><div class="ns-market-detail-why"><h4>Why this surfaced</h4><ul>${bullets.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>${methodsMarkup(row)}</div><div class="ns-market-detail-result"><div class="ns-market-eval-loading">${opportunityState()?.tradeEvaluationLoading&&opportunityState()?.tradeEvaluationKey===key?'Running full changed-roster evaluation…':'Full evaluation will appear here when available.'}</div></div></section>`;
  }
  function modeMarkup(s){const mode=s.nsMode||(s.tab==='free_agents'?'players':'opportunities');return `<nav class="ns-market-mode-nav" aria-label="Market mode"><button type="button" data-ns-mode="opportunities" class="${mode==='opportunities'?'active':''}"><strong>Opportunities</strong><small>Personalized trade discovery</small></button><button type="button" data-ns-mode="players" class="${mode==='players'?'active':''}"><strong>Players</strong><small>Browse available talent</small></button><button type="button" data-ns-mode="waivers" class="${mode==='waivers'?'active':''}"><strong>Waivers / Add-Drop</strong><small>Evaluate roster moves</small></button></nav>`}
  function wireModeNav(s){document.querySelectorAll('[data-ns-mode]').forEach(button=>button.addEventListener('click',()=>{const mode=button.dataset.nsMode;s.nsMode=mode;s.query='';s.nsSelectedTradeKey='';if(mode==='opportunities')s.tab='trades';else s.tab='free_agents';if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace()}))}
  function renderModeNav(){const s=opportunityState(),panel=document.querySelector('#generic-screen .panel');if(!s||!panel||!onMarketRoute())return;let nav=panel.querySelector('.ns-market-mode-nav');const markup=modeMarkup(s);if(nav){if(nav.outerHTML!==markup)nav.outerHTML=markup}else{const lead=panel.querySelector(':scope > .lead');if(lead)lead.insertAdjacentHTML('afterend',markup)}wireModeNav(s)}
  function renderDeck(){
    const s=opportunityState(),body=document.querySelector('#opportunity-body');if(!onMarketRoute()||!s||s.tab!=='trades'||!body)return;const all=rows();let deck=body.querySelector('.ns-market-deck');if(!all.length){deck?.remove();return}
    const filtered=filteredRows(all,s),visibleCount=s.nsVisibleCount||4,visible=filtered.slice(0,visibleCount),selectedIndex=all.findIndex(row=>rowKey(row)===s.nsSelectedTradeKey),selected=selectedIndex>=0?all[selectedIndex]:null,f=filterState(s);
    const feature=featureIndex(all),key=[...all.map(row=>`${rowKey(row)}:${authorityState(row).key}`),JSON.stringify(f),s.nsVisibleCount||4,s.nsSelectedTradeKey||'',JSON.stringify(window.fsfflMarketIntent?.selected?.()||{})].join('||');if(deck?.dataset.key===key)return;deck?.remove();deck=document.createElement('section');deck.className='ns-market-deck';deck.dataset.key=key;
    deck.innerHTML=`${detailMarkup(selected,selectedIndex)}<div class="ns-market-command"><div><p class="eyebrow">Your opportunity board</p><h3>What is worth your attention?</h3><p>Curated first. Status tells you what each move is—and what it is not.</p></div>${radarMarkup(all,f.status)}</div>${filtersMarkup(all,s)}<div class="ns-market-cards">${visible.length?visible.map(row=>card(row,all.indexOf(row),all.indexOf(row)===feature)).join(''):'<div class="ns-market-no-results"><strong>No opportunities match these filters.</strong><span>Clear a filter or change your Market focus.</span></div>'}</div><div class="ns-market-board-actions">${filtered.length>visible.length?`<button type="button" class="secondary-button" data-ns-see-more>See more (${filtered.length-visible.length})</button>`:''}<button type="button" class="text-button" data-ns-unevaluated>View all unevaluated</button><button type="button" class="text-button" data-ns-matches>Browse market matches</button></div>`;body.prepend(deck);
    deck.querySelectorAll('[data-ns-market-open]').forEach(button=>button.addEventListener('click',()=>{const index=Number(button.dataset.nsMarketOpen),row=all[index];if(!row)return;s.nsSelectedTradeKey=rowKey(row);renderDeck();if(typeof runTradeEvaluation==='function')runTradeEvaluation(row)}));
    deck.querySelectorAll('[data-ns-filter]').forEach(select=>select.addEventListener('change',()=>{filterState(s)[select.dataset.nsFilter]=select.value;s.nsVisibleCount=4;s.nsSelectedTradeKey='';renderDeck()}));
    deck.querySelectorAll('[data-ns-status]').forEach(button=>button.addEventListener('click',()=>{f.status=f.status===button.dataset.nsStatus?'':button.dataset.nsStatus;s.nsVisibleCount=4;s.nsSelectedTradeKey='';renderDeck()}));
    deck.querySelector('[data-ns-see-more]')?.addEventListener('click',()=>{s.nsVisibleCount=visibleCount+4;renderDeck()});
    deck.querySelector('[data-ns-unevaluated]')?.addEventListener('click',()=>{f.status='needs-eval';s.nsVisibleCount=12;s.nsSelectedTradeKey='';renderDeck()});
    deck.querySelector('[data-ns-matches]')?.addEventListener('click',()=>{f.status='match-only';s.nsVisibleCount=12;s.nsSelectedTradeKey='';renderDeck()});
    deck.querySelector('[data-ns-close-detail]')?.addEventListener('click',()=>{s.nsSelectedTradeKey='';renderDeck()});
    deck.querySelectorAll('[data-ns-save]').forEach(button=>button.addEventListener('click',()=>{const row=all[Number(button.dataset.nsSave)],set=storageSet(SAVE_KEY),key=rowKey(row);set.has(key)?set.delete(key):set.add(key);persistSet(SAVE_KEY,set);renderDeck()}));
    deck.querySelectorAll('[data-ns-watch]').forEach(button=>button.addEventListener('click',()=>{const row=all[Number(button.dataset.nsWatch)],ref=row?.receive?.[0]?.asset_ref;if(!ref)return;const set=storageSet(WATCH_KEY);set.has(ref)?set.delete(ref):set.add(ref);persistSet(WATCH_KEY,set);renderDeck()}));
    deck.querySelectorAll('[data-ns-trade-center]').forEach(button=>button.addEventListener('click',()=>{const row=all[Number(button.dataset.nsTradeCenter)];if(row&&typeof window.fsfflOpenOpportunityInTradeCenter==='function')window.fsfflOpenOpportunityInTradeCenter(row)}));
    const table=body.querySelector('.table-wrap');if(table&&!table.closest('.ns-market-exact')){const detail=document.createElement('details');detail.className='ns-market-exact';detail.innerHTML='<summary>View every market match</summary>';table.before(detail);detail.appendChild(table)}
    window.dispatchEvent(new CustomEvent('fsffl:market-rendered'));
  }
  function tuneFreeAgentMode(){
    const s=opportunityState();if(!s||s.tab!=='free_agents')return;const mode=s.nsMode||'players',body=document.querySelector('#opportunity-body'),note=body?.querySelector('.opp-note');if(!body)return;
    body.classList.toggle('ns-market-players-mode',mode==='players');body.classList.toggle('ns-market-waivers-mode',mode==='waivers');
    if(note){const strong=note.querySelector('strong'),span=note.querySelector('span');if(strong)strong.textContent=mode==='waivers'?'Waiver / add-drop workspace':'Best available players';if(span)span.textContent=mode==='waivers'?'Choose an available player, then compare the exact add/drop against your current roster.':'Browse unowned players as a market. Open an add/drop evaluation when a player is worth a roster decision.'}
    body.querySelectorAll('[data-waiver-add]').forEach(button=>button.textContent=mode==='waivers'?'Evaluate add/drop':'Open player');
  }
  function syncWaiverWorkflow(){const s=opportunityState(),select=document.querySelector('#opp-waiver-drop');if(!s||!select)return;const addKey=s.waiverAdd?.player_id||null;if(s.nsWaiverAddKey!==addKey){s.nsWaiverAddKey=addKey;s.nsWaiverDropSelection=''}if(select.value!==String(s.nsWaiverDropSelection||''))select.value=String(s.nsWaiverDropSelection||'');if(!select.dataset.nsPersisted){select.dataset.nsPersisted='true';select.addEventListener('change',()=>{s.nsWaiverDropSelection=select.value||''})}const evaluator=select.closest('.opp-waiver-evaluator');if(evaluator){const intro=evaluator.querySelector('.opp-result-head p');if(intro)intro.textContent='Choose who you would cut, then compare the changed roster.'}}
  function simplifyWaiverResult(){const result=document.querySelector('.opp-waiver-result');if(!result||result.classList.contains('ns-waiver-result'))return;result.classList.add('ns-waiver-result');const eyebrow=result.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='Waiver decision';const authority=result.querySelector('.opp-authority-note');if(authority&&!authority.closest('.ns-waiver-methods')){const details=document.createElement('details');details.className='ns-waiver-methods';details.innerHTML='<summary>Methods & evidence</summary>';authority.before(details);details.appendChild(authority)}const count=result.querySelector('.opp-result-head .status-chip');if(count){const methods=result.querySelector('.ns-waiver-methods');if(methods){const meta=document.createElement('p');meta.className='ns-waiver-sim-count';meta.textContent=count.textContent;methods.prepend(meta);count.remove()}}}
  function renderAlternatives(result,host){const rows=result?.negotiation?.alternatives||result?.negotiation?.counteroffers||result?.alternatives;if(!host||!Array.isArray(rows)||!rows.length||host.querySelector('.ns-market-alternatives'))return;const block=document.createElement('div');block.className='ns-market-alternatives';block.innerHTML=`<h4>Alternative packages / counters</h4><div>${rows.slice(0,4).map(item=>`<p>${esc(item.label||item.summary||item.description||String(item))}</p>`).join('')}</div>`;host.appendChild(block)}
  function enhanceResult(){
    if(!onMarketRoute())return;const result=document.querySelector('.opp-trade-result');if(!result)return;result.classList.add('ns-market-result');const heading=result.querySelector('.opp-result-head h3');if(heading&&!result.querySelector('.ns-market-result-icon'))heading.insertAdjacentHTML('beforebegin','<span class="ns-market-result-icon" aria-hidden="true">↗</span>');const metrics=result.querySelector('.opp-result-metrics');if(metrics)metrics.setAttribute('aria-label','Changed-roster outcome summary');
    const slot=document.querySelector('.ns-market-opportunity-detail .ns-market-detail-result');if(slot&&result.parentElement!==slot){slot.innerHTML='';slot.appendChild(result)}
    renderAlternatives(opportunityState()?.tradeEvaluation,slot);
  }
  function simplifyShell(){
    const panel=document.querySelector('#generic-screen .panel');if(!panel)return;if(!onMarketRoute()||opportunityState()?.payload?.status!=='ready'){panel.classList.remove('ns-market-shell');return}panel.classList.add('ns-market-shell');const eyebrow=panel.querySelector('.panel-header .eyebrow');if(eyebrow)eyebrow.textContent='Market';const title=panel.querySelector('.panel-header h2');if(title)title.textContent='Your market';const lead=panel.querySelector(':scope > .lead');if(lead)lead.textContent='Set your intent, scan a curated board, then open only the moves worth deeper work.';const summary=panel.querySelector('.opp-summary');if(summary)summary.classList.add('ns-market-summary');const note=panel.querySelector('#opportunity-body > .opp-note');if(note)note.classList.add('ns-market-supporting');const search=panel.querySelector('#opp-search');if(search)search.placeholder=opportunityState()?.tab==='trades'?'Search this opportunity board':'Search available players';const legacyTabs=panel.querySelector('.opp-tabs');if(legacyTabs)legacyTabs.classList.add('ns-market-legacy-tabs')
  }
  function enhance(){queued=false;simplifyShell();if(!onMarketRoute())return;renderModeNav();renderDeck();tuneFreeAgentMode();syncWaiverWorkflow();simplifyWaiverResult();enhanceResult()}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  const observer=new MutationObserver(schedule);const start=()=>{observer.observe(document.body,{childList:true,subtree:true});schedule()};
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('fsffl:product-context-updated',schedule);window.addEventListener('fsffl:market-intent-changed',schedule);
})();
