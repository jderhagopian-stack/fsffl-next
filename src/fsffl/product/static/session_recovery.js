const fsfflSessionKeys={league:'fsffl:last-sleeper-league',team:'fsffl:last-team'};
const fsfflOriginalApi=api;
let fsfflRestoringSession=false;

function fsfflRememberSessionRequest(path,options,result){
  try{
    if(path==='/api/connect/sleeper'&&options?.body){
      const payload=JSON.parse(options.body);if(payload?.league_external_id)localStorage.setItem(fsfflSessionKeys.league,payload.league_external_id);
      if(result?.team_id)localStorage.setItem(fsfflSessionKeys.team,result.team_id);
    }
    if(path==='/api/select-team'&&options?.body){
      const payload=JSON.parse(options.body);if(payload?.team_id)localStorage.setItem(fsfflSessionKeys.team,payload.team_id);
    }
  }catch(_){ }
}

async function fsfflRestoreSession(){
  if(fsfflRestoringSession)return false;
  const leagueId=localStorage.getItem(fsfflSessionKeys.league);if(!leagueId)return false;
  fsfflRestoringSession=true;
  try{
    let context=await fsfflOriginalApi('/api/connect/sleeper',{method:'POST',body:JSON.stringify({league_external_id:leagueId})});
    const teamId=localStorage.getItem(fsfflSessionKeys.team);
    if(teamId&&(context.teams||[]).some(team=>team.team_id===teamId)){
      context=await fsfflOriginalApi('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})});
    }
    state.context=context;state.teamView=null;state.valueCatalog=null;state.intelligence=null;applyContext();
    if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
    return true;
  }catch(error){
    console.error('Unable to restore previous FSFFL session',error);return false;
  }finally{fsfflRestoringSession=false}
}

api=async function(path,options={}){
  try{
    const result=await fsfflOriginalApi(path,options);fsfflRememberSessionRequest(path,options,result);return result;
  }catch(error){
    const recoverable=error?.message==='No league is loaded'||error?.message==='No managed team is selected';
    const isRestoreCall=path==='/api/connect/sleeper'||path==='/api/select-team';
    if(recoverable&&!isRestoreCall&&await fsfflRestoreSession())return fsfflOriginalApi(path,options);
    throw error;
  }
};

function fsfflFocalEconomicNet(result){
  const net=result?.economic_net;if(!net)return null;
  return [net.side_a,net.side_b].find(side=>side?.team_id===result.focal_team_id)||null;
}

function fsfflTradeNetMarkup(result){
  const side=fsfflFocalEconomicNet(result),market=side?.market;
  if(!market||market.status!=='complete'||typeof market.mean_delta!=='number')return '<strong>—</strong><small>Complete comparable market evidence is not available.</small>';
  const sign=market.mean_delta>0?'+':'';
  return `<strong>${sign}${fmtFsfflValue(market.mean_delta)}</strong><small>Received ${fmtFsfflValue(market.received_mean)} · sent ${fmtFsfflValue(market.sent_mean)}</small>`;
}

function fsfflTradeDecisionHeading(result){
  if(result?.disposition?.disposition){
    const raw=result.disposition.disposition;
    const labels={support:'Support',decline:'Decline',counter_or_review:'Counter / review',no_clear_advantage:'No clear advantage',insufficient_evidence:'More evidence needed'};
    return labels[raw]||raw.replaceAll('_',' ');
  }
  return 'Complete the decision';
}

function fsfflTradeDecisionCopy(result){
  if(result?.disposition?.disposition)return 'This is the governed NEXT-5 disposition for the managed team.';
  const gaps=[];
  if(!result?.availability?.competitive_outcomes)gaps.push('competitive simulation');
  if(!result?.availability?.mandatory_cut_cost)gaps.push('mandatory cut cost');
  if(!result?.availability?.package_concentration_premium)gaps.push('elite-asset/package premium');
  return `The fast analysis is useful, but FSFFL will not invent an accept/reject call before ${gaps.join(', ')} ${gaps.length===1?'is':'are'} attached.`;
}

function fsfflTradePlayerDelta(){
  if(typeof tradeUiState==='undefined')return null;
  const focal=tradeSideTeam('focal'),counter=tradeSideTeam('counterparty');
  if(!focal||!counter)return null;
  const countPlayers=(team,selected)=>[...selected].map(ref=>team.assets.find(item=>item.asset_ref===ref)).filter(item=>item?.asset_kind==='player').length;
  const sent=countPlayers(focal,tradeUiState.focalSelected),received=countPlayers(counter,tradeUiState.counterpartySelected);
  return received-sent;
}

function fsfflUpgradeTradePresentation(result){
  const panel=qs('#trade-analysis-empty');if(!panel)return;
  const existing=panel.firstElementChild;if(!existing)return;
  const playerDelta=fsfflTradePlayerDelta();
  const rosterCopy=playerDelta===null?'Roster-space effect unavailable.':playerDelta>0?`Net +${playerDelta} rostered player${playerDelta===1?'':'s'}. Mandatory cut selection/cost is not yet applied.`:playerDelta<0?`Net ${playerDelta} rostered players; the deal creates roster space.`:'No net change in rostered-player count from the selected player assets.';
  const summary=document.createElement('div');
  summary.className='fsffl-trade-decision-summary';
  summary.style.cssText='border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px;background:#0a1120;text-align:left';
  summary.innerHTML=`<p class="eyebrow">Decision summary</p><h2 style="margin:0 0 6px">${escapeHtml(fsfflTradeDecisionHeading(result))}</h2><p style="color:var(--muted);margin:0 0 14px;line-height:1.5">${escapeHtml(fsfflTradeDecisionCopy(result))}</p><div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px"><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Market value change</span>${fsfflTradeNetMarkup(result)}</div><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Roster-space effect</span><strong>${playerDelta===null?'—':playerDelta>0?`+${playerDelta}`:String(playerDelta)}</strong><small>${escapeHtml(rosterCopy)}</small></div><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Competitive impact</span><strong>Run simulation</strong><small>Expected wins, playoff odds and true championship odds belong to Simulation authority.</small></div><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Package premium</span><strong>Pending governed attachment</strong><small>FSFFL will not treat several lesser assets as automatically equivalent to one elite asset.</small></div></div>`;
  const details=document.createElement('details');
  details.style.cssText='margin-top:12px;border-top:1px solid var(--line);padding-top:12px';
  const detailsSummary=document.createElement('summary');
  detailsSummary.style.cssText='cursor:pointer;color:var(--accent);font-weight:700';
  detailsSummary.textContent='Show advanced details';
  details.appendChild(detailsSummary);
  const advanced=document.createElement('div');advanced.style.marginTop='12px';
  while(existing.firstChild)advanced.appendChild(existing.firstChild);
  details.appendChild(advanced);existing.appendChild(summary);existing.appendChild(details);
}

function fsfflInstallDecisionFirstTradeAnalysis(){
  const button=qs('#analyze-trade');if(!button||button.dataset.fsfflDecisionFirst==='1')return;
  button.dataset.fsfflDecisionFirst='1';
  button.addEventListener('click',async event=>{
    event.stopImmediatePropagation();
    if(button.disabled)return;
    button.disabled=true;button.textContent='Analyzing…';
    if(typeof invalidateTradeScenario==='function')invalidateTradeScenario();
    if(typeof renderTradeAnalysisNotice==='function')renderTradeAnalysisNotice('Building governed bilateral consequences…');
    try{
      const result=await api('/api/trade-center/analyze',{method:'POST',body:JSON.stringify(tradeDraftPayload())});
      renderTradeAnalysis(result);fsfflUpgradeTradePresentation(result);
      ['#simulate-trade','#explore-price'].forEach(selector=>{const action=qs(selector);if(action)action.disabled=false});
    }catch(error){
      if(typeof renderTradeAnalysisNotice==='function')renderTradeAnalysisNotice(`Trade analysis is unavailable for this draft: ${error.message}. Your visual draft is preserved.`);
    }finally{
      button.textContent='Analyze Trade';if(typeof updateAnalyzeTradeState==='function')updateAnalyzeTradeState();
    }
  },true);
}

document.addEventListener('DOMContentLoaded',fsfflInstallDecisionFirstTradeAnalysis,{once:true});

setTimeout(async()=>{
  if(!state.context?.league_id){
    const restored=await fsfflRestoreSession();
    if(restored)console.info('Restored previous FSFFL league session after hosted restart.');
  }
},0);
