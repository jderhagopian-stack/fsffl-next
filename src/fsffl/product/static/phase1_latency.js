(function(){
  const pending=new Map();
  const now=()=>window.performance?.now?.()??Date.now();
  function post(operation,elapsedMs,outcome='success',detail=null){
    if(!Number.isFinite(elapsedMs)||elapsedMs<0)return;
    fetch('/api/performance/latency',{
      method:'POST',
      headers:{'Accept':'application/json','Content-Type':'application/json'},
      body:JSON.stringify({operation,elapsed_ms:elapsedMs,outcome,detail}),
      keepalive:true,
    }).catch(()=>{});
  }
  function start(operation,detail=null){pending.set(operation,{started:now(),detail})}
  function finish(operation,outcome='success',detail=null){const item=pending.get(operation);if(!item)return;pending.delete(operation);post(operation,Math.max(0,now()-item.started),outcome,detail??item.detail)}
  window.fsfflPhase1Latency={start,finish,post};

  document.addEventListener('click',event=>{
    const target=event.target?.closest?.('[data-route="opportunities"],[data-direct-route="opportunities"]');
    if(target)start('opportunities_ready');
    const deep=event.target?.closest?.('[data-trade-eval],#opp-waiver-run,#simulate-trade');
    if(deep)start('explicit_deep_analysis',deep.id||deep.dataset?.tradeEval||'opportunity');
  },true);

  function inspect(){
    if(pending.has('opportunities_ready')&&document.querySelector('#generic-screen .opp-summary'))finish('opportunities_ready');
    if(pending.has('explicit_deep_analysis')&&document.querySelector('.opp-trade-result,.opp-waiver-result,.beta-trade-summary.final,#trade-simulation-result:not(:empty)'))finish('explicit_deep_analysis');
  }
  function observe(){const root=document.querySelector('#screen');if(!root)return;new MutationObserver(inspect).observe(root,{childList:true,subtree:true});inspect()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',observe,{once:true});else observe();
})();
