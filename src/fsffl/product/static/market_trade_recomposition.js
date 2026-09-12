/* North Star Market + Trade Center recomposition.
 * Presentation/workflow only. Existing Search, Decision, Value, Simulation and
 * Behavioral outputs remain authoritative. No browser-side analytical truth is created.
 */
(function(){
  let queued=false,tradeInstalled=false,tradeAnalysis=null,tradeSimulation=null,tradeFrontier=null,marketEvalOriginal=null,fullTradeRunning=false;
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const words=value=>String(value||'').replaceAll('_',' ');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const signed=(value,digits=1,suffix='')=>finite(value)?`${value>0?'+':''}${value.toFixed(digits)}${suffix}`:'—';
  const pp=value=>finite(value)?signed(value*100,1,' pp'):'—';

  function marketState(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function marketRows(){try{return typeof oppTradeRows==='function'?oppTradeRows():marketState()?.payload?.trade_discovery?.candidates||[]}catch(_){return[]}}
  function marketKey(row){try{return typeof oppTradeKey==='function'?oppTradeKey(row):''}catch(_){return''}}
  function selectedMarketRow(){const s=marketState(),key=s?.nsSelectedTradeKey;if(!key)return null;return marketRows().find(row=>marketKey(row)===key)||null}

  function simplifyMarketModes(){
    const s=marketState(),nav=document.querySelector('.ns-market-mode-nav');if(!s||!nav)return;
    nav.querySelector('[data-ns-mode="players"]')?.remove();
    const waiver=nav.querySelector('[data-ns-mode="waivers"]');if(waiver){waiver.querySelector('strong').textContent='Waiver / Add-Drop';const small=waiver.querySelector('small');if(small)small.textContent='Find an add and evaluate the roster move'}
    if(s.nsMode==='players'){s.nsMode='waivers';s.tab='free_agents';setTimeout(()=>{if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace()},0)}
  }

  function upgradeMarketFocus(){
    const control=document.querySelector('#opp-posture-control'),select=control?.querySelector('#opp-posture-select');if(!control||!select)return;
    const signature=[...select.options].map(option=>`${option.value}:${option.textContent}`).join('|');if(control.dataset.touchSignature===signature&&control.querySelector('.ns-focus-choice-grid'))return;
    control.dataset.touchSignature=signature;control.querySelector('.ns-focus-choice-grid')?.remove();
    const grid=document.createElement('div');grid.className='ns-focus-choice-grid';
    let group='';[...select.children].forEach(node=>{if(node.tagName==='OPTGROUP'){group=node.label;const heading=document.createElement('p');heading.className='ns-focus-group-label';heading.textContent=group;grid.appendChild(heading);[...node.children].forEach(option=>grid.appendChild(focusButton(option,select)))}else if(node.tagName==='OPTION')grid.appendChild(focusButton(node,select))});
    select.closest('label')?.classList.add('ns-focus-native-hidden');control.querySelector('label')?.insertAdjacentElement('afterend',grid);
  }
  function focusButton(option,select){const button=document.createElement('button');button.type='button';button.className='ns-focus-choice';button.dataset.focusValue=option.value;button.textContent=option.textContent;button.classList.toggle('active',option.selected);button.addEventListener('click',()=>{select.value=option.value;select.dispatchEvent(new Event('change',{bubbles:true}));setTimeout(schedule,0)});return button}

  function installMarketEvaluationBoundary(){
    if(marketEvalOriginal)return;
    const original=typeof window.runTradeEvaluation==='function'?window.runTradeEvaluation:(typeof runTradeEvaluation==='function'?runTradeEvaluation:null);if(!original)return;
    marketEvalOriginal=original;
    const suppressed=function(){return Promise.resolve(null)};
    window.runTradeEvaluation=suppressed;try{runTradeEvaluation=suppressed}catch(_){ }
  }

  function marketKnownImpact(){
    const host=document.querySelector('.ns-market-opportunity-detail.nsod'),row=selectedMarketRow();if(!host||!row)return;
    const impact=host.querySelector('.nsod-impact');if(!impact)return;
    const s=marketState(),result=s?.tradeEvaluationKey===marketKey(row)?s.tradeEvaluation:null;if(result)return;
    const position=row.target_position||'roster need',rank=row.focal_position_strength_rank,gap=finite(row.market_gap_ratio)?`${(row.market_gap_ratio*100).toFixed(1)}%`:'—',shape=words(row.package_shape||((row.send||[]).length>1?'consolidation':'trade'));
    const body=impact.querySelector('.nsod-unavailable');if(body)body.innerHTML=`<strong>What Search already knows</strong><div class="ns-market-known-grid"><span><small>Need addressed</small><b>${esc(position)}${rank?` · #${rank}`:''}</b></span><span><small>Current value gap</small><b>${esc(gap)}</b></span><span><small>Package shape</small><b>${esc(shape)}</b></span></div><p>Season wins and playoff impact belong in Trade Center, where the exact changed roster is evaluated once.</p>`;
    const next=host.querySelector('[data-nsod-next]');if(next){next.dataset.kind='trade-center';next.textContent='Evaluate in Trade Center';const section=next.closest('.nsod-next');section?.querySelector('h4')&&(section.querySelector('h4').textContent='Evaluate in Trade Center');section?.querySelector('p')&&(section.querySelector('p').textContent='Market is for discovery. Trade Center runs the full roster, lineup and season-impact evaluation for this exact package.')}
  }

  function focalAdjusted(result){const id=result?.focal_team_id;return[result?.roster_adjusted_market_net?.side_a,result?.roster_adjusted_market_net?.side_b].find(side=>side?.team_id===id)||null}
  function focalDelta(result){return(result?.team_deltas||[]).find(row=>row.team_id===result?.focal_team_id)||null}
  function disposition(result){return result?.disposition?.action||result?.disposition?.disposition||result?.disposition?.shape||''}
  function actionTitle(action){const labels={accept:'Pursue this trade',support:'Pursue this trade',reject:'Pass on this trade',decline:'Pass on this trade',counter:'Build a counter',counter_or_review:'Build a counter',hold:'Hold',review:'Review before acting',no_clear_advantage:'No clear edge',insufficient_evidence:'Need more evidence'};return labels[action]||words(action)||'Trade evaluation'}
  function selectedLabels(side){try{const team=side==='focal'?tradeUiState.browser?.focal_team:(tradeUiState.browser?.counterparties||[]).find(item=>item.team_id===tradeUiState.counterpartyTeamId),refs=side==='focal'?tradeUiState.focalSelected:tradeUiState.counterpartySelected;return[...(refs||[])].map(ref=>(team?.assets||[]).find(item=>item.asset_ref===ref)?.label||ref).filter(Boolean)}catch(_){return[]}}
  function tradePackage(){return `<div class="ns2-trade-package"><div><small>You give</small><strong>${esc(selectedLabels('focal').join(' + ')||'—')}</strong></div><i>⇄</i><div><small>You get</small><strong>${esc(selectedLabels('counterparty').join(' + ')||'—')}</strong></div></div>`}
  function positionRows(result){const rows=result?.position_strength?.positions||[];return rows.filter(row=>finite(row.expected_points_delta)).sort((a,b)=>Math.abs(b.expected_points_delta)-Math.abs(a.expected_points_delta))}
  function positionMarkup(result){const rows=positionRows(result);if(!rows.length)return'<p class="ns2-muted">Projected starter changes by position are unavailable for this package.</p>';return `<div class="ns2-position-list">${rows.map(row=>`<div><b>${esc(row.position)}</b><span>${finite(row.before_expected_points)?row.before_expected_points.toFixed(1):'—'}</span><i>→</i><span>${finite(row.after_expected_points)?row.after_expected_points.toFixed(1):'—'}</span><strong data-tone="${row.expected_points_delta>0?'good':row.expected_points_delta<0?'risk':'neutral'}">${signed(row.expected_points_delta,1)}</strong></div>`).join('')}</div>`}
  function seasonMarkup(result){const delta=focalDelta(result)?.competitive||{};return `<div class="ns2-season-grid"><div><small>Expected wins</small><strong data-tone="${delta.expected_wins>0?'good':delta.expected_wins<0?'risk':'neutral'}">${signed(delta.expected_wins,2)}</strong></div><div><small>Playoff odds</small><strong data-tone="${delta.playoff_probability>0?'good':delta.playoff_probability<0?'risk':'neutral'}">${pp(delta.playoff_probability)}</strong></div><div><small>First-place odds</small><strong data-tone="${delta.first_place_probability>0?'good':delta.first_place_probability<0?'risk':'neutral'}">${pp(delta.first_place_probability)}</strong></div></div>`}
  function drivers(result){const evidence=result?.disposition?.evidence||{};return{gain:(evidence.material_gains||[])[0],loss:(evidence.material_losses||[])[0]}}
  function counterPoints(){return(tradeFrontier?.points||[]).filter(point=>!point.is_seed&&point.feasibility_shape==='mutual_gain_candidate').slice(0,3)}
  function counterMarkup(){const points=counterPoints();if(!tradeFrontier)return'';if(!points.length)return'<div class="ns2-counter-result"><strong>No nearby mutual-gain package surfaced in this search slice.</strong></div>';return `<div class="ns2-counter-result"><small>Best returned counter paths</small>${points.map(point=>`<article><span>You give <b>${esc((point.focal_assets||[]).map(x=>x.label).join(' + ')||'—')}</b></span><span>You get <b>${esc((point.counterparty_assets||[]).map(x=>x.label).join(' + ')||'—')}</b></span></article>`).join('')}</div>`}

  function ensureTradeRoot(){const panel=document.querySelector('#trade-analysis-empty');if(!panel)return null;let root=panel.querySelector(':scope > div');if(!root){root=document.createElement('div');root.style.width='100%';panel.innerHTML='';panel.appendChild(root)}return root}
  function renderTradeLoading(title,copy){const root=ensureTradeRoot();if(!root)return;root.querySelector('#ns2-trade-room')?.remove();const section=document.createElement('section');section.id='ns2-trade-room';section.className='ns2-trade-room loading';section.innerHTML=`${tradePackage()}<div class="ns2-loading"><i></i><div><strong>${esc(title)}</strong><span>${esc(copy)}</span></div></div>`;root.prepend(section)}
  function renderTradeRoom(){
    const root=ensureTradeRoot(),analysis=tradeAnalysis,sim=tradeSimulation;if(!root||!analysis)return;root.querySelector('#ns2-trade-room')?.remove();const final=Boolean(sim),evidence=sim||analysis,action=disposition(sim),adjusted=focalAdjusted(evidence)||focalAdjusted(analysis),cuts=adjusted?.required_cut_count||0,net=adjusted?.roster_adjusted_market_delta,drive=drivers(sim),counterAction=['counter','counter_or_review','review','no_clear_advantage'].includes(action);const section=document.createElement('section');section.id='ns2-trade-room';section.className='ns2-trade-room';
    section.innerHTML=`<header><div><p class="eyebrow">Trade Center</p><h2>${esc(final?actionTitle(action):'Finishing the trade evaluation')}</h2><p>${final?'One completed view of the package, roster and season impact.':'Roster and value analysis is ready; season impact is the final step.'}</p></div><span class="ns2-status" data-ready="${final?'true':'false'}">${final?'Decision ready':'Evaluating'}</span></header>${tradePackage()}<div class="ns2-key-grid"><article><small>FSFFL Value after cuts</small><strong>${finite(net)?signed(net,0):'—'}</strong><span>${cuts?`${cuts} required cut${cuts===1?'':'s'}`:'No required cuts'}</span></article><article><small>Season impact</small>${final?seasonMarkup(sim):'<strong>Running…</strong><span>Expected wins and playoff odds are being added.</span>'}</article></div><section class="ns2-section"><div class="ns2-section-head"><div><small>Starting lineup</small><h3>Projected starter points by position</h3></div></div>${positionMarkup(analysis)}</section>${final?`<section class="ns2-driver-grid"><article><small>Main upside</small><strong>${esc(words(drive.gain||'No material gain leads the result'))}</strong></article><article><small>Main risk</small><strong>${esc(words(drive.loss||'No major modeled blocker leads the result'))}</strong></article></section><section class="ns2-next"><div><small>What to do next</small><h3>${esc(actionTitle(action))}</h3><p>Counterparty acceptance is not predicted; this action comes from the governed trade disposition for your team.</p></div>${counterAction?'<button type="button" class="primary-button" data-ns2-counter>Build a counter</button>':'<button type="button" class="secondary-button" data-ns2-adjust>Adjust package</button>'}</section><div id="ns2-counter-zone">${counterMarkup()}</div>`:''}<details class="ns2-methods"><summary>Methods & evidence</summary><p>Value: NEXT-3 · Competitive outcomes: NEXT-4 Simulation · Bilateral materiality/disposition: NEXT-5 Trade Decision. No acceptance probability is invented.</p>${(analysis.warnings||[]).length?`<ul>${analysis.warnings.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}</details>`;
    root.prepend(section);section.querySelector('[data-ns2-adjust]')?.addEventListener('click',()=>document.querySelector('.trade-builder-grid')?.scrollIntoView({behavior:'smooth',block:'start'}));section.querySelector('[data-ns2-counter]')?.addEventListener('click',runCounterSearch)
  }

  async function runFullTradeEvaluation(event){
    if(fullTradeRunning)return;if(event){event.preventDefault();event.stopImmediatePropagation()}const analyze=typeof window.analyzeTradeDraft==='function'?window.analyzeTradeDraft:(typeof analyzeTradeDraft==='function'?analyzeTradeDraft:null),simulate=typeof window.simulateTradeDraft==='function'?window.simulateTradeDraft:(typeof simulateTradeDraft==='function'?simulateTradeDraft:null);if(!analyze||!simulate)return;fullTradeRunning=true;tradeAnalysis=null;tradeSimulation=null;tradeFrontier=null;renderTradeLoading('Analyzing roster and package','Checking roster legality, value after cuts and projected lineup changes.');try{await analyze();if(!tradeAnalysis)return;renderTradeLoading('Running season impact','Adding expected wins, playoff odds and first-place odds for the changed roster.');await simulate()}finally{fullTradeRunning=false;const button=document.querySelector('#analyze-trade');if(button){button.textContent='Analyze Trade';button.disabled=!(tradeUiState?.counterpartyTeamId&&tradeUiState?.focalSelected?.size&&tradeUiState?.counterpartySelected?.size)}}}
  async function runCounterSearch(){if(tradeFrontier)return renderTradeRoom();const runner=typeof window.exploreTradeFrontier==='function'?window.exploreTradeFrontier:(typeof exploreTradeFrontier==='function'?exploreTradeFrontier:null);if(!runner)return;const zone=document.querySelector('#ns2-counter-zone');if(zone)zone.innerHTML='<div class="ns2-loading compact"><i></i><div><strong>Searching nearby counter packages…</strong><span>The result will appear here; you do not need to hunt through advanced details.</span></div></div>';await runner()}

  function installTrade(){
    if(tradeInstalled||typeof window.renderTradeAnalysis!=='function'||typeof window.renderTradeSimulationResult!=='function')return;tradeInstalled=true;
    const oldAnalysis=window.renderTradeAnalysis;window.renderTradeAnalysis=function(result){tradeAnalysis=result;tradeSimulation=null;tradeFrontier=null;const out=oldAnalysis.apply(this,arguments);renderTradeRoom();return out};try{renderTradeAnalysis=window.renderTradeAnalysis}catch(_){ }
    const oldSimulation=window.renderTradeSimulationResult;window.renderTradeSimulationResult=function(result){tradeSimulation=result;if(!tradeAnalysis)tradeAnalysis=result;const out=oldSimulation.apply(this,arguments);renderTradeRoom();return out};try{renderTradeSimulationResult=window.renderTradeSimulationResult}catch(_){ }
    if(typeof window.renderTradeFrontierResult==='function'){const oldFrontier=window.renderTradeFrontierResult;window.renderTradeFrontierResult=function(result){tradeFrontier=result;const out=oldFrontier.apply(this,arguments);renderTradeRoom();return out};try{renderTradeFrontierResult=window.renderTradeFrontierResult}catch(_){ }}
    document.addEventListener('click',event=>{const button=event.target?.closest?.('#analyze-trade');if(button)void runFullTradeEvaluation(event)},true)
  }

  function cleanTradeShell(){const screen=document.querySelector('#trade-center-screen');if(!screen)return;screen.classList.add('ns2-trade-center');const hero=screen.querySelector('.trade-hero');if(hero){const h=hero.querySelector('h1'),p=hero.querySelector('.lead');if(h)h.textContent='Build the deal. Get one answer.';if(p)p.textContent='Analyze once to see roster value, lineup changes and season impact together.'}const button=screen.querySelector('#analyze-trade');if(button)button.textContent='Analyze Trade';}

  function enhance(){queued=false;simplifyMarketModes();upgradeMarketFocus();installMarketEvaluationBoundary();marketKnownImpact();installTrade();cleanTradeShell()}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  const observer=new MutationObserver(schedule);observer.observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',schedule);window.addEventListener('fsffl:market-rendered',schedule);window.addEventListener('fsffl:market-intent-changed',schedule);window.addEventListener('fsffl:product-context-updated',schedule);schedule();
})();