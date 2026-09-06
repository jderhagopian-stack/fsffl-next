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

function renderTradeDraftSide(side){
  const container=qs(side==='focal'?'#focal-draft':'#counterparty-draft');
  const count=qs(side==='focal'?'#focal-count':'#counterparty-count');
  if(!container||!count)return;
  const team=tradeSideTeam(side),selected=selectedRefs(side);
  count.textContent=`${selected.size} selected`;
  container.innerHTML='';
  if(!team||!selected.size){
    container.innerHTML=`<p class="trade-empty">${side==='focal'?'Tap assets below to add them.':'Choose a team, then tap assets.'}</p>`;
    return;
  }
  [...selected].forEach(ref=>{
    const option=team.assets.find(item=>item.asset_ref===ref);
    if(!option)return;
    const chip=document.createElement('button');
    chip.type='button';chip.className='draft-chip';chip.title='Remove from draft';
    chip.innerHTML=`${escapeHtml(option.label)}${tradeAssetScore(option)?` · ${fmtFsfflValue(tradeAssetScore(option).score)}`:''}`;
    chip.addEventListener('click',()=>toggleTradeAsset(side,ref));
    container.appendChild(chip);
  });
}

function renderTradeAssetList(side){
  const container=qs(side==='focal'?'#focal-assets':'#counterparty-assets');
  const filter=qs(side==='focal'?'#focal-asset-filter':'#counterparty-asset-filter')?.value?.trim().toLowerCase()||'';
  if(!container)return;
  const team=tradeSideTeam(side),selected=selectedRefs(side);
  container.innerHTML='';
  if(!team){container.innerHTML=`<p class="trade-empty">${side==='focal'?'Select a managed team first.':'No counterparty selected.'}</p>`;return}
  const assets=(team.assets||[]).filter(option=>`${option.label} ${option.detail||''} ${option.asset_kind}`.toLowerCase().includes(filter));
  if(!assets.length){container.innerHTML='<p class="trade-empty">No matching assets.</p>';return}
  assets.forEach(option=>{
    const button=document.createElement('button');button.type='button';button.className=`asset-option${selected.has(option.asset_ref)?' selected':''}`;
    button.innerHTML=`<span><strong>${escapeHtml(option.label)}</strong><small>${escapeHtml(option.detail||option.asset_kind)}</small></span>${tradeValueMarkup(option)}`;
    button.addEventListener('click',()=>toggleTradeAsset(side,option.asset_ref));
    container.appendChild(button);
  });
}

function updateAnalyzeTradeState(){
  const button=qs('#analyze-trade');if(!button)return;
  button.disabled=!(tradeUiState.counterpartyTeamId&&tradeUiState.focalSelected.size&&tradeUiState.counterpartySelected.size);
}

function toggleTradeAsset(side,assetRef){
  const selected=selectedRefs(side);selected.has(assetRef)?selected.delete(assetRef):selected.add(assetRef);
  renderTradeDraftSide(side);renderTradeAssetList(side);updateAnalyzeTradeState();renderTradeAnalysisNotice();
}

function renderTradeCounterparties(){
  const select=qs('#counterparty-select');if(!select||!tradeUiState.browser)return;
  select.innerHTML='<option value="">Choose a team</option>';
  tradeUiState.browser.counterparties.forEach(team=>{const option=document.createElement('option');option.value=team.team_id;option.textContent=team.display_name;if(team.team_id===tradeUiState.counterpartyTeamId)option.selected=true;select.appendChild(option)});
  qs('#focal-trade-team').textContent=tradeUiState.browser.focal_team.display_name;
  qs('#counterparty-trade-team').textContent=currentCounterparty()?.display_name||'Counterparty';
}

function renderTradeAnalysisNotice(message){
  const panel=qs('#trade-analysis-empty');if(!panel)return;
  if(message){panel.textContent=message;return}
  const ready=tradeUiState.counterpartyTeamId&&tradeUiState.focalSelected.size&&tradeUiState.counterpartySelected.size;
  panel.textContent=ready?'Draft ready. Analyze Trade submits these canonically owned assets to the authoritative Trade Decision endpoint. Provisional FSFFL Values shown above are display-only and do not determine the result.':'Select at least one asset from each side. Provisional FSFFL Values are shown only for private-beta presentation testing; they are not a trade grade, recommendation, acceptance probability, or package economics.';
}

