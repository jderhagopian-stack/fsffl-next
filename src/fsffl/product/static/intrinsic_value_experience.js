/* Phase 3 Franchise Value Lens — canonical Shapley Intrinsic consumer.
 * Presentation only. Model truth comes from governed Value/Market/Team Utility APIs.
 * Broad Market, FSFFL Intrinsic, League Market, and Team Utility remain separate.
 */
(function(){
  'use strict';
  const VERSION='20260921-shapley-franchise3-value-index';
  const TAB='value_lens';
  const MARKET_SCALE='dynasty-market-percentile';
  let cached=null,cachedStateId=null,inFlight=null,requestGeneration=0;
  const POLL_MS=1500,MAX_POLLS=80;

  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'","&#039;");
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const pct=value=>finite(value)?`${Math.round(value*100)}th pct`:'Unavailable';
  const raw=value=>finite(value)?value.toLocaleString(undefined,{maximumFractionDigits:1}):'—';
  const index=value=>finite(value)?Math.round(value).toLocaleString():'Unavailable';
  const words=value=>String(value||'').replaceAll('_',' ');

  function currentView(){try{return typeof fsfflMyTeamState!=='undefined'?fsfflMyTeamState.view:null}catch(_){return null}}
  function currentPlayers(){return currentView()?.players||[]}
  function stateId(){return state?.context?.state_id||currentView()?.context?.league_state_id||null}
  function marketPercentile(player){const estimate=player?.value_profile?.market_price;if(estimate?.scale?.scale_id!==MARKET_SCALE)return null;const value=estimate?.distribution?.mean;return finite(value)?Math.max(0,Math.min(1,value)):null}
  function intrinsicValue(estimate){return finite(estimate?.raw_intrinsic_value)?estimate.raw_intrinsic_value:null}

  function percentileMap(estimates){
    const rows=(estimates||[]).map(row=>({player_id:row.player_id,value:intrinsicValue(row)})).filter(row=>finite(row.value)).sort((a,b)=>a.value-b.value||String(a.player_id).localeCompare(String(b.player_id)));
    const out=new Map(),n=rows.length;if(!n)return out;
    let i=0;while(i<n){let j=i+1;while(j<n&&rows[j].value===rows[i].value)j+=1;const rank=(i+j-1)/2,p=(rank+.5)/n;for(let k=i;k<j;k++)out.set(rows[k].player_id,p);i=j}
    return out;
  }

  function comparison(intrinsicRank,marketRank){
    if(!finite(intrinsicRank)||!finite(marketRank))return{kind:'unavailable',label:'Comparison unavailable',copy:'One of the two comparable rank views is unavailable.'};
    const delta=intrinsicRank-marketRank;
    if(delta>=.10)return{kind:'intrinsic',label:'FSFFL higher than broad market',copy:'FSFFL’s football economics rank this player materially higher than the broad dynasty market does. That is a reason to investigate—not an automatic buy signal.'};
    if(delta<=-.10)return{kind:'market',label:'Broad market higher than FSFFL',copy:'The broad dynasty market ranks this player materially higher than FSFFL’s football economics do. That is a reason to investigate—not an automatic sell signal.'};
    return{kind:'aligned',label:'Roughly aligned',copy:'FSFFL Intrinsic and the broad market place this player in a similar part of their respective distributions.'};
  }

  function mainDriver(estimate){
    const contributions=(estimate?.contributions||[]).filter(row=>finite(row?.discounted_contribution));
    if(!contributions.length)return'Year-by-year Shapley contribution detail is unavailable.';
    const lead=[...contributions].sort((a,b)=>Math.abs(b.discounted_contribution)-Math.abs(a.discounted_contribution))[0];
    return `Year ${lead.year_index} contributes the most discounted Shapley value at ${lead.discounted_contribution.toFixed(1)} marginal fantasy-point units.`;
  }

  function evidenceRead(estimate){
    const paths=(estimate?.contributions||[]).map(row=>words(row?.uncertainty?.evidence_path)).filter(Boolean);
    if(!paths.length)return{label:'Unavailable',copy:'No per-horizon evidence path is available.'};
    const reduced=paths.some(path=>path.includes('fallback')||path.includes('reduced'));
    return reduced
      ?{label:'Governed reduced / fallback path',copy:'Intrinsic remains governed, but at least one future horizon uses an explicit reduced or fallback Forecast path.'}
      :{label:'Governed Forecast path',copy:'All displayed Shapley contributions carry governed Forecast provenance; uncertainty remains horizon-specific.'};
  }

  function lensRow(payload,playerId){return (payload?.value_lenses?.players||[]).find(row=>row.player_id===playerId)||null}

  function coordinateCards(payload){
    const hasIntrinsic=(payload?.estimates||[]).length>0&&payload?.status!=='unavailable';
    return `<div class="value-lens-coordinates" aria-label="FSFFL value coordinates">
      <article><span>Broad Market Value</span><strong>What the wider dynasty market prices</strong><p>Primary display uses the shared 0-10,000 Value Index; percentile remains secondary.</p><small>Universal market lens · separate from FSFFL fundamentals</small></article>
      <article class="primary"><span>FSFFL Intrinsic · Shapley</span><strong>${hasIntrinsic?'What FSFFL football economics imply':'Currently unavailable'}</strong><p>Primary display uses the same 0-10,000 presentation ruler as Broad Market. Raw governed Shapley marginal points remain available in drill-down; market price is not an Intrinsic input.</p><small>${hasIntrinsic?`Contract ${esc(payload.contract_version||'intrinsic-shapley-contract')}`:'No substitute value is fabricated'}</small></article>
      <article class="unavailable"><span>League Market Value</span><strong>Not production-ready</strong><p>How this specific league appears to price a player. FSFFL does not substitute Broad Market or Intrinsic when this evidence is unavailable.</p><small>Unavailable by design</small></article>
      <article><span>Team Utility</span><strong>What the asset does for this franchise</strong><p>Roster fit, competitive timing and trade consequences remain downstream and separate from universal player value.</p><small>Use Franchise Diagnosis and Trade Center</small></article>
    </div>`;
  }

  function rowHtml(row,payload){
    const cmp=row.comparison,estimate=row.estimate,evidence=estimate?evidenceRead(estimate):{label:'Unavailable',copy:'No Intrinsic estimate is available.'};
    return `<details class="value-lens-player" data-signal="${cmp.kind}">
      <summary>
        <span class="value-lens-player-name"><strong>${esc(row.player.full_name)}</strong><small>${esc(row.player.position)}${finite(row.player.age_years)?` · age ${row.player.age_years}`:''}</small></span>
        <span><small>Broad Market</small><strong>${index(row.marketIndex)}</strong><small>${pct(row.market)}</small></span>
        <span><small>FSFFL Intrinsic</small><strong>${index(row.intrinsicIndex)}</strong><small>${pct(row.intrinsicRank)}</small></span>
        <span class="value-lens-signal"><small>Read</small><strong>${esc(cmp.label)}</strong></span>
      </summary>
      <div class="value-lens-player-detail">
        <div><span>Why this read</span><p>${esc(cmp.copy)}</p><p>${esc(estimate?mainDriver(estimate):'FSFFL Intrinsic is unavailable for this player; no fallback value is shown.')}</p></div>
        <div><span>Evidence path</span><strong>${esc(evidence.label)}</strong><p>${esc(evidence.copy)}</p></div>
        ${estimate?`<details class="value-lens-provenance"><summary>Why this value?</summary><p><b>Raw Shapley quantity:</b> ${raw(intrinsicValue(estimate))} marginal fantasy-point units<br><b>Intrinsic contract:</b> ${esc(payload.contract_version||'—')}<br><b>Intrinsic model:</b> ${esc(payload.intrinsic_model_version||'—')}<br><b>Forecast model:</b> ${esc(payload.forecast_model_version||'—')}<br><b>Display coordinate:</b> ${esc(payload.value_lenses?.value_presentation?.contract_version||'unavailable')}<br><b>Quantity:</b> ${esc(payload.quantity_semantics||'—')}<br><b>Discount:</b> ${finite(payload.discount)?payload.discount.toFixed(2):'—'}<br><b>Simulation permutations:</b> ${finite(payload.permutations)?payload.permutations.toLocaleString():'—'}</p></details>`:''}
      </div>
    </details>`;
  }

  function render(payload){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    if(payload?.status==='unavailable'){renderUnavailable(payload?.status_reason||'Governed Shapley Intrinsic evidence is unavailable.');return}
    const players=currentPlayers(),estimates=payload?.estimates||[],byId=new Map(estimates.map(row=>[row.player_id,row])),ranks=percentileMap(estimates);
    const rows=players.map(player=>{const estimate=byId.get(player.player_id)||null,lens=lensRow(payload,player.player_id),intrinsicRank=lens?.intrinsic_percentile??ranks.get(player.player_id)??null,market=lens?.broad_market_percentile??marketPercentile(player),marketIndex=lens?.broad_market_value_index??null,intrinsicIndex=lens?.intrinsic_value_index??null;return{player,estimate,intrinsicRank,market,marketIndex,intrinsicIndex,comparison:comparison(intrinsicRank,market)}})
      .sort((a,b)=>{const ad=finite(a.intrinsicRank)&&finite(a.market)?Math.abs(a.intrinsicRank-a.market):-1,bd=finite(b.intrinsicRank)&&finite(b.market)?Math.abs(b.intrinsicRank-b.market):-1;return bd-ad||String(a.player.full_name).localeCompare(String(b.player.full_name))});
    const comparable=rows.filter(row=>finite(row.intrinsicRank)&&finite(row.market)),disagree=comparable.filter(row=>Math.abs(row.intrinsicRank-row.market)>=.10).length;
    const missing=payload?.coverage?.missing_required_fact_families||[];
    host.innerHTML=`<div class="value-lens-shell">
      <header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>Market price and football worth are different questions.</h3><p>Broad Market tells you how dynasty players generally price an asset. <strong>FSFFL Intrinsic</strong> now uses the canonical governed Shapley economic authority: three-year marginal football contribution, market-independent and separate from Team Utility. League Market Value is not yet available.</p></div><div class="value-lens-count"><strong>${disagree}</strong><span>roster player${disagree===1?'':'s'} worth a closer look</span><small>Based on rank disagreement of 10+ percentile points</small></div></header>
      ${coordinateCards(payload)}
      <section class="value-lens-read"><div class="value-lens-section-head"><div><p class="eyebrow">Where the lenses disagree</p><h3>Start with the biggest differences.</h3></div><span>${comparable.length} roster players comparable</span></div>
        <p class="value-lens-note">Broad Market and FSFFL Intrinsic now use the same versioned 0-10,000 Value Index for presentation, while percentile remains secondary. The Index is percentile-equated from governed native market distributions and does not change either underlying authority. Raw Market and raw Shapley quantities are never subtracted.</p>
        <div class="value-lens-players">${rows.length?rows.map(row=>rowHtml(row,payload)).join(''):'<p class="franchise-empty">No roster players are available for this franchise.</p>'}</div>
      </section>
      <section class="value-lens-actions"><div><strong>How to use this</strong><p>If FSFFL is higher than the broad market, investigate whether the player can be acquired near broad-market cost. If the market is higher, investigate whether the market is paying for value FSFFL’s football economics do not support. Finish the decision with league price and team context when available.</p></div><button type="button" class="secondary-button" data-value-lens-market>Open Market</button><button type="button" class="secondary-button" data-value-lens-trade>Open Trade Center</button></section>
      <details class="value-lens-methods"><summary>What exactly is FSFFL Intrinsic?</summary><p>FSFFL Intrinsic is the governed Shapley economic coordinate. It attributes each player’s marginal contribution to the three-year deployment game, using governed Year 1 and future Forecast evidence with the contract discount. Raw marginal points are audit detail; the primary Value Index is presentation-only. Broad Market, League Market Value and Team Utility are different coordinates and are not inputs to this Intrinsic calculation.</p><p><strong>Authority:</strong> ${esc(payload.intrinsic_model_version||'Shapley Intrinsic')} · ${esc(payload.quantity_semantics||'raw governed Shapley marginal fantasy points')}. The older replacement-surplus endpoint remains compatibility-only and is not this Franchise consumer’s Intrinsic authority.${missing.length?` Missing/reduced fact families remain explicit: ${esc(missing.join(', '))}.`:''}</p></details>
    </div>`;
    host.querySelector('[data-value-lens-market]')?.addEventListener('click',()=>window.setRoute?.('opportunities'));
    host.querySelector('[data-value-lens-trade]')?.addEventListener('click',()=>window.setRoute?.('trade_center'));
  }

  function renderUnavailable(message){const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;host.innerHTML=`<div class="value-lens-shell"><header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>FSFFL Shapley Intrinsic is unavailable right now.</h3><p>${esc(message||'Governed Forecast or Shapley evidence is not available for the current league state.')}</p></div></header><div class="value-lens-unavailable"><strong>No substitute number is shown.</strong><p>Broad Market, League Market Value and Team Utility are different coordinates. FSFFL will not silently use another coordinate in place of canonical Shapley Intrinsic.</p></div></div>`}

  function requestIsCurrent(generation,sid){return generation===requestGeneration&&sid===stateId()}
  async function load(){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const sid=stateId(),generation=requestGeneration;if(cached&&cachedStateId===sid){render(cached);return}
    host.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Loading governed Shapley Intrinsic evidence…</h3><p>Your Franchise view remains usable while this secondary lens loads.</p></div>';
    if(inFlight?.generation===generation&&inFlight?.stateId===sid)return inFlight.promise;
    const promise=(async()=>{try{
      let result=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        result=await api('/api/value/intrinsic-shapley-v1');
        if(!requestIsCurrent(generation,sid))return;
        if(result?.status!=='loading')break;
        host.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Preparing governed FSFFL Intrinsic server-side…</h3><p>Your Franchise view remains usable. This request will stop with an explicit unavailable state instead of spinning indefinitely.</p></div>';
        await new Promise(resolve=>setTimeout(resolve,Number(result?.retry_after_ms)||POLL_MS));
      }
      if(result?.status==='loading')throw new Error('FSFFL Intrinsic is still preparing after two minutes. Try again shortly.');
      if(!requestIsCurrent(generation,sid))return;
      if(result?.status==='unavailable'){renderUnavailable(result?.status_reason||result?.message||'Governed Shapley Intrinsic evidence is unavailable.');return}
      let lenses=null;
      for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
        lenses=await api('/api/league/value-lenses');
        if(!requestIsCurrent(generation,sid))return;
        if(lenses?.status!=='loading')break;
        await new Promise(resolve=>setTimeout(resolve,Number(lenses?.retry_after_ms)||POLL_MS));
      }
      if(lenses?.status==='loading')throw new Error('Shared Value presentation evidence is still preparing after two minutes.');
      result.value_lenses=lenses;
      cached=result;cachedStateId=sid;render(result)
    }catch(error){if(!requestIsCurrent(generation,sid))return;renderUnavailable(error?.message||String(error))}finally{if(inFlight?.generation===generation&&inFlight?.stateId===sid)inFlight=null}})();
    inFlight={generation,stateId:sid,promise};
    return promise;
  }

  function activate(panel){panel.querySelectorAll('[data-franchise-tab]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.franchiseTab===TAB)));panel.querySelectorAll('[data-franchise-view]').forEach(section=>section.hidden=section.dataset.franchiseView!==TAB);load()}

  function replaceTextWithin(root,from,to){if(!root)return;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);nodes.forEach(node=>{if(node.parentElement?.closest('.value-lens-view'))return;if(node.nodeValue?.includes(from))node.nodeValue=node.nodeValue.replaceAll(from,to)})}
  function clarifyLegacyLabels(){}

  function inject(){
    clarifyLegacyLabels();
    const shell=document.querySelector('.franchise-shell');if(!shell||shell.dataset.valueLensInstalled===VERSION)return;
    const tabs=shell.querySelector('.franchise-tabs');if(!tabs)return;
    shell.dataset.valueLensInstalled=VERSION;
    if(!tabs.querySelector(`[data-franchise-tab="${TAB}"]`)){const button=document.createElement('button');button.type='button';button.setAttribute('role','tab');button.dataset.franchiseTab=TAB;button.setAttribute('aria-selected','false');button.textContent='Value Lens';button.addEventListener('click',()=>activate(shell));tabs.appendChild(button)}
    if(!shell.querySelector(`[data-franchise-view="${TAB}"]`)){const section=document.createElement('section');section.className='franchise-view value-lens-view';section.dataset.franchiseView=TAB;section.hidden=true;section.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Open this lens to compare Broad Market and canonical Shapley Intrinsic.</h3></div>';const firstView=shell.querySelector('[data-franchise-view]');firstView?.parentNode?.insertBefore(section,null)}
  }

  function reset(){requestGeneration+=1;cached=null;cachedStateId=null;inFlight=null;setTimeout(inject,0)}
  const observer=new MutationObserver(()=>inject());
  function install(){observer.observe(document.body,{childList:true,subtree:true});inject();window.addEventListener('fsffl:product-context-updated',reset)}
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',install,{once:true});else install();
  window.fsfflIntrinsicValueExperience={install,load,version:VERSION};
})();
