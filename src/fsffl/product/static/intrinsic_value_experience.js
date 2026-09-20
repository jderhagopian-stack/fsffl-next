/* Phase 3 Franchise Value Lens.
 * Presentation only. Model truth comes from governed Value/Market/Team Utility APIs.
 * Broad Market, FSFFL Intrinsic, League Market, and Team Utility remain separate.
 */
(function(){
  'use strict';
  const VERSION='20260913-phase3-intrinsic2';
  const TAB='value_lens';
  const MARKET_SCALE='dynasty-market-percentile';
  let cached=null,cachedStateId=null,inFlight=null,requestGeneration=0;

  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const pct=value=>finite(value)?`${Math.round(value*100)}th pct`:'Unavailable';
  const raw=value=>finite(value)?value.toLocaleString(undefined,{maximumFractionDigits:1}):'—';
  const words=value=>String(value||'').replaceAll('_',' ');

  function currentView(){try{return typeof fsfflMyTeamState!=='undefined'?fsfflMyTeamState.view:null}catch(_){return null}}
  function currentPlayers(){return currentView()?.players||[]}
  function stateId(){return state?.context?.state_id||currentView()?.context?.league_state_id||null}
  function marketPercentile(player){const estimate=player?.value_profile?.market_price;if(estimate?.scale?.scale_id!==MARKET_SCALE)return null;const value=estimate?.distribution?.mean;return finite(value)?Math.max(0,Math.min(1,value)):null}
  function confidenceLabel(value){const label=words(value||'unavailable');return label.charAt(0).toUpperCase()+label.slice(1)}

  function percentileMap(estimates){
    const rows=(estimates||[]).filter(row=>finite(row?.value)).sort((a,b)=>a.value-b.value||String(a.player_id).localeCompare(String(b.player_id)));
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
    const horizons=(estimate?.horizons||[]).filter(row=>finite(row?.weighted_surplus));
    if(!horizons.length)return'Long-horizon contribution detail is unavailable.';
    const lead=[...horizons].sort((a,b)=>b.weighted_surplus-a.weighted_surplus)[0];
    if(!finite(lead.player_mean)||!finite(lead.replacement_mean))return`Year ${lead.horizon_year} contributes the largest share of modeled surplus.`;
    return `Year ${lead.horizon_year} is the largest modeled contributor: ${lead.player_mean.toFixed(1)} projected points versus ${lead.replacement_mean.toFixed(1)} replacement points before the horizon weight.`;
  }

  function coordinateCards(payload){
    const hasIntrinsic=(payload?.estimates||[]).length>0;
    return `<div class="value-lens-coordinates" aria-label="FSFFL value coordinates">
      <article><span>Broad Market Value</span><strong>What the wider dynasty market prices</strong><p>Shown here as the current broad-market percentile when market evidence is available.</p><small>Universal market lens · separate from FSFFL fundamentals</small></article>
      <article class="primary"><span>FSFFL Intrinsic v1 · replacement surplus</span><strong>${hasIntrinsic?'What FSFFL football economics imply':'Currently unavailable'}</strong><p>Three-year weighted expected fantasy-point surplus above lineup replacement, using governed Forecast evidence.</p><small>${hasIntrinsic?`Model ${esc(payload.model_version||'intrinsic-value-v1')}`:'No substitute value is fabricated'}</small></article>
      <article class="unavailable"><span>League Market Value</span><strong>Not production-ready</strong><p>How this specific league appears to price a player. FSFFL does not substitute broad market or Intrinsic when this evidence is unavailable.</p><small>Unavailable by design</small></article>
      <article><span>Team Utility</span><strong>What the asset does for this franchise</strong><p>Roster fit, competitive timing and trade consequences remain downstream and separate from universal player value.</p><small>Use Franchise Diagnosis and Trade Center</small></article>
    </div>`;
  }

  function rowHtml(row){
    const cmp=row.comparison,estimate=row.estimate;
    return `<details class="value-lens-player" data-signal="${cmp.kind}">
      <summary>
        <span class="value-lens-player-name"><strong>${esc(row.player.full_name)}</strong><small>${esc(row.player.position)}${finite(row.player.age_years)?` · age ${row.player.age_years}`:''}</small></span>
        <span><small>Broad market</small><strong>${pct(row.market)}</strong></span>
        <span><small>FSFFL Intrinsic</small><strong>${estimate?`${raw(estimate.value)} pts`:'Unavailable'}</strong>${finite(row.intrinsicRank)?`<small>${pct(row.intrinsicRank)} display rank</small>`:''}</span>
        <span class="value-lens-signal"><small>Read</small><strong>${esc(cmp.label)}</strong></span>
      </summary>
      <div class="value-lens-player-detail">
        <div><span>Why this read</span><p>${esc(cmp.copy)}</p><p>${esc(estimate?mainDriver(estimate):'FSFFL Intrinsic is unavailable for this player; no fallback value is shown.')}</p></div>
        <div><span>Confidence</span><strong>${esc(estimate?confidenceLabel(estimate.confidence):'Unavailable')}</strong><p>${estimate?.confidence==='low'?'Long-horizon evidence is weaker, so use this as directional evidence rather than precise certainty.':estimate?'The estimate uses governed Forecast evidence; uncertainty still matters.':'No Intrinsic estimate is available.'}</p></div>
        ${estimate?`<details class="value-lens-provenance"><summary>Evidence & provenance</summary><p><b>Intrinsic model:</b> ${esc(estimate.model_version||'—')}<br><b>Forecast policy:</b> ${esc(estimate.forecast_policy_version||'—')}<br><b>Base Forecast:</b> ${esc(estimate.base_forecast_model_version||'—')}<br><b>Replacement context:</b> ${esc(estimate.replacement_context_version||'—')}<br><b>As of:</b> ${esc(estimate.evaluation_as_of||'—')}</p></details>`:''}
      </div>
    </details>`;
  }

  function render(payload){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const players=currentPlayers(),estimates=payload?.estimates||[],byId=new Map(estimates.map(row=>[row.player_id,row])),ranks=percentileMap(estimates);
    const rows=players.map(player=>{const estimate=byId.get(player.player_id)||null,intrinsicRank=ranks.get(player.player_id)??null,market=marketPercentile(player);return{player,estimate,intrinsicRank,market,comparison:comparison(intrinsicRank,market)}})
      .sort((a,b)=>{const ad=finite(a.intrinsicRank)&&finite(a.market)?Math.abs(a.intrinsicRank-a.market):-1,bd=finite(b.intrinsicRank)&&finite(b.market)?Math.abs(b.intrinsicRank-b.market):-1;return bd-ad||String(a.player.full_name).localeCompare(String(b.player.full_name))});
    const comparable=rows.filter(row=>finite(row.intrinsicRank)&&finite(row.market)),disagree=comparable.filter(row=>Math.abs(row.intrinsicRank-row.market)>=.10).length;
    host.innerHTML=`<div class="value-lens-shell">
      <header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>Market price and football worth are different questions.</h3><p>Broad Market tells you how dynasty players generally price an asset. <strong>This replacement-surplus Intrinsic v1 lens</strong> asks how much multi-year football surplus the player projects to create above lineup replacement. Shapley Intrinsic, used by current Market disagreement and the Atlas comparison contract, is a separate deployment-attribution coordinate. Neither is Team Utility, and League Market Value is not yet available.</p></div><div class="value-lens-count"><strong>${disagree}</strong><span>roster player${disagree===1?'':'s'} worth a closer look</span><small>Based on rank disagreement of 10+ percentile points</small></div></header>
      ${coordinateCards(payload)}
      <section class="value-lens-read"><div class="value-lens-section-head"><div><p class="eyebrow">Where the lenses disagree</p><h3>Start with the biggest differences.</h3></div><span>${comparable.length} roster players comparable</span></div>
        <p class="value-lens-note">The comparison uses percentile rank only as a presentation aid because Broad Market and Intrinsic use different units. FSFFL does <strong>not</strong> subtract the raw numbers or turn disagreement into a buy/sell command. League-specific pricing and Team Utility still matter.</p>
        <div class="value-lens-players">${rows.length?rows.map(rowHtml).join(''):'<p class="franchise-empty">No roster players are available for this franchise.</p>'}</div>
      </section>
      <section class="value-lens-actions"><div><strong>How to use this</strong><p>If FSFFL is higher than the broad market, investigate whether the player can be acquired near broad-market cost. If the market is higher, investigate whether the market is paying for value FSFFL’s football economics do not support. Finish the decision with league price and team context when available.</p></div><button type="button" class="secondary-button" data-value-lens-market>Open Market</button><button type="button" class="secondary-button" data-value-lens-trade>Open Trade Center</button></section>
      <details class="value-lens-methods"><summary>What exactly is replacement-surplus Intrinsic v1?</summary><p>Replacement-surplus Intrinsic v1 is a raw, market-independent coordinate. It combines Year 1, Year 2 and Year 3 expected fantasy-point surplus above replacement with weights 1.00, 0.85 and 0.70. Quarterback career-state probabilities live in Forecast; replacement economics live in Value. Market evidence is not an Intrinsic input.</p><p><strong>Important:</strong> the older generic “FSFFL Value” shown in parts of the private beta is a separate beta coordinate and is not this Intrinsic value. This slice labels governed Cardinal evidence explicitly as <strong>FSFFL Cardinal Value</strong> wherever it decorates the current Franchise/League view.</p></details>
    </div>`;
    host.querySelector('[data-value-lens-market]')?.addEventListener('click',()=>window.setRoute?.('opportunities'));
    host.querySelector('[data-value-lens-trade]')?.addEventListener('click',()=>window.setRoute?.('trade_center'));
  }

  function renderUnavailable(message){const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;host.innerHTML=`<div class="value-lens-shell"><header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>Replacement-surplus Intrinsic v1 is unavailable right now.</h3><p>${esc(message||'Governed Forecast or Intrinsic evidence is not available for the current league state.')}</p></div></header><div class="value-lens-unavailable"><strong>No substitute number is shown.</strong><p>Broad Market, the older beta FSFFL value, League Market and Team Utility are different coordinates. FSFFL will not silently use one in place of Intrinsic.</p></div></div>`}

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

  function reset(){requestGeneration+=1;cached=null;cachedStateId=null;inFlight=null;setTimeout(inject,0)}
  const observer=new MutationObserver(()=>inject());
  function install(){observer.observe(document.body,{childList:true,subtree:true});inject();window.addEventListener('fsffl:product-context-updated',reset)}
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',install,{once:true});else install();
  window.fsfflIntrinsicValueExperience={install,load,version:VERSION};
})();
