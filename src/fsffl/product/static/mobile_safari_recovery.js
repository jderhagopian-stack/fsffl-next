let fsfflMobileHiddenAt=null;
let fsfflMobileResumeInFlight=false;
let fsfflMobileResumeToken=0;

function fsfflIsMobileSafari(){
  const ua=navigator.userAgent||'';
  const ios=/iP(hone|ad|od)/.test(ua)||(/Macintosh/.test(ua)&&navigator.maxTouchPoints>1);
  const webkit=/WebKit/.test(ua);
  const otherIosBrowser=/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
  return ios&&webkit&&!otherIosBrowser;
}

function fsfflForceMobileRepaint(){
  const shell=document.querySelector('.app-shell');
  const body=document.body;
  if(!body)return;
  body.style.visibility='visible';
  body.style.opacity='1';
  body.style.minHeight='100dvh';
  if(shell){
    shell.style.visibility='visible';
    shell.style.opacity='1';
  }
  void body.offsetHeight;
  requestAnimationFrame(()=>requestAnimationFrame(()=>window.dispatchEvent(new Event('resize'))));
}

async function fsfflRehydrateAfterMobileResume(reason){
  if(!fsfflIsMobileSafari()||document.visibilityState==='hidden'||fsfflMobileResumeInFlight)return;
  fsfflMobileResumeInFlight=true;
  const token=++fsfflMobileResumeToken;
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),5000);
  try{
    fsfflForceMobileRepaint();
    let context=null;
    try{
      const response=await fetch('/api/product-context',{headers:{Accept:'application/json'},cache:'no-store',signal:controller.signal});
      if(response.ok)context=await response.json();
    }catch(error){
      console.warn('Mobile Safari resume context check failed',reason,error);
    }
    if(token!==fsfflMobileResumeToken)return;
    if(context&&typeof state!=='undefined'){
      state.context=context;
      if(typeof applyContext==='function')applyContext();
    }
    if((!context?.league_id)&&typeof fsfflRestoreSession==='function'){
      try{await fsfflRestoreSession()}catch(error){console.warn('Mobile Safari session restore failed',error)}
    }
    if(typeof state!=='undefined'&&typeof setRoute==='function'){
      try{setRoute(state.route||'league')}catch(error){console.warn('Mobile Safari route restore failed',error)}
    }
    fsfflForceMobileRepaint();
  }finally{
    clearTimeout(timeout);
    fsfflMobileResumeInFlight=false;
  }
}

function fsfflMarkMobileHidden(){
  if(fsfflIsMobileSafari())fsfflMobileHiddenAt=Date.now();
}

function fsfflHandleMobileVisible(reason){
  if(!fsfflIsMobileSafari())return;
  const hiddenFor=fsfflMobileHiddenAt==null?0:Date.now()-fsfflMobileHiddenAt;
  fsfflMobileHiddenAt=null;
  fsfflForceMobileRepaint();
  if(hiddenFor>=750||reason==='pageshow')void fsfflRehydrateAfterMobileResume(reason);
}

document.addEventListener('visibilitychange',()=>{
  if(document.visibilityState==='hidden')fsfflMarkMobileHidden();
  else fsfflHandleMobileVisible('visibilitychange');
});
window.addEventListener('pagehide',fsfflMarkMobileHidden);
window.addEventListener('pageshow',()=>fsfflHandleMobileVisible('pageshow'));
window.addEventListener('focus',()=>fsfflHandleMobileVisible('focus'));
