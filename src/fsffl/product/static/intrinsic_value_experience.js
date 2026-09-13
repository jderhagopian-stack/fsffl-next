/* Phase 3 Franchise Value Lens.
 * Presentation only. Model truth comes from governed Value/Market/Team Utility APIs.
 * Broad Market, FSFFL Intrinsic, League Market, and Team Utility remain separate.
 */
(function(){
  'use strict';
  const VERSION='20260913-fundamental-intrinsic-v3';
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

  function percentileMap(estimates){
    const rows=(estimates||[]).filter(row=>finite(row?.fundamental_value)).sort((a,b)=>a.fundamental_value-b.fundamental_value||String(a.player_id).localeCompare(String(b.player_id)));
    const out=new Map(),n=rows.length;if(!n)return out;
    let i=0;while(i<n){let j=i+1;while(j<n&&rows[j].fundamental_value===rows[i].fundamental_value)j+=1;const rank=(i+j-1)/2,p=(rank+.5)/n;for(let k=i;k<j;k++)out.set(rows[k].player_id,p);i=j}
    return out;
  }

  function comparison(intrinsicRank,marketRank,available){
    if(!available)return{kind:'unavailable',label:'Intrinsic unavailable',copy:'FSFFL does not have enough governed Forecast evidence to publish an Intrinsic value for this player.'};
    if(!finite(intrinsicRank)||!finite(marketRank))return{kind:'unavailable',label:'Comparison unavailable',copy:'One of the two comparable rank views is unavailable.'};
    const delta=intrinsicRank-marketRank;
    if(delta>=.18)return{kind:'intrinsic',label:'FSFFL materially higher',copy:'FSFFL’s fundamental football-value rank is materially higher than the broad dynasty market. Investigate the gap; it is not an automatic buy signal.'};
    if(delta>=.07)return{kind:'intrinsic',label:'FSFFL moderately higher',copy:'FSFFL’s fundamental football-value rank is moderately higher than the broad dynasty market. Investigate the gap before acting.'};
    if(delta<=-.18)return{kind:'market',label:'Broad market materially higher',copy:'The broad dynasty market ranks this player materially higher than FSFFL fundamentals do. Investigate the gap; it is not an automatic sell signal.'};
    if(delta<=-.07)return{kind:'market',label:'Broad market moderately higher',copy:'The broad dynasty market ranks this player moderately higher than FSFFL fundamentals do. Investigate the gap before acting.'};
    return{kind:'aligned',label:'Roughly aligned',copy:'FSFFL Intrinsic and the broad market place this player in a similar part of their respective value distributions.'};
  }

  function mainDriver(estimate){
    const horizons=(estimate?.horizons||[]).filter(row=>finite(row?.weighted_mean));
    const lead=horizons.length?[...horizons].sort((a,b)=>b.weighted_mean-a.weighted_mean)[0]:null;
    const terminal=estimate?.terminal;
    if(terminal&&finite(terminal.continuation_value)){
      const pedigree=terminal.pedigree_band?` Draft pedigree is ${terminal.pedigree_band} and contributes only through its validated residual effect on post-Year-3 continuation.`:' No pedigree residual is applied because governed pedigree evidence is unavailable.';
      return `Years 1–3 contribute ${Math.round(estimate.raw_discounted_y1_y3||0)} discounted production units; the governed post-Year-3 continuation contributes ${Math.round(terminal.continuation_value)}.${pedigree}`;
    }
    if(lead)return`Year ${lead.horizon_year} is the largest near-term contributor to the governed career-value profile.`;
    return'Long-horizon contribution detail is unavailable.';
  }

  function coordinateCards(payload){
    const hasIntrinsic=(payload?.estimates||[]).length>0;
    return `<div class="value-lens-coordinates" aria-label="FSFFL value coordinates">
      <article><span>Broad Market Value</span><strong>What the wider dynasty market prices</strong><p>Primary magnitude uses the governed 0–10,000 market-cardinal coordinate; market percentile remains secondary context.</p><small>External market evidence · separate from FSFFL fundamentals</small></article>
      <article class="primary"><span>FSFFL Intrinsic Value</span><strong>${hasIntrinsic?'What FSFFL believes the dynasty asset is fundamentally worth':'Currently unavailable'}</strong><p>Independent long-term football value: governed Y1–Y3 Forecast distributions plus an empirically calibrated post-Y3 continuation value.</p><small>${hasIntrinsic?`Model ${esc(payload.model_version||'intrinsic-fundamental-career-value-v3')}`:'No substitute value is fabricated'}</small></article>
      <article class="unavailable"><span>League Market Value</span><strong>Not production-ready</strong><p>How this specific league appears to price the asset. It will remain a separate price coordinate.</p><small>Unavailable by design</small></article>
      <article><span>Team Utility</span><strong>What the asset does for this franchise</strong><p>Roster fit, lineup replacement, competitive timing and transaction consequences remain downstream.</p><small>Use Franchise Diagnosis and Trade Center</small></article>
    </div>`;
  }

  function rowHtml(row){
    const cmp=row.comparison,estimate=row.estimate,available=!!estimate;
    return `<details class="value-lens-player" data-signal="${cmp.kind}">
      <summary>
        <span class="value-lens-player-name"><strong>${esc(row.player.full_name)}</strong><small>${esc(row.player.position)}${finite(row.player.age_years)?` · age ${row.player.age_years}`:''}</small></span>
        <span><small>Broad Market Value</small><strong>${valueNumber(row.marketValue)}</strong>${finite(row.marketRank)?`<small>${pct(row.marketRank)}</small>`:'<small>Percentile unavailable</small>'}</span>
        <span><small>FSFFL Intrinsic Value</small><strong>${available?valueNumber(estimate.display_value):'Unavailable'}</strong>${finite(row.intrinsicRank)?`<small>${pct(row.intrinsicRank)}</small>`:'<small>Rank unavailable</small>'}</span>
        <span class="value-lens-signal"><small>Read</small><strong>${esc(cmp.label)}</strong></span>
      </summary>
      <div class="value-lens-player-detail">
        <div><span>Why this read</span><p>${esc(cmp.copy)}</p><p>${esc(available?mainDriver(estimate):'FSFFL Intrinsic is unavailable for this player; no fallback value is shown.')}</p></div>
        <div><span>Confidence</span><strong>${esc(available?confidenceLabel(estimate.confidence):'Unavailable')}</strong><p>${estimate?.confidence==='low'?'Deep-horizon Forecast evidence is weaker, so use this as directional evidence rather than false precision.':available?'The estimate uses governed Forecast and historical continuation evidence; uncertainty remains explicit.':'No Intrinsic estimate is available.'}</p></div>
        ${available?`<details class="value-lens-provenance"><summary>Evidence & provenance</summary><p><b>Displayed Intrinsic:</b> ${valueNumber(estimate.display_value)} / 10,000<br><b>Fundamental coordinate:</b> ${finite(estimate.fundamental_value)?estimate.fundamental_value.toFixed(1):'—'} normalized career units<br><b>Raw expected career value:</b> ${finite(estimate.raw_fundamental_career_value)?estimate.raw_fundamental_career_value.toFixed(1):'—'} discounted football units<br><b>Terminal model:</b> ${esc(estimate.terminal?.model_version||'—')}<br><b>Intrinsic model:</b> ${esc(estimate.model_version||'—')}<br><b>Forecast policy:</b> ${esc(estimate.forecast_policy_version||'—')}<br><b>Base Forecast:</b> ${esc(estimate.base_forecast_model_version||'—')}<br><b>As of:</b> ${esc(estimate.evaluation_as_of||'—')}</p></details>`:''}
      </div>
    </details>`;
  }

  function render(payload){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const players=currentPlayers(),estimates=payload?.estimates||[],byId=new Map(estimates.map(row=>[row.player_id,row])),ranks=percentileMap(estimates),cardinals=marketCardinalMap();
    const rows=players.map(player=>{const estimate=byId.get(player.player_id)||null,intrinsicRank=ranks.get(player.player_id)??null,marketRank=marketPercentile(player),marketValue=cardinals.get(player.player_id)??null;return{player,estimate,intrinsicRank,marketRank,marketValue,comparison:comparison(intrinsicRank,marketRank,!!estimate)}})
      .sort((a,b)=>{const ad=finite(a.intrinsicRank)&&finite(a.marketRank)?Math.abs(a.intrinsicRank-a.marketRank):-1,bd=finite(b.intrinsicRank)&&finite(b.marketRank)?Math.abs(b.intrinsicRank-b.marketRank):-1;return bd-ad||String(a.player.full_name).localeCompare(String(b.player.full_name))});
    const comparable=rows.filter(row=>row.estimate&&finite(row.intrinsicRank)&&finite(row.marketRank)),disagree=comparable.filter(row=>Math.abs(row.intrinsicRank-row.marketRank)>=.07).length;
    host.innerHTML=`<div class="value-lens-shell">
      <header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>Market price and fundamental dynasty worth are different questions.</h3><p><strong>Broad Market Value</strong> is what the wider dynasty market prices the asset at. <strong>FSFFL Intrinsic Value</strong> is FSFFL’s independent estimate of long-term dynasty asset worth from football fundamentals. Both use a familiar 0–10,000 presentation language, but neither is derived from the other.</p></div><div class="value-lens-count"><strong>${disagree}</strong><span>roster player${disagree===1?'':'s'} worth a closer look</span><small>Based on governed rank disagreement</small></div></header>
      ${coordinateCards(payload)}
      <section class="value-lens-read"><div class="value-lens-section-head"><div><p class="eyebrow">Where the lenses disagree</p><h3>Start with the biggest differences.</h3></div><span>${comparable.length} roster players comparable</span></div>
        <p class="value-lens-note">The two primary numbers are directly comparable as dynasty-value magnitudes, but independently generated. The read classification uses distribution rank as a stable diagnostic; disagreement is a reason to investigate, not a BUY/SELL command. League-specific pricing and Team Utility still determine transaction context.</p>
        <div class="value-lens-players">${rows.length?rows.map(rowHtml).join(''):'<p class="franchise-empty">No roster players are available for this franchise.</p>'}</div>
      </section>
      <section class="value-lens-actions"><div><strong>How to use this</strong><p>If FSFFL is higher than the broad market, investigate whether the market may be underpricing the football asset. If the market is higher, investigate what the market may be pricing that FSFFL fundamentals do not support. Finish the decision with acquisition cost, League Market and Team Utility.</p></div><button type="button" class="secondary-button" data-value-lens-market>Open Market</button><button type="button" class="secondary-button" data-value-lens-trade>Open Trade Center</button></section>
      <details class="value-lens-methods"><summary>What exactly is FSFFL Intrinsic Value?</summary><p>Fundamental Intrinsic is a market-independent long-term dynasty asset coordinate. It discounts the governed Year 1–3 Forecast distributions and adds an empirically calibrated post-Year-3 continuation value. The continuation model was validated on point-in-time football evidence; only draft pedigree retained robust incremental information on the final long-horizon target, so separate age/experience bonuses are not layered on top of Forecast. Replacement surplus, Broad Market, League Market, Team Utility and owner behavior are not Intrinsic inputs.</p><p>The 0–10,000 number is a separate monotonic presentation normalization of that fundamental coordinate. It makes the coordinate readable beside Market Value; it does not train Intrinsic to market prices.</p></details>
    </div>`;
    host.querySelector('[data-value-lens-market]')?.addEventListener('click',()=>window.setRoute?.('opportunities'));
    host.querySelector('[data-value-lens-trade]')?.addEventListener('click',()=>window.setRoute?.('trade_center'));
  }

  function renderUnavailable(message){const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;host.innerHTML=`<div class="value-lens-shell"><header class="value-lens-hero"><div><p class="eyebrow">Value Lens</p><h3>FSFFL Intrinsic Value is unavailable right now.</h3><p>${esc(message||'Governed Forecast or Intrinsic evidence is not available for the current league state.')}</p></div></header><div class="value-lens-unavailable"><strong>No substitute number is shown.</strong><p>Broad Market, League Market and Team Utility are different coordinates. FSFFL will not silently use one in place of Intrinsic.</p></div></div>`}

  function requestIsCurrent(generation,sid){return generation===requestGeneration&&sid===stateId()}
  async function load(){
    const host=document.querySelector('[data-franchise-view="value_lens"]');if(!host)return;
    const sid=stateId(),generation=requestGeneration;if(cached&&cachedStateId===sid){render(cached);return}
    host.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Loading governed Fundamental Intrinsic evidence…</h3><p>Your Franchise view remains usable while this secondary lens loads.</p></div>';
    if(inFlight?.generation===generation&&inFlight?.stateId===sid)return inFlight.promise;
    const promise=(async()=>{try{const result=await api('/api/value/intrinsic-v2');if(!requestIsCurrent(generation,sid))return;cached=result;cachedStateId=sid;render(result)}catch(error){if(!requestIsCurrent(generation,sid))return;renderUnavailable(error?.message||String(error))}finally{if(inFlight?.generation===generation&&inFlight?.stateId===sid)inFlight=null}})();
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
    if(!shell.querySelector(`[data-franchise-view="${TAB}"]`)){const section=document.createElement('section');section.className='franchise-view value-lens-view';section.dataset.franchiseView=TAB;section.hidden=true;section.innerHTML='<div class="value-lens-loading"><p class="eyebrow">Value Lens</p><h3>Open this lens to compare Market and Fundamental Intrinsic.</h3></div>';const firstView=shell.querySelector('[data-franchise-view]');firstView?.parentNode?.insertBefore(section,null)}
  }

  function reset(){requestGeneration+=1;cached=null;cachedStateId=null;inFlight=null;setTimeout(inject,0)}
  const observer=new MutationObserver(()=>inject());
  function install(){observer.observe(document.body,{childList:true,subtree:true});inject();window.addEventListener('fsffl:product-context-updated',reset)}
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',install,{once:true});else install();
  window.fsfflIntrinsicValueExperience={install,load,version:VERSION};
})();
