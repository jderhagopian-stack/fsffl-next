/* Server-owned Market Focus refresh.
 * Strategic posture and explicit task choices alter Search selection/order only.
 * State, Value, Decision and acceptance semantics remain unchanged.
 */
(function(){
  let requestSeq=0,queued=false;
  function stateRef(){try{return typeof fsfflOpportunityState!=='undefined'?fsfflOpportunityState:null}catch(_){return null}}
  function selected(){
    const posture=window.fsfflOpportunityPosture?.selectedPosture?.()||'default_calculated';
    const intent=window.fsfflMarketIntent?.selected?.()||{intent:'',value:''};
    return{posture,intent:intent.intent||'',value:intent.value||''};
  }
  function onMarket(){try{return Boolean(window.state?.route==='opportunities'||state?.route==='opportunities')}catch(_){return false}}
  function setBusy(busy){
    const control=document.querySelector('#opp-posture-control');if(!control)return;
    control.classList.toggle('ns-focus-refreshing',busy);
    control.setAttribute('aria-busy',busy?'true':'false');
    let status=control.querySelector('.ns-focus-refresh-status');
    if(!status){status=document.createElement('div');status.className='ns-focus-refresh-status';control.appendChild(status)}
    status.textContent=busy?'Refreshing opportunity search…':'Search updated';
    if(!busy)setTimeout(()=>{if(status?.isConnected)status.textContent=''},1200)
  }
  function updateMethods(){
    const p=document.querySelector('#opp-posture-control .opp-posture-methods p');if(!p)return;
    p.textContent='Market Focus is applied by server-owned Trade Finder search before the candidate limit. Position, target and consolidation narrow the full structural search; Shop a player rebuilds package neighborhoods around that asset. Strategic direction changes Search ordering only. Your calculated competitive state, FSFFL Value, Decision truth and acceptance uncertainty do not change.';
  }
  async function refresh(){
    if(!onMarket())return;const s=stateRef();if(!s?.payload||s.payload.status!=='ready')return;
    const id=++requestSeq,{posture,intent,value}=selected();setBusy(true);
    try{
      const params=new URLSearchParams({posture,intent,value});
      const payload=await api(`/api/opportunities/focused-workspace?${params.toString()}`);
      if(id!==requestSeq||!onMarket())return;
      const context=window.state?.context||state?.context||{};
      if(payload?.league_state_id&&context.state_id&&payload.league_state_id!==context.state_id)return;
      if(payload?.focal_team_id&&context.team_id&&payload.focal_team_id!==context.team_id)return;
      s.payload=payload;s.nsSelectedTradeKey='';s.nsVisibleCount=4;s.tradeEvaluation=null;s.tradeEvaluationKey=null;
      if(typeof renderOpportunityWorkspace==='function')renderOpportunityWorkspace();
      window.dispatchEvent(new CustomEvent('fsffl:market-focus-applied',{detail:payload.trade_discovery?.focus||{posture,intent,value}}));
    }catch(error){
      const control=document.querySelector('#opp-posture-control');if(control){let status=control.querySelector('.ns-focus-refresh-status');if(!status){status=document.createElement('div');status.className='ns-focus-refresh-status';control.appendChild(status)}status.textContent=`Unable to refresh search: ${error.message}`}
    }finally{if(id===requestSeq)setBusy(false);updateMethods()}
  }
  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;updateMethods()})}
  window.addEventListener('fsffl:market-intent-changed',()=>void refresh());
  window.addEventListener('fsffl:market-rendered',schedule);
  window.addEventListener('fsffl:product-context-updated',()=>{requestSeq+=1;schedule()});
  document.addEventListener('DOMContentLoaded',schedule);
})();
