/* Market route availability hotfix.
 * Navigation only. The Market surface already owns its own no-team/readiness states,
 * so the route must remain reachable even before managed-team context is ready.
 */
(function(){
  let queued=false;
  function unlockMarket(){
    queued=false;
    document.querySelectorAll('[data-product-route="opportunities"],[data-product-mobile-route="opportunities"],[data-direct-route="opportunities"],[data-route="opportunities"]').forEach(button=>{
      button.disabled=false;
      button.classList.remove('locked');
      button.removeAttribute('aria-disabled');
      button.querySelector('small')?.remove();
    });
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(unlockMarket)}
  const observer=new MutationObserver(schedule);
  const start=()=>{observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','class']});unlockMarket()};
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('fsffl:product-context-updated',schedule);
  window.addEventListener('load',schedule,{once:true});
  const corrected=document.createElement('script');
  corrected.src='/static/north_star_market.js?v=20260911-market-route1';
  corrected.defer=true;
  corrected.dataset.marketRouteFix='true';
  document.head.appendChild(corrected);
})();
