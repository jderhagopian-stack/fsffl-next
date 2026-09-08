(function(){
  const oldNote='Search starts with positions your optimized lineup is weakest at, checks whether what you would send may fit the other roster, then uses authoritative Cardinal Value distance to find plausible structures. It searches both 1-for-1 and 2-for-1 consolidation shapes. Use Evaluate offer for the full changed-state Decision; Search itself remains diagnostic.';
  const newNote='Search starts with authoritative Cardinal Value to find economically plausible structures. Roster need and counterparty fit then help prioritize which plausible trades deserve attention. One-for-one and two-for-one structures remain diagnostic until Decision evaluates the changed rosters.';
  const oldLead='Search uses current roster construction, optimized positional strength and authoritative Cardinal Value to surface plausible structures. Explicit evaluation attaches full changed-state evidence and directional Behavioral fit; unknown acceptance remains separate and prevents FSFFL from pretending a supported offer is guaranteed to be accepted.';
  const newLead='Search uses authoritative Cardinal Value first to locate market-plausible structures, then current roster construction and optimized positional strength to add team context. Explicit evaluation attaches full changed-state Decision evidence and directional Behavioral fit; unknown acceptance remains separate.';

  function assetMeta(item){
    const parts=[];
    if(item.detail)parts.push(String(item.detail));
    if(typeof item.age_years==='number'&&Number.isFinite(item.age_years))parts.push(`Age ${item.age_years.toFixed(1).replace(/\.0$/,'')}`);
    if(item.roster_slot)parts.push(String(item.roster_slot).replaceAll('_',' '));
    return parts.join(' · ');
  }

  window.oppAssetListMarkup=function(items){
    const rows=items||[];
    if(!rows.length)return'—';
    return`<div class="opp-asset-stack">${rows.map(item=>{
      const label=window.oppEscape?window.oppEscape(item.label||item.asset_ref):String(item.label||item.asset_ref||'');
      const meta=assetMeta(item);
      const safeMeta=window.oppEscape?window.oppEscape(meta):meta;
      const value=window.oppValue?window.oppValue(item.fsffl_value):String(item.fsffl_value??'—');
      return`<div><strong>${label}</strong>${meta?`<span class="opp-asset-meta">${safeMeta}</span>`:''}<small>FSFFL Value ${value}</small></div>`;
    }).join('')}</div>`;
  };

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
  style.id='trade-finder-presentation-style';
  style.textContent='.opp-asset-meta{color:var(--muted);font-size:11px;text-transform:capitalize}.opp-asset-stack>div{display:grid;gap:2px}';
  document.head.appendChild(style);
})();
