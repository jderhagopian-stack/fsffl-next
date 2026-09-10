/* Phase 3 Opportunity -> Trade Center workflow handoff.
 * Presentation/workflow only. Search, Value, Decision, Simulation and ownership
 * authority remain server-owned. The handoff only carries canonical asset refs
 * already returned by Opportunity Search into the existing Trade Center builder.
 */
(function(){
  const workflow={handoff:null};

  function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
  function labels(items){return(items||[]).map(item=>item.label||item.asset_ref).filter(Boolean).join(' + ')||'—'}
  function contextKey(){const context=state?.context||{};return`${context.league_id||''}|${context.team_id||''}|${context.state_id||''}`}
  function rowHandoff(row){const payload=typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState.payload:null;return{
    contextKey:contextKey(),
    leagueId:state?.context?.league_id||null,
    teamId:state?.context?.team_id||null,
    stateId:payload?.league_state_id||state?.context?.state_id||null,
    counterpartyTeamId:row?.counterparty_team_id||null,
    counterpartyName:row?.counterparty_name||null,
    focalAssetRefs:(row?.send||[]).map(item=>item.asset_ref).filter(Boolean),
    counterpartyAssetRefs:(row?.receive||[]).map(item=>item.asset_ref).filter(Boolean),
    sendLabel:labels(row?.send),
    receiveLabel:labels(row?.receive),
  }}
  function clearBanner(){document.querySelector('#trade-workflow-handoff')?.remove()}
  function clearHandoff(){workflow.handoff=null;clearBanner()}
  function handoffStillCurrent(handoff){return Boolean(handoff&&handoff.contextKey===contextKey()&&handoff.leagueId===state?.context?.league_id&&handoff.teamId===state?.context?.team_id)}
  function browserOwnsHandoff(handoff){
    if(!handoffStillCurrent(handoff)||!tradeUiState?.browser)return false;
    if(handoff.stateId&&tradeUiState.browser.state_id&&handoff.stateId!==tradeUiState.browser.state_id)return false;
    const focal=tradeUiState.browser.focal_team?.assets||[];
    const counterparty=(tradeUiState.browser.counterparties||[]).find(team=>team.team_id===handoff.counterpartyTeamId);
    if(!counterparty)return false;
    const focalRefs=new Set(focal.map(item=>item.asset_ref));
    const otherRefs=new Set((counterparty.assets||[]).map(item=>item.asset_ref));
    return handoff.focalAssetRefs.every(ref=>focalRefs.has(ref))&&handoff.counterpartyAssetRefs.every(ref=>otherRefs.has(ref));
  }
  function renderBanner(handoff,valid){
    clearBanner();
    const anchor=document.querySelector('#trade-center-screen .trade-counterparty-row');if(!anchor)return;
    const section=document.createElement('section');section.id='trade-workflow-handoff';section.className=`trade-workflow-handoff${valid?'':' stale'}`;
    section.innerHTML=valid
      ?`<div><p class="eyebrow">From Opportunities</p><h3>Opportunity package loaded</h3><p><strong>You send:</strong> ${esc(handoff.sendLabel)}<br><strong>You receive:</strong> ${esc(handoff.receiveLabel)}${handoff.counterpartyName?`<br><strong>Trade with:</strong> ${esc(handoff.counterpartyName)}`:''}</p><small>Trade Center rechecked the package against current canonical ownership. Edit it freely or analyze it as-is.</small></div><button type="button" class="primary-button" id="trade-handoff-analyze">Analyze this trade</button>`
      :`<div><p class="eyebrow">From Opportunities</p><h3>This opportunity is no longer current</h3><p>The league, managed team, State, counterparty or asset ownership changed before Trade Center could use the package.</p><small>FSFFL did not carry stale assets forward. Return to Opportunities for a current search result.</small></div><button type="button" class="secondary-button" id="trade-handoff-return">Back to Opportunities</button>`;
    anchor.insertAdjacentElement('afterend',section);
    section.querySelector('#trade-handoff-analyze')?.addEventListener('click',()=>qs('#analyze-trade')?.click());
    section.querySelector('#trade-handoff-return')?.addEventListener('click',()=>{clearHandoff();if(typeof setRoute==='function')setRoute('opportunities')});
  }
  async function settleTradeCenter(){
    if(typeof loadTradeCenter==='function')await loadTradeCenter();
    if(tradeUiState?.loading){await new Promise(resolve=>{let tries=0;const timer=setInterval(()=>{tries+=1;if(!tradeUiState.loading||tries>=100){clearInterval(timer);resolve()}},25)})}
  }
  async function openInTradeCenter(row){
    const handoff=rowHandoff(row);
    if(!handoff.counterpartyTeamId||!handoff.focalAssetRefs.length||!handoff.counterpartyAssetRefs.length)return;
    workflow.handoff=handoff;
    tradeUiState.counterpartyTeamId=handoff.counterpartyTeamId;
    tradeUiState.focalSelected=new Set(handoff.focalAssetRefs);
    tradeUiState.counterpartySelected=new Set(handoff.counterpartyAssetRefs);
    if(typeof setRoute==='function')setRoute('trade_center');
    await settleTradeCenter();
    const valid=browserOwnsHandoff(handoff);
    if(!valid){tradeUiState.focalSelected=new Set();tradeUiState.counterpartySelected=new Set();renderTradeDraftSide('focal');renderTradeDraftSide('counterparty');renderTradeAssetList('focal');renderTradeAssetList('counterparty');updateAnalyzeTradeState()}
    renderBanner(handoff,valid);
  }

  function addButton(host,row,label='Open in Trade Center'){
    if(!host||!row||host.querySelector('[data-trade-workflow-handoff]'))return;
    const button=document.createElement('button');button.type='button';button.className='text-button trade-workflow-button';button.dataset.tradeWorkflowHandoff='true';button.textContent=label;button.addEventListener('click',()=>openInTradeCenter(row));host.appendChild(button);
  }
  function enhanceOpportunityRows(){
    if(typeof fsfflOpportunityState==='undefined'||fsfflOpportunityState.tab!=='trades'||typeof oppTradeRows!=='function')return;
    const rows=oppTradeRows();document.querySelectorAll('#opportunity-body .table-wrap tbody tr').forEach((tr,index)=>{const row=rows[index],cell=tr.querySelector('td:last-child');if(row&&cell)addButton(cell,row,'Work in Trade Center')});
  }
  function enhanceSpotlights(){
    if(typeof oppSpotlightRow!=='function')return;
    const market=document.querySelector('#opp-spotlights .opp-spotlight-card.market .opp-spotlight-meta');
    const decision=document.querySelector('#opp-spotlights .opp-spotlight-card.decision .opp-spotlight-meta');
    addButton(market,oppSpotlightRow('market'),'Open deal');addButton(decision,oppSpotlightRow('decision'),'Open deal');
  }
  function enhanceEvaluatedTrade(){
    if(typeof fsfflOpportunityState==='undefined'||!fsfflOpportunityState.tradeEvaluationKey||typeof oppTradeRows!=='function'||typeof oppTradeKey!=='function')return;
    const row=oppTradeRows().find(item=>oppTradeKey(item)===fsfflOpportunityState.tradeEvaluationKey);
    const result=document.querySelector('#opportunity-body .opp-trade-result .opp-result-head');if(row&&result)addButton(result,row,'Work this exact deal');
  }
  function enhanceOpportunities(){enhanceSpotlights();enhanceEvaluatedTrade();enhanceOpportunityRows()}

  if(typeof renderOppBody==='function'){
    const prior=renderOppBody;window.renderOppBody=function(){const result=prior.apply(this,arguments);enhanceOpportunities();return result};
  }
  if(typeof oppInjectSpotlights==='function'){
    const prior=oppInjectSpotlights;window.oppInjectSpotlights=function(){const result=prior.apply(this,arguments);enhanceSpotlights();return result};
  }
  if(typeof loadTradeCenter==='function'){
    const prior=loadTradeCenter;window.loadTradeCenter=async function(){const result=await prior.apply(this,arguments);if(workflow.handoff)renderBanner(workflow.handoff,browserOwnsHandoff(workflow.handoff));return result};
  }

  document.querySelector('#trade-center-screen')?.addEventListener('click',event=>{if(event.target.closest('.asset-option,.draft-chip,#clear-trade')&&!event.target.closest('#trade-workflow-handoff'))clearHandoff()});
  document.querySelector('#counterparty-select')?.addEventListener('change',()=>{if(workflow.handoff)clearHandoff()});

  const style=document.createElement('style');style.id='trade-workflow-handoff-style';style.textContent=`.trade-workflow-handoff{display:flex;justify-content:space-between;gap:16px;align-items:center;border:1px solid var(--accent);border-radius:14px;padding:14px;margin:12px 0;background:#0a1120}.trade-workflow-handoff.stale{border-color:var(--line)}.trade-workflow-handoff h3{margin:2px 0 6px}.trade-workflow-handoff p:not(.eyebrow),.trade-workflow-handoff small{color:var(--muted);font-size:12px;line-height:1.45}.trade-workflow-button{display:block;margin-top:6px;white-space:nowrap}@media(max-width:720px){.trade-workflow-handoff{align-items:stretch;flex-direction:column}.trade-workflow-handoff>button{width:100%}.opp-spotlight-meta{align-items:flex-start;flex-wrap:wrap}}`;document.head.appendChild(style);

  window.fsfflOpenOpportunityInTradeCenter=openInTradeCenter;
})();
