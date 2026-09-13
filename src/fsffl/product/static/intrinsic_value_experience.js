/* Phase 3 Franchise Value Lens.
 * Presentation only. Model truth comes from governed Value/Market/Team Utility APIs.
 * Broad Market, FSFFL Intrinsic, League Market, and Team Utility remain separate.
 */
(function(){
  'use strict';
  const VERSION='20260913-intrinsic-dynasty-scale1';
  const TAB='value_lens';
  const MARKET_SCALE='dynasty-market-percentile';
  const MARKET_CARDINAL_SCALE='fsffl-market-cardinal';
  let cached=null,cachedStateId=null,inFlight=null,requestGeneration=0;

  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const pct=value=>finite(value)?`${Math.round(value*100)}th pct`:'Unavailable';
  const valueNumber=value=>finite(value)?Math.round(value).toLocaleString():'Unavailable';
  const words=value=>String(value||'').replaceAll('_',' ');

  function currentView(){try{return typeof fsfflMyTeamState!=='undefined'?fsfflMyTeamState.view:null}catch(_){return null}}
  function currentPlayers(){return currentView()?.players||[]}
  function stateId(){return state?.context?.state_id||currentView()?.context?.league_state_id||null}
  function marketPercentile(player){const estimate=player?.value_profile?.market_price;if(estimate?.scale?.scale_id!==MARKET_SCALE)return null;const value=estimate?.distribution?.mean;return finite(value)?Math.max(0,Math.min(1,value)):null}
  function marketCardinalMap(){try{return new Map((fsfflMyTeamState?.values?.fsffl_cardinal_values||[]).filter(row=>row?.scale?.scale_id===MARKET_CARDINAL_SCALE).map(row=>[row.asset_id,row.score]))}catch(_){return new Map()}}
  function confidenceLabel(value){const label=words(value||'unavailable');return label.charAt(0).toUpperCase()+label.slice(1)}

  function comparison(intrinsicRank,marketRank,available){
    if(!available)return{kind:'unavailable',label:'Intrinsic unavailable',copy:'FSFFL does not have enough governed evidence to publish an Intrinsic value for this player.'};
    if(!finite(intrinsicRank)||!finite(marketRank))return{kind:'unavailable',label:'Comparison unavailable',copy:'One of the two comparable rank views is unavailable.'};
    const delta=intrinsicRank-marketRank;
    if(delta>=.18)return{kind:'intrinsic',label:'FSFFL materially higher',copy:'FSFFL’s football economics place this player materially higher in the value distribution than the broad dynasty market. Investigate the gap; it is not an automatic buy signal.'};
    if(delta>=.07)return{kind:'intrinsic',label:'FSFFL moderately higher',copy:'FSFFL’s football economics place this player moderately higher than the broad dynasty market. Investigate the gap before acting.'};
    if(delta<=-.18)return{kind:'market',label:'Broad market materially higher',copy:'The broad dynasty market places this player materially higher than FSFFL’s football economics do. Investigate the gap; it is not an automatic sell signal.'};
    if(delta<=-.07)return{kind:'market',label:'Broad market moderately higher',copy:'The broad dynasty market places this player moderately higher than FSFFL’s football economics do. Investigate the gap before acting.'};
    return{kind:'aligned',label:'Roughly aligned',copy:'FSFFL Intrinsic and the broad market place this player in a similar part of their respective distributions.'};
  }

  function mainDriver(estimate){
    const horizons=(estimate?.horizons||[]).filter(row=>finite(row?.weighted_surplus));
    if(!horizons.length)return'Long-horizon contribution detail is unavailable.';
    const lead=[...horizons].sort((a,b)=>b.weighted_surplus-a.weighted_surplus)[0];
    if(!finite(lead.player_mean)||!finite(lead.replacement_mean))return`Year ${lead.horizon_year} contributes the largest share of modeled surplus.`;
    return `Year ${lead.horizon_year} is the largest modeled contributor: ${lead.player_mean.toFixed(1)} projected points versus ${lead.replacement_mean.toFixed(1)} replacement points before the horizon weight.`;
  }

  function coordinateCards(payload){
    const hasIntrinsic=(payload?.players||[]).some(row=>row.availability==='available');
    return `<div class="value-lens-coordinates" aria-label="FSFFL value coordinates">
      <article><span>Broad Market Value</span><strong>What the wider dynasty market prices</strong><p>Primary magnitude uses the governed 0–10,000 market-cardinal coordinate; ensemble market percentile remains secondary context.</p><small>External market evidence · separate from FSFFL fundamentals</small></article>
      <article class="primary"><span>FSFFL Intrinsic Value</span><strong>${hasIntrinsic?'FSFFL dynasty value from football fundamentals':'Currently unavailable'}</strong><p>The customer-facing 0–10,000 value is a deterministic transform of raw three-year surplus. Raw surplus remains the underlying economic coordinate.</p><small>${hasIntrinsic?`Display scale ${esc(payload?.display_scale?.version||'1')} · model ${esc(payload.model_version||'intrinsic-value-v1')}`:'No substitute value is fabricated'}</small></article>
      <article class="unavailable"><span>League Market Value</span><strong>Not production-ready</strong><p>How this specific league appears to price a player. FSFFL does not substitute broad market or Intrinsic when this evidence is unavailable.</p><small>Unavailable by design</small></article>
      <article><span>Team Utility</span><strong>What the asset does for this franchise</strong><p>Roster fit, competitive timing and trade consequences remain downstream and separate from universal player value.</p><small>Use Franchise Diagnosis and Trade Center</small></article>
    </div>`;
  }

  function rowHtml(row){
    const cmp=row.comparison,entry=row.entry,estimate=entry?.estimate||null,available=entry?.availability==='available';
    return `<details class="value-lens-player" data-signal="${cmp.kind}">
      <summary>
        <span class="value-lens-player-name"><strong>${esc(row.player.full_name)}</strong><small>${esc(row.player.position)}${finite(row.player.age_years)?` · age ${row.player.age_years}`:''}</small></span>
        <span><small>Broad Market Value</small><strong>${valueNumber(row.marketValue)}</strong>${finite(row.marketRank)?`<small>${pct(row.marketRank)}</small>`:'<small>Percentile unavailable</small>'}</span>
        <span><small>FSFFL Intrinsic Value</small><strong>${available?valueNumber(entry.intrinsic_dynasty_value):'Unavailable'}</strong>${available&&finite(entry.percentile)?`<small>${pct(entry.percentile)}</small>`:available?'<small>Rank unavailable</small>':`<small>${esc(entry?.reason||'Evidence incomplete')}</small>`}</span>
        <span class="value-lens-signal"><small>Read</small><strong>${esc(cmp.label)}</strong></span>
      </summary>
      <div class="value-lens-player-detail">
        <div><span>Why this read</span><p>${esc(cmp.copy)}</p><p>${esc(available?mainDriver(estimate):(entry?.reason||'FSFFL Intrinsic is unavailable for this player; no fallback value is shown.'))}</p>${available&&entry.raw_intrinsic_value===0?'<p><strong>Valid zero:</strong> the model produced zero weighted surplus above replacement; this is not missing evidence.</p>':''}</div>
        <div><span>Confidence</span><strong>${esc(available?confidenceLabel(entry.confidence):'Unavailable')}</strong><p>${entry?.evidence_state==='low_evidence'?'The value is available, but deep-horizon evidence is weaker; treat it as directional rather than precise.':available?'The estimate uses governed Forecast evidence; uncertainty still matters.':'No Intrinsic estimate is available.'}</p></div>
        ${available&&estimate?`<details class="value-lens-provenance"><summary>Evidence & provenance</summary><p><b>Displayed scale:</b> ${esc(payloadScaleLabel())}<br><b>Raw Intrinsic:</b> ${finite(entry.raw_intrinsic_value)?entry.raw_intrinsic_value.toFixed(1):'—'} weighted surplus points<br><b>Intrinsic model:</b> ${esc(estimate.model_version||'—')}<br><b>Forecast policy:</b> ${esc(estimate.forecast_policy_version||'—')}<br><b>Base Forecast:</b> ${esc(estimate.base_forecast_model_version||'—')}<br><b>Replacement context:</b> ${esc(estimate.replacement_context_version||'—')}<br><b>As of:</b> ${esc(estimate.evaluation_as_of||'—')}</p></details>`:''}
      </div>
    </details>`;
  }

  let lastPayload=null;
  function payloadScaleLabel(){const scale=lastPayload?.display_scale;return scale?`${scale.scale_id} v${scale.version}`:'fsffl-intrinsic-dynasty-value v1'}

  function legacyPlayerRows(payload){
    const estimates=payload?.estimates||[];
    return estimates.map(estimate=>({player_id:estimate.player_id,availability:'available',evidence_state:estimate.confidence==='low'?'low_evidence':'available',reason:null,raw_intrinsic_value:estimate.value,intrinsic_dynasty_value:null,percentile:null,confidence:estimate.confidence,estimate}));
  }

  function render(payload){
    lastPayload=payload;
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const players=currentPlayers(),entries=payload?.players?.length?payload.players:legacyPlayerRows(payload),byId=new Map(entries.map(row=>[row.player_id,row])),cardinals=marketCardinalMap();
    const rows=players.map(player=>{const entry=byId.get(player.player_id)||{player_id:player.player_id,availability:'unavailable',reason:'Intrinsic evidence is unavailable for this roster player.'},marketRank=marketPercentile(player),marketValue=cardinals.get(player.player_id)??null,available=entry.availability==='available';return{player,entry,marketRank,marketValue,comparison:comparison(entry.percentile,marketRank,available)}})
      .sort((a,b)=>{const ad=finite(a.entry?.percentile)&&finite(a.marketRank)?Math.abs(a.entry.percentile-a.marketRank):-1,bd=finite(b.entry?.percentile)&&finite(b.marketRank)?Math.abs(b.entry.percentile-b.marketRank):-1;return bd-ad||String(a.player.full_name).localeCompare(String(b.player.full_name))});
    const comparable=rows.filter(row=>row.entry?.availability==='available'&&finite(row.entry?.percentile)&&finite(row.marketRank)),disagree=comparable.filter(row=>Math.abs(row.entry.percentile-row.marketRank)>=.07).length;
    host.innerHTML=`<div class="value-lens-shell">
      <header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>Market price and football worth are different questions.</h3><p><strong>Broad Market Value</strong> shows governed dynasty-market magnitude. <strong>FSFFL Intrinsic Value</strong> independently translates FSFFL’s multi-year football economics onto a readable 0–10,000 dynasty scale. Neither is Team Utility, and League Market Value is not yet available.</p></div><div class="value-lens-count"><strong>${disagree}</strong><span>roster player${disagree===1?'':'s'} worth a closer look</span><small>Based on governed rank disagreement</small></div></header>
      ${coordinateCards(payload)}
      <section class="value-lens-read"><div class="value-lens-section-head"><div><p class="eyebrow">Where the lenses disagree</p><h3>Start with the biggest differences.</h3></div><span>${comparable.length} roster players comparable</span></div>
        <p class="value-lens-note">Both primary values use familiar 0–10,000 dynasty-value presentation, but they remain independent coordinates. The disagreement read uses governed distribution rank—not raw point subtraction—so the display transform does not turn Intrinsic into a market-calibrated clone. League-specific pricing and Team Utility still matter.</p>
        <div class="value-lens-players">${rows.length?rows.map(rowHtml).join(''):'<p class="franchise-empty">No roster players are available for this franchise.</p>'}</div>
      </section>
      <section class="value-lens-actions"><div><strong>How to use this</strong><p>If FSFFL is higher than the broad market, investigate whether the player can be acquired near broad-market cost. If the market is higher, investigate whether the market is paying for value FSFFL’s football economics do not support. Finish the decision with league price and team context when available.</p></div><button type="button" class="secondary-button" data-value-lens-market>Open Market</button><button type="button" class="secondary-button" data-value-lens-trade>Open Trade Center</button></section>
      <details class="value-lens-methods"><summary>What exactly is FSFFL Intrinsic Value?</summary><p>The authoritative raw v1 coordinate remains Year 1, Year 2 and Year 3 expected fantasy-point surplus above replacement, weighted 1.00, 0.85 and 0.70. The displayed dynasty value is a versioned, deterministic, market-independent monotonic transform of that raw coordinate onto 0–10,000. Quarterback career-state probabilities live in Forecast; replacement economics live in Value; Broad Market evidence never enters the Intrinsic transform.</p><p><strong>Availability matters:</strong> a valid zero means the model found no positive weighted surplus above replacement. Missing Forecast or replacement evidence is shown as <strong>Unavailable</strong>, never silently converted to zero.</p></details>
    </div>`;
    host.querySelector('[data-value-lens-market]')?.addEventListener('click',()=>window.setRoute?.('opportunities'));
    host.querySelector('[data-value-lens-trade]')?.addEventListener('click',()=>window.setRoute?.('trade_center'));
  }

  function renderUnavailable(message){const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;host.innerHTML=`<div class="value-lens-shell"><header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>FSFFL Intrinsic Value is unavailable right now.</h3><p>${esc(message||'Governed Forecast or Intrinsic evidence is not available for the current league state.')}</p></div></header><div class="value-lens-unavailable"><strong>No substitute number is shown.</strong><p>Broad Market, FSFFL Cardinal market evidence, League Market and Team Utility are different coordinates. FSFFL will not silently use one in place of Intrinsic.</p></div></div>`}

  function requestIsCurrent(generation,sid){return generation===requestGeneration&&sid===stateId()}
  async function load(){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const sid=stateId(),generation=requestGeneration;if(cached&&cachedStateId===sid){render(cached);return}
    host.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Loading governed Intrinsic evidence…</h3><p>Your Franchise view remains usable while this secondary lens loads.</p></div>';
    if(inFlight?.generation===generation&&inFlight?.stateId===sid)return inFlight.promise;
    const promise=(async()=>{try{const result=await api('/api/value/intrinsic-v1');if(!requestIsCurrent(generation,sid))return;cached=result;cachedStateId=sid;render(result)}catch(error){if(!requestIsCurrent(generation,sid))return;renderUnavailable(error?.message||String(error))}finally{if(inFlight?.generation===generation&&inFlight?.stateId===sid)inFlight=null}})();
    inFlight={generation,stateId:sid,promise};
    return promise;
  }

  function activate(panel){panel.querySelectorAll('[data-franchise-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.franchiseTab===TAB)));panel.querySelectorAll('[data-franchise-view]').forEach(section=>section.hidden=section.dataset.franchiseView!==TAB);load()}

  function replaceTextWithin(root,from,to){if(!root)return;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);nodes.forEach(node=>{if(node.parentElement?.closest('.value-lens-view'))return;if(node.nodeValue?.includes(from))node.nodeValue=node.nodeValue.replaceAll(from,to)})}
  function clarifyLegacyLabels(){replaceTextWithin(document.querySelector('.franchise-shell'),'FSFFL Value','FSFFL Cardinal Value');replaceTextWithin(document.querySelector('.league-structure-panel'),'Total FSFFL value','Total FSFFL Cardinal Value')}

  function inject(){
    clarifyLegacyLabels();
    const shell=document.querySelector('.franchise-shell');if(!shell||shell.dataset.valueLensInstalled===VERSION)return;
    const tabs=shell.querySelector('.franchise-tabs');if(!tabs)return;
    shell.dataset.valueLensInstalled=VERSION;
    if(!tabs.querySelector(`[data-franchise-tab="${TAB}"]`)){const button=document.createElement('button');button.type='button';button.setAttribute('role','tab');button.dataset.franchiseTab=TAB;button.setAttribute('aria-selected','false');button.textContent='Value Lens';button.addEventListener('click',()=>activate(shell));tabs.appendChild(button)}
    if(!shell.querySelector(`[data-franchise-view="${TAB}"]`)){const section=document.createElement('section');section.className='franchise-view value-lens-view';section.dataset.franchiseView=TAB;section.hidden=true;section.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Open this lens to compare Market and Intrinsic.</h3></div>';const firstView=shell.querySelector('[data-franchise-view]');firstView?.parentNode?.insertBefore(section,null)}
  }

  function reset(){requestGeneration+=1;cached=null;cachedStateId=null;inFlight=null;lastPayload=null;setTimeout(inject,0)}
  const observer=new MutationObserver(()=>inject());
  function install(){observer.observe(document.body,{childList:true,subtree:true});inject();window.addEventListener('fsffl:product-context-updated',reset)}
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',install,{once:true});else install();
  window.fsfflIntrinsicValueExperience={install,load,version:VERSION};
})();
