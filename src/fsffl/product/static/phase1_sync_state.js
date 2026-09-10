(function(){
  const labels={
    checking:['Checking league updates','Stored league is usable while Sleeper is revalidated.'],
    current:['League data current','Latest provider check completed successfully.'],
    stale:['Using stored league','Sleeper refresh is unavailable right now. Your last valid stored league remains usable.'],
  };
  function ensure(){
    let node=document.querySelector('#fsffl-sync-state');
    if(node)return node;
    const topbar=document.querySelector('.topbar');
    if(!topbar)return null;
    node=document.createElement('div');
    node.id='fsffl-sync-state';
    node.className='fsffl-sync-state';
    node.setAttribute('role','status');
    node.setAttribute('aria-live','polite');
    topbar.insertAdjacentElement('afterend',node);
    return node;
  }
  function set(state,detail=null){
    const node=ensure();
    if(!node||!labels[state])return;
    const [title,copy]=labels[state];
    node.dataset.state=state;
    node.innerHTML=`<strong>${title}</strong><span>${detail||copy}</span>`;
    node.hidden=false;
  }
  function clear(){const node=document.querySelector('#fsffl-sync-state');if(node)node.hidden=true}
  function installStyles(){
    if(document.querySelector('#fsffl-sync-state-style'))return;
    const style=document.createElement('style');
    style.id='fsffl-sync-state-style';
    style.textContent='.fsffl-sync-state{margin:8px 18px 0;padding:8px 11px;border:1px solid var(--line);border-radius:10px;background:#0a1120;display:flex;gap:8px;align-items:center;font-size:12px}.fsffl-sync-state span{color:var(--muted)}.fsffl-sync-state[data-state="stale"]{border-color:var(--warning,#d9a441)}@media(max-width:760px){.fsffl-sync-state{margin:7px 10px 0;display:grid;gap:2px}}';
    document.head.appendChild(style);
  }
  installStyles();
  window.fsfflSyncState={set,clear};
  window.addEventListener('fsffl:sync-state',event=>{
    const detail=event.detail||{};
    if(detail.state)set(detail.state,detail.message||null);
  });
  const pending=window.fsfflPendingSyncState;
  if(pending?.state)set(pending.state,pending.message||null);
})();
