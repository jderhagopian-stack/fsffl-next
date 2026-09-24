/* Phase 3 Intrinsic-vs-Broad-Market discovery lens.
 * Lazy-loads only after the customer opens the lens.
 * The shared 0-10,000 Value Index is presentation-only; raw Market and raw
 * Shapley remain distinct authorities. No recommendation or acceptance
 * probability is created here.
 */
(function(){
  'use strict';

  const VERSION='20260921-intrinsic-market-discovery3-value-index';
  let open=false;
  let cached=null;
  let cachedStateId=null;
  let cachedTeamId=null;
  let inFlight=null;
  let generation=0;
  let queued=false;
  const POLL_MS=1500,MAX_POLLS=80;

  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'","&#039;");
  const finite=value=>typeof value==='number'&&Number.isFinite(value);
  const pct=value=>finite(value)?`${Math.round(value*100)}th pct`:'Unavailable';
  const index=value=>finite(value)?Math.round(value).toLocaleString():'Unavailable';
  const signedPct=value=>finite(value)?`${value>=0?'+':''}${Math.round(value*100)} pct pts`:'Unavailable';
  function currentContext(){
    try{
      const ctx=window.state?.context||state?.context||{};
      return{stateId:ctx.state_id||null,teamId:ctx.team_id||null};
    }catch(_){return{stateId:null,teamId:null}}
  }
  function onMarket(){
    try{return Boolean(window.state?.route==='opportunities'||state?.route==='opportunities')}
    catch(_){return false}
  }
  function marketReady(){
    try{return Boolean(typeof fsfflOpportunityState!=='undefined'&&fsfflOpportunityState?.payload?.status==='ready')}
    catch(_){return false}
  }
  function host(){
    const panel=document.querySelector('#generic-screen .panel');
    if(!panel||!onMarket()||!marketReady())return null;
    return panel;
  }
  function cacheMatches(){
    const ctx=currentContext();
    return cached&&cached.status==='ready'&&cachedStateId===ctx.stateId&&cachedTeamId===ctx.teamId;
  }
  function requestIsCurrent(requestGeneration,stateId,teamId){
    const ctx=currentContext();
    return requestGeneration===generation&&stateId===ctx.stateId&&teamId===ctx.teamId&&onMarket();
  }
  function directionCopy(row){
    return row?.direction==='intrinsic_higher'
      ? 'FSFFL Intrinsic ranks this player higher than the broad market.'
      : 'The broad market ranks this player higher than FSFFL Intrinsic.';
  }
  function actionLabel(row){
    return row?.focus_intent==='shop'?'Explore as a shop candidate':'Explore as a target';
  }
  function rowMarkup(row,index){
    const tone=row.direction==='intrinsic_higher'?'intrinsic':'market';
    return `<article class="imd-row" data-tone="${tone}">
      <div class="imd-player">
        <button type="button" class="pi-player-link" data-player-intelligence-id="${esc(row.player_id)}"><strong>${esc(row.full_name)}</strong></button>
        <small>${esc(row.position||'')}${finite(row.age_years)?` · age ${row.age_years}`:''} · ${esc(row.owner_team_name||'Owner unavailable')}</small>
      </div>
      <div><small>Broad Market</small><strong>${index(row.market_value_index)}</strong><span>${pct(row.market_percentile)}</span></div>
      <div><small>FSFFL Intrinsic</small><strong>${index(row.intrinsic_value_index)}</strong><span>${pct(row.intrinsic_percentile)}</span></div>
      <div class="imd-gap"><small>Value Index difference</small><strong>${finite(row.value_index_gap)?`${row.value_index_gap>=0?'+':''}${index(row.value_index_gap)}`:'Unavailable'}</strong><span>${esc(directionCopy(row))}</span></div>
      <button type="button" class="secondary-button" data-imd-focus="${index}">${esc(actionLabel(row))}</button>
    </article>`;
  }
  function unavailableMarkup(payload){
    return `<div class="imd-empty"><strong>Value disagreement lens unavailable.</strong><p>${esc(payload?.message||'Governed Broad Market or Intrinsic evidence is unavailable for this league state.')}</p><small>No substitute value or recommendation is fabricated.</small></div>`;
  }
  function bodyMarkup(payload){
    if(!payload||payload.status!=='ready')return unavailableMarkup(payload);
    const rows=Array.isArray(payload.rows)?payload.rows:[];
    if(!rows.length)return `<div class="imd-empty"><strong>No material rank disagreements surfaced.</strong><p>Broad Market and FSFFL Intrinsic are within the current 10-percentile-point discovery threshold for comparable rostered players.</p></div>`;
    return `<div class="imd-summary"><strong>${payload.disagreement_count} player${payload.disagreement_count===1?'':'s'} worth investigating</strong><span>${payload.comparable_player_count} comparable rostered players · 10+ percentile-point rank gap</span></div>
      <div class="imd-rows">${rows.map(rowMarkup).join('')}</div>`;
  }
  function shellMarkup(payload,loading=false){
    return `<section class="imd-shell" data-version="${VERSION}">
      <header class="imd-head">
        <div><p class="eyebrow">Value disagreement</p><h3>Where market price and football worth diverge</h3><p>Broad Market and FSFFL Intrinsic share the same <strong>0-10,000 Value Index</strong> for presentation. Percentile remains secondary. A disagreement is a reason to investigate—not a buy/sell instruction.</p></div>
        <button type="button" class="text-button" data-imd-close>Close</button>
      </header>
      ${loading?'<div class="imd-loading"><i></i><span>Preparing governed Intrinsic server-side. This will end in ready or an explicit unavailable state.</span></div>':bodyMarkup(payload)}
      <details class="imd-methods"><summary>Methods & authority</summary><p>The 0-10,000 Value Index is a presentation-only percentile-equated ruler derived from governed native Market distributions. Broad Market and raw Shapley remain different authorities; raw Market and raw Shapley quantities are never subtracted. The displayed Index gap is allowed only because both display numbers use the same versioned ruler. League Market Value remains unavailable. Team Utility and acceptance evidence remain separate.</p></details>
    </section>`;
  }
  function installTrigger(panel){
    let trigger=panel.querySelector('[data-imd-trigger]');
    if(trigger)return trigger;
    const external=panel.querySelector('[data-market-disagreement]');
    if(external){
      if(external.dataset.imdWired!=='true'){external.dataset.imdWired='true';external.addEventListener('click',()=>{open=true;render();void load()})}
      return external;
    }
    const control=panel.querySelector('#opp-posture-control');
    const nav=panel.querySelector('.ns-market-mode-nav');
    const northStar=panel.querySelector('.market-ns-tabs');
    if(!control&&!nav&&!northStar)return null;
    const wrap=document.createElement('div');
    wrap.className='imd-trigger';
    wrap.innerHTML='<div><small>Another discovery lens</small><strong>Market vs. Intrinsic</strong><span>Find players where broad-market rank and FSFFL football economics materially disagree.</span></div><button type="button" class="secondary-button" data-imd-trigger>Open value disagreements</button>';
    (control||nav||northStar).insertAdjacentElement('afterend',wrap);
    trigger=wrap.querySelector('[data-imd-trigger]');
    trigger.addEventListener('click',()=>{open=true;render();void load()});
    return trigger;
  }
  function render(){
    const panel=host();
    if(!panel)return;
    installTrigger(panel);
    let shell=panel.querySelector('.imd-shell');
    if(!open){shell?.remove();return}
    const markup=shellMarkup(cacheMatches()?cached:null,Boolean(inFlight&&!cacheMatches()));
    if(shell){
      if(shell.outerHTML!==markup)shell.outerHTML=markup;
    }else{
      const trigger=panel.querySelector('.imd-trigger');
      if(!trigger)return;
      trigger.insertAdjacentHTML('afterend',markup);
    }
    shell=panel.querySelector('.imd-shell');
    shell?.querySelector('[data-imd-close]')?.addEventListener('click',()=>{open=false;render()});
    shell?.querySelectorAll('[data-imd-focus]').forEach(button=>button.addEventListener('click',()=>{
      const row=(cached?.rows||[])[Number(button.dataset.imdFocus)];
      if(!row)return;
      const setter=window.fsfflMarketIntent?.set;
      if(typeof setter!=='function')return;
      setter(row.focus_intent,row.focus_value);
      open=false;
      render();
    }));
  }
  async function load(){
    if(cacheMatches()){render();return cached}
    if(inFlight)return inFlight;
    const ctx=currentContext(),requestGeneration=generation;
    if(!ctx.stateId||!ctx.teamId)return null;
    render();
    const promise=(async()=>{
      try{
        let payload=null;
        for(let attempt=0;attempt<MAX_POLLS;attempt+=1){
          payload=await api('/api/opportunities/value-disagreements?minimum_gap=0.10&limit=24');
          if(!requestIsCurrent(requestGeneration,ctx.stateId,ctx.teamId))return null;
          if(payload?.status!=='loading')break;
          await new Promise(resolve=>setTimeout(resolve,Number(payload?.retry_after_ms)||POLL_MS));
        }
        if(payload?.status==='loading')throw new Error('Value Disagreement evidence is still preparing after two minutes. Try again shortly.');
        if(payload?.league_state_id&&payload.league_state_id!==ctx.stateId)return null;
        if(payload?.focal_team_id&&payload.focal_team_id!==ctx.teamId)return null;
        cached=payload;cachedStateId=ctx.stateId;cachedTeamId=ctx.teamId;
        return payload;
      }catch(error){
        if(!requestIsCurrent(requestGeneration,ctx.stateId,ctx.teamId))return null;
        cached={status:'unavailable',message:error?.message||String(error),rows:[]};
        cachedStateId=ctx.stateId;cachedTeamId=ctx.teamId;
        return cached;
      }finally{
        if(requestGeneration===generation)inFlight=null;
        render();
      }
    })();
    inFlight=promise;
    render();
    return promise;
  }
  function reset(){
    generation+=1;
    cached=null;cachedStateId=null;cachedTeamId=null;inFlight=null;open=false;
    schedule();
  }
  function enhance(){
    queued=false;
    const panel=host();
    if(!panel)return;
    installTrigger(panel);
    render();
  }
  function schedule(){
    if(queued)return;
    queued=true;
    requestAnimationFrame(enhance);
  }

  const observer=new MutationObserver(schedule);
  function start(){
    observer.observe(document.body,{childList:true,subtree:true});
    schedule();
  }
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('fsffl:market-rendered',schedule);
  window.addEventListener('fsffl:market-intent-changed',schedule);
  window.addEventListener('fsffl:product-context-updated',reset);
  window.fsfflIntrinsicMarketDiscovery={load,open:()=>{open=true;render();return load()},version:VERSION};
})();
