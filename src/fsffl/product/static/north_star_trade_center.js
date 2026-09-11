/* Phase 3 North Star Trade Center.
 * Presentation only. Reads returned Trade Decision, Value, roster, Simulation,
 * Behavioral and price-frontier evidence; creates no new model truth.
 */
(function(){
  let lastAnalysis=null,lastSimulation=null,lastFrontier=null,installed=false;
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const words=value=>String(value||'').replaceAll('_',' ');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const signed=(value,digits=1,suffix='')=>finite(value)?`${value>0?'+':''}${value.toFixed(digits)}${suffix}`:'—';
  const pctPoints=value=>finite(value)?signed(value*100,1,' pp'):'—';
  const actionLabels={accept:'Pursue this trade',support:'Pursue this trade',reject:'Do not make this trade',decline:'Do not make this trade',counter:'Build a counter',counter_or_review:'Counter or review',hold:'Hold',review:'Review before acting',no_clear_advantage:'No clear advantage',insufficient_evidence:'Not enough evidence to act'};

  function side(result,group,teamId){return[result?.[group]?.side_a,result?.[group]?.side_b].find(item=>item?.team_id===teamId)||null}
  function adjusted(result,teamId){return[result?.roster_adjusted_market_net?.side_a,result?.roster_adjusted_market_net?.side_b].find(item=>item?.team_id===teamId)||null}
  function simRow(result,teamId){return(result?.team_deltas||[]).find(item=>item?.team_id===teamId)||null}
  function disposition(result){return result?.disposition?.action||result?.disposition?.disposition||result?.disposition?.shape||''}
  function selectedLabels(kind){
    if(typeof tradeUiState==='undefined')return[];
    const team=kind==='focal'?tradeUiState.browser?.focal_team:(tradeUiState.browser?.counterparties||[]).find(item=>item.team_id===tradeUiState.counterpartyTeamId);
    const refs=kind==='focal'?tradeUiState.focalSelected:tradeUiState.counterpartySelected;
    return[...(refs||[])].map(ref=>(team?.assets||[]).find(item=>item.asset_ref===ref)?.label||ref).filter(Boolean);
  }
  function packageText(kind){const labels=selectedLabels(kind);return labels.length?labels.join(' + '):'—'}
  function packageEvidence(result,teamId){
    const econ=side(result,'economics',teamId),net=adjusted(result,teamId);
    const sent=econ?.sent_market?.mean_value,received=econ?.received_market?.mean_value,delta=net?.roster_adjusted_market_delta;
    const pieces=[];
    if(finite(sent))pieces.push(`Send ${Math.round(sent).toLocaleString()} Value`);
    if(finite(received))pieces.push(`Receive ${Math.round(received).toLocaleString()} Value`);
    if(finite(delta))pieces.push(`${delta>=0?'+':''}${Math.round(delta).toLocaleString()} after roster effects`);
    return pieces.join(' · ')||'Market evidence incomplete';
  }
  function tone(value){return !finite(value)||Math.abs(value)<1e-9?'neutral':value>0?'good':'risk'}
  function impactCard(result,teamId,focal){
    const decision=side(result,'decision',teamId),net=adjusted(result,teamId),evaluation=side(result,'evaluation',teamId),res=evaluation?.delta?.resilience||{};
    const valueDelta=net?.roster_adjusted_market_delta;
    const lineupLoss=res?.largest_single_player_lineup_drop;
    const cuts=net?.required_cut_count;
    return`<article class="ns-trade-card ${focal?'ns-trade-card--you':'ns-trade-card--them'}"><div class="ns-trade-card__head"><span>${focal?'Your roster':'Their roster'}</span><strong>${esc(words(decision?.shape||'incomplete'))}</strong></div><div class="ns-trade-impact-line"><div><small>Roster-adjusted Value</small><strong class="ns-trade-delta" data-tone="${tone(valueDelta)}">${finite(valueDelta)?`${valueDelta>=0?'+':''}${Math.round(valueDelta).toLocaleString()}`:'—'}</strong></div><b>${esc(packageEvidence(result,teamId))}</b></div><div class="ns-trade-impact-line"><div><small>Largest lineup-loss exposure</small><strong>${finite(lineupLoss)?Math.abs(lineupLoss).toFixed(2):'—'}</strong></div><b>${finite(cuts)?`${cuts} required cut${cuts===1?'':'s'}`:'Roster effect returned'}</b></div></article>`;
  }
  function seasonCard(result,focalId){
    const row=simRow(result,focalId),c=row?.competitive||{};
    const ready=finite(c.expected_wins)||finite(c.playoff_probability)||finite(c.first_place_probability);
    return`<article class="ns-trade-card ns-trade-card--season"><div class="ns-trade-card__head"><span>Season impact</span><strong>${ready?`${Number(result?.scenario_simulation_count||0).toLocaleString()} runs`:'Simulation needed'}</strong></div><div class="ns-trade-season-grid"><div class="ns-trade-season-metric"><span>Expected wins</span><strong class="ns-trade-delta" data-tone="${tone(c.expected_wins)}">${signed(c.expected_wins,2)}</strong></div><div class="ns-trade-season-metric"><span>Playoff odds</span><strong class="ns-trade-delta" data-tone="${tone(c.playoff_probability)}">${pctPoints(c.playoff_probability)}</strong></div><div class="ns-trade-season-metric"><span>First-place odds</span><strong class="ns-trade-delta" data-tone="${tone(c.first_place_probability)}">${pctPoints(c.first_place_probability)}</strong></div></div></article>`;
  }
  function positionRows(result){return(result?.position_strength?.positions||[]).filter(row=>finite(row.expected_points_delta)&&Math.abs(row.expected_points_delta)>1e-9).sort((a,b)=>Math.abs(b.expected_points_delta)-Math.abs(a.expected_points_delta)).slice(0,4)}
  function positionCard(result){
    const rows=positionRows(result),max=Math.max(...rows.map(row=>Math.abs(row.expected_points_delta)),1);
    return`<article class="ns-trade-card ns-trade-card--position"><div class="ns-trade-card__head"><span>Lineup movement</span><strong>${rows.length?'By position':'No material move'}</strong></div><div class="ns-trade-position-list">${rows.length?rows.map(row=>`<div class="ns-trade-position-row"><span>${esc(row.position)}</span><div class="ns-trade-position-track"><i style="width:${Math.max(8,Math.min(100,Math.abs(row.expected_points_delta)/max*100)).toFixed(0)}%"></i></div><strong class="ns-trade-delta" data-tone="${tone(row.expected_points_delta)}">${signed(row.expected_points_delta,1)}</strong></div>`).join(''):'<p class="ns-trade-blocker-note">Projected starter output is essentially unchanged by position in the returned evidence.</p>'}</div></article>`;
  }
  function blocker(result,simulated){
    const focalId=result?.focal_team_id,net=adjusted(result,focalId),evidence=(lastSimulation||result)?.disposition?.evidence||{};
    const losses=(evidence.material_losses||[]).map(words),missing=(evidence.unavailable_metrics||[]).map(words),cuts=net?.required_cut_count||0;
    if(!simulated)return{title:'Season consequence still needs to be simulated',note:'The fast read can show package, roster and lineup effects, but the final action should wait for changed-roster season outcomes.'};
    if(losses.length)return{title:losses.slice(0,2).join(' · '),note:'These are material losses returned by the Decision disposition, not presentation-created warnings.'};
    if(cuts)return{title:`${cuts} required roster cut${cuts===1?'':'s'}`,note:'Roster adjustment is already included in the returned package economics where available.'};
    if(missing.length)return{title:`Missing: ${missing.slice(0,2).join(' · ')}`,note:'FSFFL fails closed where material evidence is unavailable rather than guessing.'};
    return{title:'No major blocker is identified',note:'That does not imply the other owner will accept. Owner history remains negotiation context, not an acceptance probability.'};
  }
  function bestCounter(result){
    const points=(result?.points||[]).filter(point=>!point.is_seed&&point.feasibility_shape==='mutual_gain_candidate').sort((a,b)=>(a.search_distance??Infinity)-(b.search_distance??Infinity)||a.depth-b.depth);
    return points[0]||null;
  }
  function frontierCopy(result){const point=bestCounter(result);if(!point)return'';const ours=(point.focal_assets||[]).map(item=>item.label).filter(Boolean).join(' + ')||'—',theirs=(point.counterparty_assets||[]).map(item=>item.label).filter(Boolean).join(' + ')||'—';return`<div class="ns-trade-counter"><span>Closest counter path found</span><strong>You send ${esc(ours)} → receive ${esc(theirs)}</strong></div>`}
  function actionState(simulated){
    const action=disposition(lastSimulation)||disposition(lastAnalysis);
    if(!simulated)return{title:'Simulate impact',copy:'Finish the changed-roster season comparison before treating this as a completed recommendation.',cta:'Simulate impact',target:'simulate'};
    const title=actionLabels[action]||words(action)||'Review completed evidence';
    if(action==='counter'||action==='counter_or_review')return{title,copy:'The Decision result points toward negotiation rather than accepting the current package as-is.',cta:'Explore counter path',target:'frontier'};
    if(action==='reject'||action==='decline')return{title,copy:'The current returned disposition is unfavorable for your franchise. Change the package before reconsidering it.',cta:'Adjust package',target:'builder'};
    if(action==='accept'||action==='support')return{title,copy:'The completed Decision result supports the deal for your franchise. Review the evidence below before acting outside FSFFL.',cta:'Review evidence',target:'methods'};
    return{title,copy:'The current Decision result does not support a simple accept/reject action.',cta:'Explore price frontier',target:'frontier'};
  }
  function methodsToggle(root){
    let button=root.querySelector('.ns-trade-methods-toggle');
    if(button)return button;
    button=document.createElement('button');button.type='button';button.className='ns-trade-methods-toggle';button.textContent='Methods & evidence';button.addEventListener('click',()=>{root.classList.toggle('ns-trade-show-methods');button.textContent=root.classList.contains('ns-trade-show-methods')?'Hide methods & evidence':'Methods & evidence'});root.appendChild(button);return button;
  }
  function markLegacy(root){[...root.children].forEach(node=>{if(node.id!=='ns-trade-decision-room'&&!node.classList.contains('ns-trade-methods-toggle'))node.classList.add('ns-trade-legacy')})}
  function primaryAction(target,root){
    if(target==='simulate')document.querySelector('#simulate-trade')?.click();
    else if(target==='frontier')document.querySelector('#explore-price')?.click();
    else if(target==='builder')document.querySelector('.trade-builder-grid')?.scrollIntoView({behavior:'smooth',block:'start'});
    else if(target==='methods'){root.classList.add('ns-trade-show-methods');const button=methodsToggle(root);button.textContent='Hide methods & evidence';button.scrollIntoView({behavior:'smooth',block:'center'})}
  }
  function renderRoom(){
    const result=lastAnalysis,root=document.querySelector('#trade-analysis-empty > div');if(!result||!root)return;
    const existing=root.querySelector('#ns-trade-decision-room');if(existing)existing.remove();
    markLegacy(root);
    const evidenceResult=lastSimulation||result;
    const focalId=result.focal_team_id,otherId=result.counterparty_team_id,simulated=Boolean(lastSimulation),action=actionState(simulated),block=blocker(evidenceResult,simulated);
    const finalAction=simulated&&Boolean(disposition(lastSimulation));
    const room=document.createElement('section');room.id='ns-trade-decision-room';room.className='ns-trade-room';
    room.innerHTML=`<div class="ns-trade-room__hero"><div class="ns-trade-room__top"><div><p class="eyebrow">Trade decision</p><h2>${esc(action.title)}</h2><p>${simulated?'Changed-roster evidence is complete for this run.':'Fast roster and package evidence is ready; season impact is the next decision layer.'}</p></div><span class="ns-trade-status" data-final="${finalAction?'true':'false'}">${finalAction?'Decision ready':'Simulation needed'}</span></div><div class="ns-trade-packages"><div class="ns-trade-package"><span>You give</span><strong>${esc(packageText('focal'))}</strong><small>${esc(packageEvidence(evidenceResult,focalId))}</small></div><div class="ns-trade-swap" aria-hidden="true">⇄</div><div class="ns-trade-package"><span>You get</span><strong>${esc(packageText('counterparty'))}</strong><small>${esc(packageEvidence(evidenceResult,otherId))}</small></div></div></div><div class="ns-trade-room__grid">${impactCard(evidenceResult,focalId,true)}${impactCard(evidenceResult,otherId,false)}${seasonCard(lastSimulation,focalId)}${positionCard(result)}<article class="ns-trade-card ns-trade-card--blocker"><span>Main blocker / risk</span><h3 class="ns-trade-blocker-copy">${esc(block.title)}</h3><p class="ns-trade-blocker-note">${esc(block.note)}</p>${frontierCopy(lastFrontier)}</article><article class="ns-trade-card ns-trade-card--action"><span>What to do next</span><h3 class="ns-trade-action-title">${esc(action.title)}</h3><p class="ns-trade-action-copy">${esc(action.copy)}</p><button type="button" class="primary-button ns-trade-primary">${esc(action.cta)}</button></article></div>`;
    root.prepend(room);methodsToggle(root);markLegacy(root);room.querySelector('.ns-trade-primary')?.addEventListener('click',()=>primaryAction(action.target,root));
  }
  function refineShell(){
    const screen=document.querySelector('#trade-center-screen');if(!screen)return;screen.classList.add('ns-trade-center');
    const hero=screen.querySelector('.trade-hero');if(hero){const h=hero.querySelector('h1'),lead=hero.querySelector('.lead');if(h)h.textContent='Does this deal make you better?';if(lead)lead.textContent='Build the package, compare both franchises, then finish the decision with changed-roster season impact.'}
    const analysisTitle=screen.querySelector('.trade-analysis-panel>.panel-header h2');if(analysisTitle)analysisTitle.textContent='Decision room';
  }
  function install(){
    if(installed||typeof window.renderTradeAnalysis!=='function'||typeof window.renderTradeSimulationResult!=='function')return false;installed=true;refineShell();
    const priorAnalysis=window.renderTradeAnalysis;window.renderTradeAnalysis=function(result){lastAnalysis=result;lastSimulation=null;lastFrontier=null;const output=priorAnalysis.apply(this,arguments);renderRoom();return output};renderTradeAnalysis=window.renderTradeAnalysis;
    const priorSimulation=window.renderTradeSimulationResult;window.renderTradeSimulationResult=function(result){lastSimulation=result;const output=priorSimulation.apply(this,arguments);renderRoom();return output};renderTradeSimulationResult=window.renderTradeSimulationResult;
    if(typeof window.renderTradeFrontierResult==='function'){const priorFrontier=window.renderTradeFrontierResult;window.renderTradeFrontierResult=function(result){lastFrontier=result;const output=priorFrontier.apply(this,arguments);renderRoom();return output};renderTradeFrontierResult=window.renderTradeFrontierResult}
    document.querySelectorAll('[data-route="trade_center"],[data-route-link="trade_center"]').forEach(node=>node.addEventListener('click',()=>setTimeout(refineShell,0)));
    return true;
  }
  window.installFsfflNorthStarTradeCenter=install;install();
})();
