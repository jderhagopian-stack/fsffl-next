/* Phase 3 Opportunity Decision triage.
 * Presentation only. This layer groups already-returned Search candidates by
 * existing governed bilateral Decision evidence. It never changes Search order,
 * computes a composite Opportunity score, or creates action authority.
 */
(function(){
  let triageFilter='all';
  const originalOppTradeRows=typeof oppTradeRows==='function'?oppTradeRows:null;

  function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
  function assetLabels(items){return(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean).join(' + ')||'—'}
  function category(row){
    if(!row?.negotiation_feasibility_evaluated)return'not_evaluated';
    const shape=row.negotiation_feasibility_shape;
    if(shape==='mutual_gain_candidate')return'mutual_gain';
    if(shape==='counterparty_dominated')return'needs_restructure';
    if(shape==='mixed'||shape==='neutral')return'mixed';
    return'incomplete';
  }
  function allSearchRows(){return originalOppTradeRows?originalOppTradeRows():[]}
  function allCandidates(){return fsfflOpportunityState?.payload?.trade_discovery?.candidates||[]}
  function counts(){const result={mutual_gain:0,needs_restructure:0,mixed:0,not_evaluated:0,incomplete:0};allCandidates().forEach(row=>{result[category(row)]+=1});return result}
  function filterLabel(value){return{all:'All candidates',mutual_gain:'Both sides gain',needs_restructure:'Needs restructuring',mixed:'Mixed / neutral',not_evaluated:'Not fully evaluated',incomplete:'Incomplete evidence'}[value]||value}
  function explanation(value){return{mutual_gain:'Governed bilateral feasibility shows calculated gains on both sides. This is worth investigating, but it is not an acceptance forecast.',needs_restructure:'The current package leaves the other team with a calculated loss. Use this as a starting point for a counter, not as a send-ready offer.',mixed:'The bilateral result is mixed or near-neutral. The package may need a different structure before it becomes compelling.',not_evaluated:'Search found a market-plausible structure, but the fast bilateral Decision budget has not evaluated it yet.',incomplete:'Some Decision evidence is incomplete, so FSFFL cannot characterize the bilateral shape confidently.'}[value]||'Search candidates remain in their governed original order.'}
  function triageButton(kind,count){const active=triageFilter===kind;return`<button type="button" class="opp-triage-filter${active?' active':''}" data-opp-triage="${kind}"><strong>${Number(count).toLocaleString()}</strong><span>${esc(filterLabel(kind))}</span></button>`}
  function startHereCard(row){return`<article class="opp-triage-lead"><div><p class="eyebrow">Both sides show calculated gains</p><h3>${esc(assetLabels(row.receive))}</h3><p><strong>You send:</strong> ${esc(assetLabels(row.send))}<br><strong>Trade with:</strong> ${esc(row.counterparty_name||row.counterparty_team_id||'—')}</p><small>${esc((row.search_context||[])[0]||'Preserves the original governed Search ordering within this bilateral subset.')}</small></div><button type="button" class="primary-button" data-opp-triage-open="${esc(typeof oppTradeKey==='function'?oppTradeKey(row):'')}">Work this deal</button></article>`}
  function renderTriage(){
    if(fsfflOpportunityState?.tab!=='trades')return;
    const body=document.querySelector('#opportunity-body');if(!body)return;
    body.querySelector('#opp-decision-triage')?.remove();
    const tally=counts(),mutual=allCandidates().filter(row=>category(row)==='mutual_gain').slice(0,3);
    const section=document.createElement('section');section.id='opp-decision-triage';section.className='opp-decision-triage';
    section.innerHTML=`<div class="opp-triage-head"><div><p class="eyebrow">Decision triage</p><h3>Start with the deals that deserve attention</h3><p>These buckets organize existing bilateral Decision evidence. They do not rerank Search, predict acceptance, or create a recommendation.</p></div><button type="button" class="text-button" data-opp-triage="all">Show all</button></div><div class="opp-triage-filters">${triageButton('mutual_gain',tally.mutual_gain)}${triageButton('needs_restructure',tally.needs_restructure)}${triageButton('mixed',tally.mixed)}${triageButton('not_evaluated',tally.not_evaluated)}${tally.incomplete?triageButton('incomplete',tally.incomplete):''}</div><p class="opp-triage-explanation"><strong>${esc(filterLabel(triageFilter))}:</strong> ${esc(explanation(triageFilter))}</p>${mutual.length?`<div class="opp-triage-start"><div class="opp-triage-start-head"><strong>Start here</strong><span>First ${mutual.length} mutual-gain candidate${mutual.length===1?'':'s'} in the existing Search order</span></div>${mutual.map(startHereCard).join('')}</div>`:'<div class="opp-triage-empty"><strong>No mutual-gain candidate is currently in the evaluated subset.</strong><span>That does not mean a deal is impossible; it means the current evaluated candidates have not produced one yet.</span></div>'}`;
    const note=body.querySelector('.opp-note');if(note)note.insertAdjacentElement('afterend',section);else body.prepend(section);
    section.querySelectorAll('[data-opp-triage]').forEach(button=>button.addEventListener('click',()=>{triageFilter=button.dataset.oppTriage||'all';renderOppBody()}));
    section.querySelectorAll('[data-opp-triage-open]').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.oppTriageOpen;const row=allCandidates().find(item=>typeof oppTradeKey==='function'&&oppTradeKey(item)===key);if(row&&typeof fsfflOpenOpportunityInTradeCenter==='function')fsfflOpenOpportunityInTradeCenter(row)}));
  }

  if(originalOppTradeRows){window.oppTradeRows=function(){const rows=originalOppTradeRows();return triageFilter==='all'?rows:rows.filter(row=>category(row)===triageFilter)}}
  if(typeof renderOppBody==='function'){
    const prior=renderOppBody;window.renderOppBody=function(){const result=prior.apply(this,arguments);renderTriage();return result};
  }
  if(typeof invalidateOpportunityWorkspaceContext==='function'){
    const prior=invalidateOpportunityWorkspaceContext;window.invalidateOpportunityWorkspaceContext=function(){triageFilter='all';return prior.apply(this,arguments)};
  }

  const style=document.createElement('style');style.id='opportunity-decision-triage-style';style.textContent=`.opp-decision-triage{border:1px solid var(--line);border-radius:14px;padding:14px;margin:12px 0;background:#0a1120}.opp-triage-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.opp-triage-head h3{margin:2px 0 5px}.opp-triage-head p:not(.eyebrow),.opp-triage-explanation,.opp-triage-lead p,.opp-triage-lead small,.opp-triage-start-head span,.opp-triage-empty span{color:var(--muted);font-size:12px;line-height:1.45}.opp-triage-filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-top:12px}.opp-triage-filter{display:grid;gap:3px;text-align:left;border:1px solid var(--line);border-radius:10px;padding:10px;background:transparent;color:var(--text)}.opp-triage-filter.active{border-color:var(--accent);background:rgba(255,255,255,.03)}.opp-triage-filter strong{font-size:1.15rem}.opp-triage-filter span{font-size:11px;color:var(--muted)}.opp-triage-explanation{margin:10px 0 0}.opp-triage-start{display:grid;gap:8px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}.opp-triage-start-head{display:flex;justify-content:space-between;gap:10px}.opp-triage-lead{display:flex;justify-content:space-between;gap:12px;align-items:center;border:1px solid var(--line);border-radius:10px;padding:11px}.opp-triage-lead h3{margin:2px 0 5px}.opp-triage-lead p{margin:0 0 4px}.opp-triage-empty{display:grid;gap:3px;margin-top:12px;padding-top:12px;border-top:1px solid var(--line)}@media(max-width:720px){.opp-triage-head,.opp-triage-lead,.opp-triage-start-head{display:grid}.opp-triage-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.opp-triage-lead>button{width:100%}}`;document.head.appendChild(style);
})();
