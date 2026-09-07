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
function fsfflFocalRosterAdjustedNet(result){
  const net=result?.roster_adjusted_market_net;if(!net)return null;
  return [net.side_a,net.side_b].find(side=>side?.team_id===result.focal_team_id)||null;
}
function fsfflFocalRosterResolution(result){
  return (result?.roster_legality||[]).find(item=>item?.team_id===result.focal_team_id)||null;
}

function fsfflTradeNetMarkup(result){
  const adjusted=fsfflFocalRosterAdjustedNet(result);
  if(adjusted?.status==='complete'&&typeof adjusted.roster_adjusted_market_delta==='number'){
    const value=adjusted.roster_adjusted_market_delta,sign=value>0?'+':'';
    const raw=typeof adjusted.raw_trade_market_delta==='number'?fmtFsfflValue(adjusted.raw_trade_market_delta):'—';
    const cut=typeof adjusted.mandatory_cut_market_cost==='number'?fmtFsfflValue(adjusted.mandatory_cut_market_cost):'—';
    return `<strong>${sign}${fmtFsfflValue(value)}</strong><small>Raw trade ${raw} · mandatory cut cost ${cut}</small>`;
  }
  const side=fsfflFocalEconomicNet(result),market=side?.market;
  if(!market||market.status!=='complete'||typeof market.mean_delta!=='number')return '<strong>—</strong><small>Complete comparable market evidence is not available.</small>';
  const sign=market.mean_delta>0?'+':'';
  return `<strong>${sign}${fmtFsfflValue(market.mean_delta)}</strong><small>Raw received-minus-sent Value; cut cost is incomplete.</small>`;
}

function fsfflRosterImpactMarkup(result){
  const resolution=fsfflFocalRosterResolution(result);
  if(!resolution)return '<strong>—</strong><small>Roster legality evidence unavailable.</small>';
  const count=Number(resolution.required_cut_count||0);
  if(!count)return '<strong>No cuts</strong><small>The post-trade active roster remains within the league limit.</small>';
  const names=(resolution.cuts||[]).map(cut=>{
    const option=[...(tradeUiState.browser?.focal_team?.assets||[]),...(currentCounterparty()?.assets||[])].find(item=>item.player_id===cut.player_id);
    return option?.label||cut.player_id;
  });
  const cost=typeof resolution.cut_market_value_total==='number'?` · ${fmtFsfflValue(resolution.cut_market_value_total)} Value removed`:' · cut Value incomplete';
  return `<strong>${count} mandatory cut${count===1?'':'s'}</strong><small>${escapeHtml(names.join(', ')||'Resolved by NEXT-5')}${escapeHtml(cost)}</small>`;
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
  if(!result?.availability?.mandatory_cut_cost)gaps.push('complete cut cost');
  if(!result?.availability?.package_concentration_premium)gaps.push('consolidation evidence');
  if(!gaps.length)return 'The governed decision inputs are attached; final disposition is being resolved by NEXT-5.';
  return `FSFFL will not invent an accept/reject call before ${gaps.join(', ')} ${gaps.length===1?'is':'are'} attached.`;
}

function fsfflUpgradeTradePresentation(result){
  const panel=qs('#trade-analysis-empty');if(!panel)return;
  const existing=panel.firstElementChild;if(!existing)return;
  const summary=document.createElement('div');
  summary.className='fsffl-trade-decision-summary';
  summary.style.cssText='border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px;background:#0a1120;text-align:left';
  summary.innerHTML=`<p class="eyebrow">Decision summary</p><h2 style="margin:0 0 6px">${escapeHtml(fsfflTradeDecisionHeading(result))}</h2><p style="color:var(--muted);margin:0 0 14px;line-height:1.5">${escapeHtml(fsfflTradeDecisionCopy(result))}</p><div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px"><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Overall market Value</span>${fsfflTradeNetMarkup(result)}</div><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Roster consequences</span>${fsfflRosterImpactMarkup(result)}</div><div id="fsffl-competitive-summary" style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Competitive impact</span><strong>Run simulation</strong><small>Expected wins, playoff odds and championship odds belong to Simulation authority.</small></div><div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Consolidation effect</span><strong>${result?.availability?.package_concentration_premium?'Attached':'Deriving from roster utility'}</strong><small>No arbitrary multiplier: FSFFL evaluates the actual legal roster, lineup, cut cost and competitive effect of the package.</small></div></div>`;
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
