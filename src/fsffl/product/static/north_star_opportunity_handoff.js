/* North Star Opportunity -> Trade Center context bridge.
 * Workflow metadata only. Trade Center still revalidates canonical assets and owns
 * the bilateral workflow; this bridge carries the Market status/evaluation context
 * so the user does not lose where the candidate came from.
 */
(function(){
  let meta=null;
  const words=value=>String(value||'').replaceAll('_',' ');
  const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const refs=items=>(items||[]).map(item=>item.asset_ref).filter(Boolean);
  function rowKey(row){return `${row?.counterparty_team_id||''}:${refs(row?.send).join('+')}:${refs(row?.receive).join('+')}`}
  function capture(row){
    let result=null;try{if(typeof fsfflOpportunityState!=='undefined'&&fsfflOpportunityState.tradeEvaluationKey===rowKey(row))result=fsfflOpportunityState.tradeEvaluation}catch(_){ }
    meta={
      rowKey:rowKey(row),
      targetPosition:row?.target_position||null,
      searchStatus:row?.bilateral_decision_evaluated?'evaluated':'needs full evaluation',
      actionAuthority:result?.action_authority||row?.action_authority||row?.recommendation_authority||null,
      disposition:result?.disposition?.disposition||row?.focal_decision_shape||null,
      simulationCount:Number(result?.scenario_simulation_count||0),
    };
    window.fsfflOpportunityHandoffMeta=meta;
  }
  function decorate(){
    const banner=document.querySelector('#trade-workflow-handoff');if(!banner||!meta||banner.querySelector('.ns-opportunity-handoff-context'))return;
    const host=banner.querySelector('div');if(!host)return;
    const block=document.createElement('div');block.className='ns-opportunity-handoff-context';
    const authority=meta.actionAuthority?words(meta.actionAuthority):'not yet evaluated',disposition=meta.disposition?words(meta.disposition):'pending';
    block.innerHTML=`<span>Market context carried forward</span><strong>${esc(authority)}</strong><small>${esc(disposition)}${meta.simulationCount?` · ${meta.simulationCount.toLocaleString()} simulations`:''}</small>`;
    host.appendChild(block);
  }
  function install(){
    if(typeof window.fsfflOpenOpportunityInTradeCenter!=='function'||window.fsfflOpenOpportunityInTradeCenter.nsContextWrapped)return false;
    const prior=window.fsfflOpenOpportunityInTradeCenter;
    const wrapped=async function(row){capture(row);const output=await prior(row);requestAnimationFrame(decorate);return output};
    wrapped.nsContextWrapped=true;window.fsfflOpenOpportunityInTradeCenter=wrapped;return true;
  }
  const style=document.createElement('style');style.id='ns-opportunity-handoff-context-style';style.textContent='.ns-opportunity-handoff-context{display:grid;grid-template-columns:auto 1fr;gap:2px 8px;margin-top:9px;padding-top:8px;border-top:1px solid var(--line)}.ns-opportunity-handoff-context>span{grid-column:1/-1;font-size:9px;color:var(--muted)}.ns-opportunity-handoff-context>strong{font-size:11px;text-transform:capitalize}.ns-opportunity-handoff-context>small{font-size:10px!important;text-transform:capitalize}';document.head.appendChild(style);
  if(!install()){const timer=setInterval(()=>{if(install())clearInterval(timer)},50);setTimeout(()=>clearInterval(timer),5000)}
  const observer=new MutationObserver(decorate);observer.observe(document.documentElement,{childList:true,subtree:true});
})();
