const tradeUiState={browser:null,counterpartyTeamId:'',focalSelected:new Set(),counterpartySelected:new Set(),loading:false};

function tradeAssetScore(option){
  const assetId=option?.player_id||option?.pick_id;
  return assetId?provisionalScoreFor(assetId):null;
}

function tradeValueMarkup(option){
  const item=tradeAssetScore(option);
  if(!item||typeof item.score!=='number')return'<span class="asset-kind">Value —</span>';
  const detail=`${provisionalValueExplanation}\nStatus: ${item.status}\nModel: ${item.model_version}\nReference source: ${item.reference_source_id}\nReference scale: ${item.reference_scale_id}`;
  return`<span class="asset-kind" title="${escapeHtml(detail)}">FSFFL ${fmtFsfflValue(item.score)} · PROVISIONAL</span>`;
}

function selectedRefs(side){return side==='focal'?tradeUiState.focalSelected:tradeUiState.counterpartySelected}
function currentCounterparty(){return(tradeUiState.browser?.counterparties||[]).find(team=>team.team_id===tradeUiState.counterpartyTeamId)||null}
function tradeSideTeam(side){return side==='focal'?tradeUiState.browser?.focal_team:currentCounterparty()}
function tradeFilterId(side,kind){return`${side}-${kind}-filter`}

function filterOptions(side,kind){
  const team=tradeSideTeam(side);if(!team)return[];
  if(kind==='position')return[...new Set((team.assets||[]).filter(item=>item.asset_kind==='player'&&item.detail).map(item=>item.detail))].sort();
  if(kind==='slot')return[...new Set((team.assets||[]).filter(item=>item.asset_kind==='player'&&item.roster_slot).map(item=>item.roster_slot))].sort();
  return[];
}

