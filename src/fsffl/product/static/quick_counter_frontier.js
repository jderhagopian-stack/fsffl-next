/* Interactive counter search: first return a small governed frontier slice.
 * The full 24-point frontier remains available explicitly. This changes only how
 * much NEXT-6 work blocks the first response; every evaluated point still uses the
 * existing governed frontier + bilateral Decision path.
 */
(function(){
  let quickResult=null,quickRequest=null,deepRequest=null,queued=false;
  function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
  async function quick(){
    const request=tradeBeginRequest('frontier');
    const button=qs('#explore-price');if(button){button.disabled=true;button.textContent='Searching…'};
    const target=qs('#trade-frontier-result');if(target)target.innerHTML='<div class="chart-empty"><p>Checking the closest counter paths first…</p></div>';
    try{
      const result=await api('/api/trade-center/frontier/quick',{method:'POST',body:JSON.stringify(tradeDraftPayload())});
      if(!tradeRequestIsCurrent(request))return;tradeRequireCurrentEvidence(result);
      quickResult=result;quickRequest=request;window.fsfflLastQuickFrontier=result;renderTradeFrontierResult(result);schedule();return result;
    }catch(error){if(!tradeRequestIsCurrent(request))return;const node=qs('#trade-frontier-result');if(node)node.innerHTML=`<div class="chart-empty"><p>Counter search is unavailable: ${esc(error.message)}</p></div>`;throw error}
    finally{if(button&&tradeRequestIsCurrent(request)){button.disabled=false;button.textContent='Explore price frontier'}}
  }
  async function deep(){
    if(!quickResult||!tradeScopeIsCurrent(quickRequest)||(deepRequest&&tradeRequestIsCurrent(deepRequest)))return;
    const request=tradeBeginRequest('frontier');deepRequest=request;const zone=document.querySelector('#ns2-counter-zone');if(zone)zone.insertAdjacentHTML('beforeend','<div class="ns2-loading compact" data-deep-frontier-loading><i></i><div><strong>Expanding the search…</strong><span>Testing the wider governed frontier. The current quick results stay visible.</span></div></div>');
    const marker=zone?.querySelector('[data-deep-frontier-loading]');
    try{
      const result=await api('/api/trade-center/frontier',{method:'POST',body:JSON.stringify(tradeDraftPayload())});
      if(!tradeRequestIsCurrent(request))return;tradeRequireCurrentEvidence(result);
      quickResult=null;window.fsfflLastQuickFrontier=null;renderTradeFrontierResult(result);schedule();return result;
    }catch(error){if(!tradeRequestIsCurrent(request))return;if(zone)zone.insertAdjacentHTML('beforeend',`<p class="ns2-muted">Deeper search unavailable: ${esc(error.message)}</p>`);throw error}
    finally{if(deepRequest===request)deepRequest=null;marker?.remove()}
  }
  function enhance(){queued=false;const zone=document.querySelector('#ns2-counter-zone');if(!zone||!quickResult?.deeper_search_available||!tradeScopeIsCurrent(quickRequest)||zone.querySelector('[data-expand-counter-search]'))return;const wrap=document.createElement('div');wrap.className='ns-counter-expand';wrap.innerHTML='<button type="button" class="secondary-button" data-expand-counter-search>Search more counter packages</button><small>The first result checks the nearest governed slice. Expand only if you want the wider search.</small>';wrap.querySelector('button').addEventListener('click',()=>void deep());zone.appendChild(wrap)}
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(enhance)}
  window.exploreTradeFrontier=quick;try{exploreTradeFrontier=quick}catch(_){ }
  window.fsfflExploreDeepFrontier=deep;
  new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',schedule);schedule();
})();
