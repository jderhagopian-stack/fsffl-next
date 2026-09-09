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

function fsfflContextsEquivalent(a,b){
  if(!a||!b)return false;
  return a.league_id===b.league_id&&a.team_id===b.team_id&&a.state_id===b.state_id;
}

async function fsfflRehydrateAfterMobileResume(reason){
  if(!fsfflIsMobileSafari()||document.visibilityState==='hidden'||fsfflMobileResumeInFlight)return;
  fsfflMobileResumeInFlight=true;
  const token=++fsfflMobileResumeToken;
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),4000);
  try{
    let context=null;
    try{
      const response=await fetch('/api/product-context',{headers:{Accept:'application/json'},cache:'no-store',signal:controller.signal});
      if(response.ok)context=await response.json();
    }catch(error){
      console.warn('Mobile Safari resume context check failed',reason,error);
    }
    if(token!==fsfflMobileResumeToken)return;
    if(context&&typeof state!=='undefined'&&!fsfflContextsEquivalent(state.context,context)){
      state.context=context;
      if(typeof applyContext==='function')applyContext();
    }
    if((!context?.league_id)&&typeof fsfflRestoreSession==='function'){
      try{await fsfflRestoreSession()}catch(error){console.warn('Mobile Safari session restore failed',error)}
    }
  }finally{
    clearTimeout(timeout);
    fsfflMobileResumeInFlight=false;
  }
}

function fsfflMarkMobileHidden(){
  if(fsfflIsMobileSafari())fsfflMobileHiddenAt=Date.now();
}

function fsfflHandleMobileVisible(reason){
  if(!fsfflIsMobileSafari()||fsfflMobileHiddenAt==null)return;
  const hiddenFor=Date.now()-fsfflMobileHiddenAt;
  fsfflMobileHiddenAt=null;
  if(hiddenFor>=750)void fsfflRehydrateAfterMobileResume(reason);
}

document.addEventListener('visibilitychange',()=>{
  if(document.visibilityState==='hidden')fsfflMarkMobileHidden();
  else fsfflHandleMobileVisible('visibilitychange');
});
window.addEventListener('pagehide',fsfflMarkMobileHidden);
window.addEventListener('pageshow',event=>{
  if(event.persisted&&fsfflMobileHiddenAt!=null)fsfflHandleMobileVisible('pageshow-bfcache');
});
