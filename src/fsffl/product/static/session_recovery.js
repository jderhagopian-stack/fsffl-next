const fsfflSessionKeys={league:'fsffl:last-sleeper-league',team:'fsffl:last-team'};
const fsfflOriginalApi=api;
let fsfflRestoringSession=false;

function fsfflRememberSessionRequest(path,options,result){
  try{
    if(path==='/api/connect/sleeper'&&options?.body){
      const payload=JSON.parse(options.body);if(payload?.league_external_id)localStorage.setItem(fsfflSessionKeys.league,payload.league_external_id);
      if(result?.team_id)localStorage.setItem(fsfflSessionKeys.team,result.team_id);
    }
    if(path==='/api/select-team'&&options?.body){
      const payload=JSON.parse(options.body);if(payload?.team_id)localStorage.setItem(fsfflSessionKeys.team,payload.team_id);
    }
  }catch(_){ }
}

async function fsfflRestoreSession(){
  if(fsfflRestoringSession)return false;
  const leagueId=localStorage.getItem(fsfflSessionKeys.league);if(!leagueId)return false;
  fsfflRestoringSession=true;
  try{
    let context=await fsfflOriginalApi('/api/connect/sleeper',{method:'POST',body:JSON.stringify({league_external_id:leagueId})});
    const teamId=localStorage.getItem(fsfflSessionKeys.team);
    if(teamId&&(context.teams||[]).some(team=>team.team_id===teamId)){
      context=await fsfflOriginalApi('/api/select-team',{method:'POST',body:JSON.stringify({team_id:teamId})});
    }
    state.context=context;state.teamView=null;state.valueCatalog=null;state.intelligence=null;applyContext();
    if(state.route==='trade_center'&&typeof loadTradeCenter==='function')await loadTradeCenter();
    return true;
  }catch(error){
    console.error('Unable to restore previous FSFFL session',error);return false;
  }finally{fsfflRestoringSession=false}
}

api=async function(path,options={}){
  try{
    const result=await fsfflOriginalApi(path,options);fsfflRememberSessionRequest(path,options,result);return result;
  }catch(error){
    const recoverable=error?.message==='No league is loaded'||error?.message==='No managed team is selected';
    const isRestoreCall=path==='/api/connect/sleeper'||path==='/api/select-team';
    if(recoverable&&!isRestoreCall&&await fsfflRestoreSession())return fsfflOriginalApi(path,options);
    throw error;
  }
};

setTimeout(async()=>{
  if(!state.context?.league_id){
    const restored=await fsfflRestoreSession();
    if(restored)console.info('Restored previous FSFFL league session after hosted restart.');
  }
},0);
