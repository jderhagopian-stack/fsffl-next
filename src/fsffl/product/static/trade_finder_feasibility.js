(function(){
  const labels={
    mutual_gain_candidate:'Both sides show calculated gains',
    counterparty_dominated:'Other team takes a calculated loss',
    mixed:'Mixed bilateral impact',
    neutral:'Near-neutral bilateral impact',
    incomplete:'Decision evidence incomplete'
  };
  const priorLabel=window.oppDecisionLabel;
  const priorDetail=window.oppDecisionDetail;

  window.oppDecisionLabel=function(row){
    if(row?.negotiation_feasibility_evaluated){
      return labels[row.negotiation_feasibility_shape]||'Bilateral impact evaluated';
    }
    return typeof priorLabel==='function'?priorLabel(row):'Not evaluated';
  };

  window.oppDecisionDetail=function(row){
    if(row?.negotiation_feasibility_evaluated){
      const focal=String(row.focal_decision_shape||'unknown').replaceAll('_',' ');
      const other=String(row.counterparty_decision_shape||'unknown').replaceAll('_',' ');
      return `Decision feasibility only — not an acceptance probability. You: ${focal} · Other team: ${other}`;
    }
    return typeof priorDetail==='function'?priorDetail(row):'Outside the current fast Decision-enrichment budget.';
  };

  function assetMeta(item){
    const parts=[];
    if(item?.detail)parts.push(String(item.detail));
    if(typeof item?.age_years==='number'&&Number.isFinite(item.age_years)){
      parts.push(`Age ${item.age_years.toFixed(1).replace(/\.0$/,'')}`);
    }
    if(item?.roster_slot)parts.push(String(item.roster_slot).replaceAll('_',' '));
    return parts.join(' · ');
  }

  window.oppAssetListMarkup=function(items){
    const rows=items||[];
    if(!rows.length)return'—';
    return`<div class="opp-asset-stack">${rows.map(item=>{
      const label=oppEscape(item.label||item.asset_ref);
      const meta=assetMeta(item);
      return`<div><strong>${label}</strong>${meta?`<span class="opp-asset-meta">${oppEscape(meta)}</span>`:''}<small>FSFFL Value ${oppValue(item.fsffl_value)}</small></div>`;
    }).join('')}</div>`;
  };

  const oldNote='Search starts with positions your optimized lineup is weakest at, checks whether what you would send may fit the other roster, then uses authoritative Cardinal Value distance to find plausible structures. It searches both 1-for-1 and 2-for-1 consolidation shapes. Use Evaluate offer for the full changed-state Decision; Search itself remains diagnostic.';
  const newNote='Search starts with authoritative Cardinal Value to find economically plausible structures. Roster need and counterparty fit then help prioritize which plausible trades deserve attention. One-for-one and two-for-one structures remain diagnostic until Decision evaluates the changed rosters.';
  const oldLead='Search uses current roster construction, optimized positional strength and authoritative Cardinal Value to surface plausible structures. Explicit evaluation attaches full changed-state evidence and directional Behavioral fit; unknown acceptance remains separate and prevents FSFFL from pretending a supported offer is guaranteed to be accepted.';
  const newLead='Search uses authoritative Cardinal Value first to locate market-plausible structures, then current roster construction and optimized positional strength to add team context. Explicit evaluation attaches full changed-state Decision evidence and directional Behavioral fit; unknown acceptance remains separate.';

  function alignCopy(){
    document.querySelectorAll('#opportunity-body .opp-note span').forEach(node=>{
      if(node.textContent.trim()===oldNote)node.textContent=newNote;
    });
    document.querySelectorAll('#generic-screen .panel > .lead').forEach(node=>{
      if(node.textContent.trim()===oldLead)node.textContent=newLead;
    });
  }

  const observer=new MutationObserver(alignCopy);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('DOMContentLoaded',alignCopy);

  const style=document.createElement('style');
  style.id='trade-finder-context-style';
  style.textContent='.opp-asset-meta{color:var(--muted);font-size:11px;text-transform:capitalize}.opp-asset-stack>div{display:grid;gap:2px}';
  document.head.appendChild(style);
})();
