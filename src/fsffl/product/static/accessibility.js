function installFsfflAccessibility(){
  if(document.documentElement.dataset.fsfflA11y==='ready')return;
  document.documentElement.dataset.fsfflA11y='ready';

  const main=document.querySelector('.main-panel');
  if(main&&!main.id)main.id='main-content';
  if(main&&!document.querySelector('.skip-link')){
    const skip=document.createElement('a');
    skip.className='skip-link';skip.href='#main-content';skip.textContent='Skip to main content';
    document.body.prepend(skip);
  }

  const syncNavigationAccessibility=()=>{
    document.querySelectorAll('.nav-item').forEach(button=>{
      const active=button.classList.contains('active');
      if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
      if(button.classList.contains('locked')){button.setAttribute('aria-disabled','true');button.title='Select a managed team to open this section'}else{button.removeAttribute('aria-disabled')}
    });
  };
  syncNavigationAccessibility();

  const sidebar=document.querySelector('.sidebar');
  const mobileMenu=document.querySelector('#mobile-menu');
  if(sidebar&&mobileMenu){
    mobileMenu.setAttribute('aria-controls','primary-nav');
    mobileMenu.setAttribute('aria-expanded',String(sidebar.classList.contains('open')));
    const observer=new MutationObserver(()=>mobileMenu.setAttribute('aria-expanded',String(sidebar.classList.contains('open'))));
    observer.observe(sidebar,{attributes:true,attributeFilter:['class']});
  }

  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&sidebar?.classList.contains('open')){
      sidebar.classList.remove('open');
      mobileMenu?.focus();
    }
  });

  const navObserver=new MutationObserver(syncNavigationAccessibility);
  const nav=document.querySelector('#primary-nav');if(nav)navObserver.observe(nav,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});

  document.querySelectorAll('table').forEach(table=>{
    if(!table.getAttribute('role'))table.setAttribute('role','table');
  });

  const style=document.createElement('style');
  style.textContent=`
    .skip-link{position:fixed;left:12px;top:-60px;z-index:1000;background:#fff;color:#07101c;padding:10px 14px;border-radius:8px;font-weight:800;text-decoration:none;transition:top .15s ease}
    .skip-link:focus{top:12px}
    button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
    .nav-item[aria-current="page"]{box-shadow:inset 3px 0 0 var(--accent)}
    .nav-item[aria-disabled="true"]{cursor:not-allowed}
    button,.nav-item,.asset-option,.draft-chip,summary{touch-action:manipulation}
    @media(pointer:coarse){button,.nav-item,select,input,summary{min-height:44px}.text-button{min-height:44px}.asset-option{min-height:52px}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition-duration:.001ms!important;animation-duration:.001ms!important;animation-iteration-count:1!important}}
    @media(max-width:620px){.table-wrap{margin-inline:-14px;padding-inline:14px;scrollbar-width:thin}.table-wrap::after{content:'Swipe horizontally for more';display:block;color:var(--muted);font-size:10px;padding-top:6px;text-align:right}.nav-item{min-height:46px}}
  `;
  document.head.appendChild(style);
}

window.installFsfflAccessibility=installFsfflAccessibility;