function clearTradeDraft(){
  tradeUiState.focalSelected.clear();tradeUiState.counterpartySelected.clear();
  renderTradeDraftSide('focal');renderTradeDraftSide('counterparty');renderTradeAssetList('focal');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice();
}

function chooseTradeCounterparty(teamId){
  tradeUiState.counterpartyTeamId=teamId;tradeUiState.counterpartySelected.clear();
  renderTradeCounterparties();renderTradeDraftSide('counterparty');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice();
}

async function analyzeTradeDraft(){
  const button=qs('#analyze-trade');if(button){button.disabled=true;button.textContent='Analyzing…'}
  renderTradeAnalysisNotice('Submitting the draft to authoritative Trade Decision…');
  try{
    const result=await api('/api/trade-center/analyze',{method:'POST',body:JSON.stringify({counterparty_team_id:tradeUiState.counterpartyTeamId,focal_asset_refs:[...tradeUiState.focalSelected],counterparty_asset_refs:[...tradeUiState.counterpartySelected]})});
    const panel=qs('#trade-analysis-empty');if(panel){panel.innerHTML=`<pre style="white-space:pre-wrap;text-align:left;width:100%;margin:0">${escapeHtml(JSON.stringify(result,null,2))}</pre>`}
  }catch(error){renderTradeAnalysisNotice(`Trade Decision is not available for this draft yet: ${error.message}. Your visual draft is preserved.`)}
  finally{if(button){button.textContent='Analyze Trade';updateAnalyzeTradeState()}}
}

async function loadTradeCenter(){
  if(!state.context?.team_id||tradeUiState.loading)return;
  tradeUiState.loading=true;
  const focalAssets=qs('#focal-assets');if(focalAssets)focalAssets.innerHTML='<p class="trade-empty">Loading canonical assets…</p>';
  try{
    const browserPromise=api('/api/trade-center/browser');
    const valuesPromise=state.valueCatalog?Promise.resolve(state.valueCatalog):(state.context?.value_ready?api('/api/values').catch(()=>null):Promise.resolve(null));
    const[browser,values]=await Promise.all([browserPromise,valuesPromise]);
    tradeUiState.browser=browser;if(values)state.valueCatalog=values;
    if(tradeUiState.counterpartyTeamId&&!browser.counterparties.some(team=>team.team_id===tradeUiState.counterpartyTeamId))tradeUiState.counterpartyTeamId='';
    tradeUiState.focalSelected=new Set([...tradeUiState.focalSelected].filter(ref=>browser.focal_team.assets.some(item=>item.asset_ref===ref)));
    const counterparty=currentCounterparty();tradeUiState.counterpartySelected=new Set([...tradeUiState.counterpartySelected].filter(ref=>counterparty?.assets.some(item=>item.asset_ref===ref)));
    renderTradeCounterparties();renderTradeDraftSide('focal');renderTradeDraftSide('counterparty');renderTradeAssetList('focal');renderTradeAssetList('counterparty');updateAnalyzeTradeState();renderTradeAnalysisNotice();
    const label=qs('#trade-state-label span:last-child');if(label)label.textContent=`Canonical ownership · ${String(browser.state_id).slice(0,12)}…`;
  }catch(error){if(focalAssets)focalAssets.innerHTML=`<p class="trade-empty">Unable to load Trade Center: ${escapeHtml(error.message)}</p>`}
  finally{tradeUiState.loading=false}
}

function wireTradeCenter(){
  qs('#counterparty-select')?.addEventListener('change',event=>chooseTradeCounterparty(event.target.value));
  qs('#focal-asset-filter')?.addEventListener('input',()=>renderTradeAssetList('focal'));
  qs('#counterparty-asset-filter')?.addEventListener('input',()=>renderTradeAssetList('counterparty'));
  qs('#clear-trade')?.addEventListener('click',clearTradeDraft);
  qs('#analyze-trade')?.addEventListener('click',analyzeTradeDraft);
  qsa('[data-route="trade_center"],[data-route-link="trade_center"]').forEach(button=>button.addEventListener('click',()=>setTimeout(loadTradeCenter,0)));
}

wireTradeCenter();