function ensureTradeFilters(side){
  const search=qs(side==='focal'?'#focal-asset-filter':'#counterparty-asset-filter');if(!search)return;
  search.placeholder='Search player by name';search.setAttribute('aria-label',`${side==='focal'?'Your':'Their'} player name search`);
  let row=search.closest('.asset-search')?.querySelector('.trade-filter-row');
  if(!row){
    row=document.createElement('div');row.className='trade-filter-row';row.style.cssText='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;margin-top:8px';
    row.innerHTML=`<select id="${tradeFilterId(side,'type')}" aria-label="Asset type"><option value="">All assets</option><option value="player">Players</option><option value="pick">Picks</option></select><select id="${tradeFilterId(side,'position')}" aria-label="Player position"><option value="">All positions</option></select><select id="${tradeFilterId(side,'slot')}" aria-label="Roster slot"><option value="">All roster slots</option></select>`;
    search.closest('.asset-search').appendChild(row);
    row.querySelectorAll('select').forEach(select=>select.addEventListener('change',()=>renderTradeAssetList(side)));
  }
  const position=qs(`#${tradeFilterId(side,'position')}`),slot=qs(`#${tradeFilterId(side,'slot')}`);
  const currentPosition=position?.value||'',currentSlot=slot?.value||'';
  if(position){position.innerHTML='<option value="">All positions</option>'+filterOptions(side,'position').map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');if(filterOptions(side,'position').includes(currentPosition))position.value=currentPosition}
  if(slot){slot.innerHTML='<option value="">All roster slots</option>'+filterOptions(side,'slot').map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');if(filterOptions(side,'slot').includes(currentSlot))slot.value=currentSlot}
}

function renderTradeDraftSide(side){
  const container=qs(side==='focal'?'#focal-draft':'#counterparty-draft');
  const count=qs(side==='focal'?'#focal-count':'#counterparty-count');
  if(!container||!count)return;
  const team=tradeSideTeam(side),selected=selectedRefs(side);
  count.textContent=`${selected.size} selected`;
  container.innerHTML='';
  if(!team||!selected.size){container.innerHTML=`<p class="trade-empty">${side==='focal'?'Tap assets below to add them.':'Choose a team, then tap assets.'}</p>`;return}
  [...selected].forEach(ref=>{const option=team.assets.find(item=>item.asset_ref===ref);if(!option)return;const chip=document.createElement('button');chip.type='button';chip.className='draft-chip';chip.title='Remove from draft';chip.innerHTML=`${escapeHtml(option.label)}${tradeAssetScore(option)?` · ${fmtFsfflValue(tradeAssetScore(option).score)}`:''}`;chip.addEventListener('click',()=>toggleTradeAsset(side,ref));container.appendChild(chip)})
}

function renderTradeAssetList(side){
  const container=qs(side==='focal'?'#focal-assets':'#counterparty-assets');
  const query=qs(side==='focal'?'#focal-asset-filter':'#counterparty-asset-filter')?.value?.trim().toLowerCase()||'';
  if(!container)return;
  const team=tradeSideTeam(side),selected=selectedRefs(side);container.innerHTML='';
  if(!team){container.innerHTML=`<p class="trade-empty">${side==='focal'?'Select a managed team first.':'No counterparty selected.'}</p>`;return}
  ensureTradeFilters(side);
  const type=qs(`#${tradeFilterId(side,'type')}`)?.value||'',position=qs(`#${tradeFilterId(side,'position')}`)?.value||'',slot=qs(`#${tradeFilterId(side,'slot')}`)?.value||'';
  const assets=(team.assets||[]).filter(option=>{
    if(query&&(option.asset_kind!=='player'||!option.label.toLowerCase().includes(query)))return false;
    if(type&&option.asset_kind!==type)return false;
    if(position&&(option.asset_kind!=='player'||option.detail!==position))return false;
    if(slot&&(option.asset_kind!=='player'||option.roster_slot!==slot))return false;
    return true;
  });
  if(!assets.length){container.innerHTML='<p class="trade-empty">No matching assets.</p>';return}
  assets.forEach(option=>{const button=document.createElement('button');button.type='button';button.className=`asset-option${selected.has(option.asset_ref)?' selected':''}`;button.innerHTML=`<span><strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.detail||option.asset_kind)}</small></span>${tradeValueMarkup(option)}`;button.addEventListener('click',()=>toggleTradeAsset(side,option.asset_ref));container.appendChild(button)})
}

function updateAnalyzeTradeState(){const button=qs('#analyze-trade');if(!button)return;button.disabled=!(tradeUiState.counterpartyTeamId&&tradeUiState.focalSelected.size&&tradeUiState.counterpartySelected.size)}
function toggleTradeAsset(side,assetRef){const selected=selectedRefs(side);selected.has(assetRef)?selected.delete(assetRef):selected.add(assetRef);renderTradeDraftSide(side);renderTradeAssetList(side);updateAnalyzeTradeState();renderTradeAnalysisNotice()}

function renderTradeCounterparties(){
  const select=qs('#counterparty-select');if(!select||!tradeUiState.browser)return;select.innerHTML='<option value="">Choose a team</option>';
  tradeUiState.browser.counterparties.forEach(team=>{const option=document.createElement('option');option.value=team.team_id;option.textContent=team.display_name;if(team.team_id===tradeUiState.counterpartyTeamId)option.selected=true;select.appendChild(option)});
  qs('#focal-trade-team').textContent=tradeUiState.browser.focal_team.display_name;qs('#counterparty-trade-team').textContent=currentCounterparty()?.display_name||'Counterparty';
}

function renderTradeAnalysisNotice(message){
  const panel=qs('#trade-analysis-empty');if(!panel)return;if(message){panel.textContent=message;return}
  const ready=tradeUiState.counterpartyTeamId&&tradeUiState.focalSelected.size&&tradeUiState.counterpartySelected.size;
  panel.textContent=ready?'Draft ready. Analyze Trade submits these canonically owned assets to the authoritative Trade Decision endpoint. Provisional FSFFL Values shown above are display-only and do not determine the result.':'Select at least one asset from each side. Provisional FSFFL Values are shown only for private-beta presentation testing; they are not a trade grade, recommendation, acceptance probability, or package economics.';
}

function tradeTeamName(teamId){
  if(tradeUiState.browser?.focal_team?.team_id===teamId)return tradeUiState.browser.focal_team.display_name;
  return(tradeUiState.browser?.counterparties||[]).find(team=>team.team_id===teamId)?.display_name||teamId;
}
function signedTradeNumber(value,digits=2){if(typeof value!=='number')return'—';const n=value.toFixed(digits);return value>0?`+${n}`:n}
function tradeDirectionText(value){return value?value.replaceAll('_',' '):'unavailable'}
function analysisSide(result,teamId){
  const evaluation=[result.evaluation?.side_a,result.evaluation?.side_b].find(side=>side?.team_id===teamId)||null;
  const decision=[result.decision?.side_a,result.decision?.side_b].find(side=>side?.team_id===teamId)||null;
  const economics=[result.economics?.side_a,result.economics?.side_b].find(side=>side?.team_id===teamId)||null;
  return{evaluation,decision,economics};
}
function marketPackageMarkup(summary,label){
  if(!summary)return`<div><span class="metric-label">${escapeHtml(label)}</span><strong style="display:block;margin-top:4px">—</strong><small style="color:var(--muted)">Evidence unavailable</small></div>`;
  const scale=summary.scale?.scale_id||'governed market scale';
  return`<div><span class="metric-label">${escapeHtml(label)}</span><strong style="display:block;margin-top:4px">${fmtNumber(summary.mean_value,2)}</strong><small style="color:var(--muted)">${escapeHtml(scale)} · ${summary.included_asset_ids?.length||0} evidenced asset(s)</small></div>`;
}
function rosterMetricMarkup(label,value,direction,digits=2){
  return`<div><span class="metric-label">${escapeHtml(label)}</span><strong style="display:block;margin-top:4px">${signedTradeNumber(value,digits)}</strong><small style="color:var(--muted);text-transform:capitalize">${escapeHtml(tradeDirectionText(direction))}</small></div>`;
}
function sideAnalysisMarkup(result,teamId){
  const side=analysisSide(result,teamId),delta=side.evaluation?.delta,resilience=delta?.resilience;
  const rosterReady=Boolean(resilience);
  return`<article style="border:1px solid var(--line);border-radius:12px;padding:14px;background:#0a1120">
    <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:12px"><div><p class="eyebrow" style="margin-bottom:5px">Franchise impact</p><h3 style="margin:0">${escapeHtml(tradeTeamName(teamId))}</h3></div><span class="trade-count" style="text-transform:capitalize">${escapeHtml(tradeDirectionText(side.decision?.shape||'incomplete'))}</span></div>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:14px">
      ${rosterMetricMarkup('Largest lineup-loss exposure',resilience?.largest_single_player_lineup_drop,side.decision?.largest_single_player_lineup_drop)}
      ${rosterMetricMarkup('Forecasted bench depth',resilience?.bench_forecasted_count,side.decision?.bench_forecasted_count,0)}
      ${rosterMetricMarkup('Unavailable players',resilience?.unavailable_count,side.decision?.unavailable_count,0)}
      ${rosterMetricMarkup('Missing forecasts',resilience?.missing_forecast_count,side.decision?.missing_forecast_count,0)}
    </div>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding-top:12px;border-top:1px solid var(--line)">
      ${marketPackageMarkup(side.economics?.sent_market,'Market evidence sent')}
      ${marketPackageMarkup(side.economics?.received_market,'Market evidence received')}
    </div>
    ${rosterReady?'':'<p style="color:var(--muted);font-size:12px;margin:12px 0 0">Roster consequence evidence is not available for this side.</p>'}
  </article>`;
}
function renderTradeAnalysis(result){
  const panel=qs('#trade-analysis-empty');if(!panel)return;
  const focalId=result.focal_team_id,counterpartyId=result.counterparty_team_id;
  const competitiveReady=Boolean(result.availability?.competitive_outcomes);
  const decisionShape=result.decision?.shape?tradeDirectionText(result.decision.shape):'incomplete';
  const warnings=(result.warnings||[]).map(item=>`<li>${escapeHtml(item)}</li>`).join('');
  panel.innerHTML=`<div style="width:100%;text-align:left">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:14px"><div><p class="eyebrow">Current analysis</p><h3 style="margin:0">Bilateral consequence view</h3><p style="color:var(--muted);font-size:12px;margin:7px 0 0">Decision shape: <strong style="color:var(--text);text-transform:capitalize">${escapeHtml(decisionShape)}</strong>. This is descriptive evidence, not a trade grade or recommendation.</p></div><span class="status-chip">${result.availability?.roster_consequences?'Roster impact ready':'Partial evidence'}</span></div>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px">${sideAnalysisMarkup(result,focalId)}${sideAnalysisMarkup(result,counterpartyId)}</div>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px">
      <div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Competitive impact</span><strong style="display:block;margin:5px 0">${competitiveReady?'Ready':'Not simulated yet'}</strong><small style="color:var(--muted)">Win, playoff and first-place deltas require the changed roster to run through NEXT-4 Simulation authority.</small></div>
      <div style="border:1px solid var(--line);border-radius:10px;padding:12px"><span class="metric-label">Acceptance probability</span><strong style="display:block;margin:5px 0">Not estimated</strong><small style="color:var(--muted)">The presentation layer does not consume or estimate acceptance authority. Behavioral evidence will be attached through a governed Decision/API contract when ready.</small></div>
    </div>
    ${warnings?`<details style="margin-top:12px"><summary style="cursor:pointer;color:var(--accent)">Evidence & limitations</summary><ul style="color:var(--muted);font-size:12px;line-height:1.5;padding-left:18px">${warnings}</ul></details>`:''}
    <p style="color:var(--muted);font-size:11px;margin:12px 0 0">Provisional FSFFL Value shown in the builder is not used in this analysis.</p>
  </div>`;
}

function clearTradeDraft(){tradeUiState.focalSelected.clear();tradeUiState.counterpartySelected.clear();renderTradeDraftSide('focal');renderTradeDraftSide('counterparty');renderTradeAssetList('focal');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice()}
function chooseTradeCounterparty(teamId){tradeUiState.counterpartyTeamId=teamId;tradeUiState.counterpartySelected.clear();const search=qs('#counterparty-asset-filter');if(search)search.value='';['type','position','slot'].forEach(kind=>{const control=qs(`#${tradeFilterId('counterparty',kind)}`);if(control)control.value=''});renderTradeCounterparties();renderTradeDraftSide('counterparty');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice()}

async function analyzeTradeDraft(){
  const button=qs('#analyze-trade');if(button){button.disabled=true;button.textContent='Analyzing…'}renderTradeAnalysisNotice('Building governed bilateral consequences…');
  try{const result=await api('/api/trade-center/analyze',{method:'POST',body:JSON.stringify({counterparty_team_id:tradeUiState.counterpartyTeamId,focal_asset_refs:[...tradeUiState.focalSelected],counterparty_asset_refs:[...tradeUiState.counterpartySelected]})});renderTradeAnalysis(result)}
  catch(error){renderTradeAnalysisNotice(`Trade analysis is unavailable for this draft: ${error.message}. Your visual draft is preserved.`)}finally{if(button){button.textContent='Analyze Trade';updateAnalyzeTradeState()}}
}

async function loadTradeCenter(){
  if(!state.context?.team_id||tradeUiState.loading)return;tradeUiState.loading=true;const focalAssets=qs('#focal-assets');if(focalAssets)focalAssets.innerHTML='<p class="trade-empty">Loading canonical assets…</p>';
  try{const browserPromise=api('/api/trade-center/browser');const valuesPromise=state.valueCatalog?Promise.resolve(state.valueCatalog):(state.context?.value_ready?api('/api/values').catch(()=>null):Promise.resolve(null));const[browser,values]=await Promise.all([browserPromise,valuesPromise]);tradeUiState.browser=browser;if(values)state.valueCatalog=values;if(tradeUiState.counterpartyTeamId&&!browser.counterparties.some(team=>team.team_id===tradeUiState.counterpartyTeamId))tradeUiState.counterpartyTeamId='';tradeUiState.focalSelected=new Set([...tradeUiState.focalSelected].filter(ref=>browser.focal_team.assets.some(item=>item.asset_ref===ref)));const counterparty=currentCounterparty();tradeUiState.counterpartySelected=new Set([...tradeUiState.counterpartySelected].filter(ref=>counterparty?.assets.some(item=>item.asset_ref===ref)));ensureTradeFilters('focal');ensureTradeFilters('counterparty');renderTradeCounterparties();renderTradeDraftSide('focal');renderTradeDraftSide('counterparty');renderTradeAssetList('focal');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice();const label=qs('#trade-state-label span:last-child');if(label)label.textContent=`Canonical ownership · ${String(browser.state_id).slice(0,12)}…`}
  catch(error){if(focalAssets)focalAssets.innerHTML=`<p class="trade-empty">Unable to load Trade Center: ${escapeHtml(error.message)}</p>`}finally{tradeUiState.loading=false}
}

function wireTradeCenter(){
  qs('#counterparty-select')?.addEventListener('change',event=>chooseTradeCounterparty(event.target.value));
  qs('#focal-asset-filter')?.addEventListener('input',()=>renderTradeAssetList('focal'));
  qs('#counterparty-asset-filter')?.addEventListener('input',()=>renderTradeAssetList('counterparty'));
  qs('#clear-trade')?.addEventListener('click',clearTradeDraft);qs('#analyze-trade')?.addEventListener('click',analyzeTradeDraft);
  qsa('[data-route="trade_center"],[data-route-link="trade_center"]').forEach(button=>button.addEventListener('click',()=>setTimeout(loadTradeCenter,0)));
}

wireTradeCenter();
