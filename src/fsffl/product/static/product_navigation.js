/* FSFFL NEXT product hierarchy shell.
 * Presentation/navigation only. No model truth, Search ordering, Decision logic,
 * Value, Simulation or Behavioral inference lives here.
 */
(function(){
  const PRIMARY=[
    {route:'my_team',label:'Franchise',short:'Franchise',question:'What is driving my team?',icon:'franchise',teamScoped:true},
    {route:'league_comparison',label:'League',short:'League',question:'How does this league fit together?',icon:'league'},
    {route:'opportunities',label:'Explore',short:'Explore',question:'Where is there something worth doing?',icon:'market'},
    {route:'trade_center',label:'Trade',short:'Trade',question:'What does this deal change?',icon:'trade',teamScoped:true},
  ];
  const LEAGUE_INTELLIGENCE=[
    {route:'behavioral_intelligence',label:'Owners',description:'Understand observed manager behavior.',icon:'owner'},
  ];
  const SCENARIOS=[
    {route:'what_if',label:'What-If',description:'Stress-test one roster availability change.',icon:'scenario',teamScoped:true},
    {route:'simulator',label:'Simulator',description:'Test multiple roster shocks together.',icon:'simulation',teamScoped:true},
  ];
  const ANALYSIS=[
    {route:'reports',label:'Reports',description:'Read polished decision intelligence.',icon:'report'},
    {route:'analytics',label:'Analytics',description:'Investigate the governed evidence stack.',icon:'analytics'},
  ];
  const COMPATIBILITY=[
    {route:'league',label:'Franchise',question:'Connect a league and select the franchise you manage.'},
  ];
  const SECONDARY=[...LEAGUE_INTELLIGENCE,...SCENARIOS,...ANALYSIS];
  const ALL=[...PRIMARY,...SECONDARY,...COMPATIBILITY];
  let installed=false;
  let moreReturnFocus=null;

  function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
  function routeMeta(route){return ALL.find(item=>item.route===route)||{route,label:String(route||'FSFFL NEXT'),question:'Decision intelligence for your league.'}}
  function hasTeam(){return Boolean(state?.context?.team_id)}
  function locked(item){return Boolean(item.teamScoped&&!hasTeam())}
  function secondaryActive(){return SECONDARY.some(item=>item.route===state?.route)}
  function icon(name){
    const paths={
      franchise:'<circle cx="12" cy="8" r="3.2"/><path d="M5.5 20c.7-4 3-6 6.5-6s5.8 2 6.5 6"/>',
      league:'<path d="M4 5h16v14H4z"/><path d="M4 10h16M9 5v14M15 5v14"/>',
      market:'<path d="M4 18V9m5 9V5m5 13v-6m5 6V3"/><path d="m3 8 5-3 5 5 7-7"/>',
      trade:'<path d="M4 8h13l-3-3m3 3-3 3M20 16H7l3-3m-3 3 3 3"/>',
      owner:'<circle cx="12" cy="8" r="3"/><path d="M5 20c.8-4.2 3.1-6.2 7-6.2s6.2 2 7 6.2"/>',
      scenario:'<path d="M5 5v14M19 5v14M5 8c4 0 4 3 7 3s3-3 7-3M5 16c4 0 4-3 7-3s3 3 7 3"/>',
      simulation:'<path d="M5 19V9l7-5 7 5v10z"/><path d="M9 19v-6h6v6"/>',
      report:'<path d="M6 3h9l3 3v15H6z"/><path d="M15 3v4h4M9 11h6M9 15h6"/>',
      analytics:'<path d="M4 19h16M6 16v-5m4 5V6m4 10v-8m4 8v-3"/>',
      more:'<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
    };
    return `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths[name]||paths.more}</svg>`;
  }
  function go(route){closeMore(false);if(typeof window.setRoute==='function')window.setRoute(route)}
  function desktopButton(item){const isActive=state?.route===item.route,isLocked=locked(item);return `<button type="button" class="nav-item product-nav-item${isActive?' active':''}${isLocked?' locked':''}" data-product-route="${esc(item.route)}" ${isLocked?'disabled':''} ${isActive?'aria-current="page"':''}>${icon(item.icon)}<span><strong>${esc(item.label)}</strong>${item.question?`<small>${esc(item.question)}</small>`:''}</span></button>`}
  function desktopMoreButton(){const isActive=secondaryActive();return `<button type="button" class="nav-item product-nav-item product-nav-more${isActive?' active':''}" data-product-more ${isActive?'aria-current="page"':''}>${icon('more')}<span><strong>More</strong><small>More league tools and analysis</small></span></button>`}
  function renderDesktop(){
    const nav=document.querySelector('#primary-nav');if(!nav)return;
    nav.className='nav-list product-desktop-nav';
    nav.innerHTML=PRIMARY.map(desktopButton).join('')+desktopMoreButton();
    nav.querySelectorAll('[data-product-route]').forEach(button=>button.addEventListener('click',()=>{if(!button.disabled)go(button.dataset.productRoute)}));
    const moreButton=nav.querySelector('[data-product-more]');moreButton?.addEventListener('click',()=>openMore(moreButton));
  }
  function moreRow(item){const isLocked=locked(item);return `<button type="button" class="product-more-row" data-product-more-route="${esc(item.route)}" ${isLocked?'disabled':''}>${icon(item.icon)}<span><strong>${esc(item.label)}</strong><small>${esc(isLocked?'Select a managed franchise first.':item.description||'')}</small></span><b aria-hidden="true">›</b></button>`}
  function ensureMore(){
    let backdrop=document.querySelector('#product-more-backdrop');
    if(!backdrop){backdrop=document.createElement('div');backdrop.id='product-more-backdrop';backdrop.className='product-more-backdrop';backdrop.hidden=true;backdrop.addEventListener('click',()=>closeMore());document.body.appendChild(backdrop)}
    let sheet=document.querySelector('#product-more-sheet');
    if(!sheet){sheet=document.createElement('section');sheet.id='product-more-sheet';sheet.className='product-more-sheet';sheet.hidden=true;sheet.setAttribute('role','dialog');sheet.setAttribute('aria-modal','true');sheet.setAttribute('aria-label','More FSFFL destinations');document.body.appendChild(sheet)}
    sheet.innerHTML=`<div class="product-more-handle" aria-hidden="true"></div><div class="product-more-head"><div><p class="eyebrow">More</p><h2>More league tools.</h2></div><button type="button" class="icon-button" data-product-more-close aria-label="Close More menu">×</button></div><div class="product-more-group"><span>League intelligence</span>${LEAGUE_INTELLIGENCE.map(moreRow).join('')}</div><div class="product-more-group"><span>Scenarios</span>${SCENARIOS.map(moreRow).join('')}</div><div class="product-more-group"><span>Reports & analysis</span>${ANALYSIS.map(moreRow).join('')}</div>`;
    sheet.querySelector('[data-product-more-close]')?.addEventListener('click',()=>closeMore());
    sheet.querySelectorAll('[data-product-more-route]').forEach(button=>button.addEventListener('click',()=>{if(!button.disabled)go(button.dataset.productMoreRoute)}));
    return sheet;
  }
  function openMore(trigger){const sheet=ensureMore(),backdrop=document.querySelector('#product-more-backdrop');moreReturnFocus=trigger||document.activeElement;if(backdrop)backdrop.hidden=false;sheet.hidden=false;requestAnimationFrame(()=>document.body.classList.add('product-more-open'));sheet.querySelector('[data-product-more-close]')?.focus()}
  function closeMore(restoreFocus=true){document.body.classList.remove('product-more-open');const sheet=document.querySelector('#product-more-sheet'),backdrop=document.querySelector('#product-more-backdrop');if(sheet)sheet.hidden=true;if(backdrop)backdrop.hidden=true;if(restoreFocus&&moreReturnFocus?.isConnected)moreReturnFocus.focus();moreReturnFocus=null}
  function trapMoreFocus(event){const sheet=document.querySelector('#product-more-sheet');if(event.key!=='Tab'||!sheet||sheet.hidden)return;const focusable=[...sheet.querySelectorAll('button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])')].filter(node=>!node.hidden);if(!focusable.length){event.preventDefault();return}const first=focusable[0],last=focusable[focusable.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}else if(!sheet.contains(document.activeElement)){event.preventDefault();first.focus()}}
  function renderMobile(){
    document.querySelector('#mobile-direct-nav')?.remove();
    let nav=document.querySelector('#product-mobile-nav');if(!nav){nav=document.createElement('nav');nav.id='product-mobile-nav';nav.className='product-mobile-nav';nav.setAttribute('aria-label','Primary product navigation');document.body.appendChild(nav)}
    const current=state?.route;
    nav.innerHTML=PRIMARY.map(item=>{const isActive=current===item.route,isLocked=locked(item);return `<button type="button" data-product-mobile-route="${esc(item.route)}" ${isLocked?'disabled':''} ${isActive?'aria-current="page"':''}>${icon(item.icon)}<span>${esc(item.short)}</span></button>`}).join('')+`<button type="button" data-product-more ${secondaryActive()?'aria-current="page"':''}>${icon('more')}<span>More</span></button>`;
    nav.querySelectorAll('[data-product-mobile-route]').forEach(button=>button.addEventListener('click',()=>{if(!button.disabled)go(button.dataset.productMobileRoute)}));
    const moreButton=nav.querySelector('[data-product-more]');moreButton?.addEventListener('click',()=>openMore(moreButton));
    ensureMore();
  }
  function renderRouteContext(){
    const topbar=document.querySelector('.topbar');if(!topbar)return;
    let node=document.querySelector('#product-route-context');if(!node){node=document.createElement('div');node.id='product-route-context';node.className='product-route-context';topbar.insertBefore(node,topbar.querySelector('.context-controls')||topbar.firstChild)}
    const meta=routeMeta(state?.route||'league');
    node.innerHTML=`<strong>${esc(meta.label)}</strong><span>${esc(meta.question||meta.description||'')}</span>`;
  }
  function renderAll(){document.body.classList.add('fsffl-product-architecture');renderDesktop();renderMobile();renderRouteContext()}
  function install(){
    if(installed)return;installed=true;
    const previous=window.setRoute;
    if(typeof previous==='function'){
      window.setRoute=function(route){const result=previous(route);renderAll();return result};
      try{setRoute=window.setRoute}catch(_){ }
    }
    window.addEventListener('fsffl:product-context-updated',()=>setTimeout(renderAll,0));
    window.addEventListener('load',renderAll,{once:true});
    window.addEventListener('keydown',event=>{if(event.key==='Escape'&&!document.querySelector('#product-more-sheet')?.hidden){event.preventDefault();closeMore();return}trapMoreFocus(event)});
    window.addEventListener('resize',()=>{if(window.innerWidth>980&&document.body.classList.contains('product-more-open'))closeMore(false)});
    renderAll();
  }
  window.fsfflProductArchitecture={primary:PRIMARY,secondary:SECONDARY,leagueIntelligence:LEAGUE_INTELLIGENCE,scenarios:SCENARIOS,analysis:ANALYSIS};
  window.installFsfflProductArchitecture=install;
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
