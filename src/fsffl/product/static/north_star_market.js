/* FSFFL NEXT Market North Star.
 * Presentation and workflow composition only.
 * Search, Value, Forecast, Decision, Simulation and Behavioral authority remain server-owned.
 */
(function(){
  "use strict";
  const VERSION="20260924-market-north-star1";
  const SAVE_KEY="fsffl.market.savedOpportunities";
  const WATCH_KEY="fsffl.market.watchedPlayers";
  const TABS=[
    ["for_you","For You","What might I care about?"],
    ["trade_finder","Trade Finder","Find realistic paths"],
    ["player_board","Player Board","Discover for yourself"],
    ["free_agents","Free Agents","Add without a trade"]
  ];
  const POSTURES=[
    ["default_calculated","Calculated"],
    ["win_now","Contend / Win now"],
    ["balanced","Balanced"],
    ["retool","Retool"],
    ["rebuild","Rebuild"]
  ];
  const market={
    tab:"for_you",
    readOnly:false,
    playerRows:[],
    playerLoading:false,
    playerLoaded:false,
    playerError:null,
    boardFilters:{query:"",position:"",age:"",owner:"",nfl:"",roster:"",role:""},
    boardSort:{key:"market_index",direction:"desc"},
    freeFilters:{query:"",position:"",nfl:""},
    freeSort:{key:"market_index",direction:"desc"},
    finderFilters:{position:"",team:"",status:"",deal:"",assets:"",sort:"search"},
    detailKey:"",
    pathKey:"",
    detailSection:"overview",
    waiverPlayer:null,
    waiverDrop:"",
    waiverResult:null,
    waiverBusy:false,
    waiverSeq:0
  };

  const esc=value=>String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  const finite=value=>typeof value==="number"&&Number.isFinite(value);
  const num=(value,digits=1)=>finite(value)?value.toLocaleString(undefined,{minimumFractionDigits:digits,maximumFractionDigits:digits}):"Unavailable";
  const integer=value=>finite(value)?Math.round(value).toLocaleString():"Unavailable";
  const age=value=>finite(value)?(Number.isInteger(value)?String(value):value.toFixed(1)):"Unavailable";
  const words=value=>String(value||"").replaceAll("_"," ");
  const unique=values=>[...new Set(values.filter(Boolean))];
  function storageSet(key){try{return new Set(JSON.parse(localStorage.getItem(key)||"[]"))}catch(_){return new Set()}}
  function persistSet(key,set){try{localStorage.setItem(key,JSON.stringify([...set]))}catch(_){}}

  const opp=()=>{try{return typeof fsfflOpportunityState!=="undefined"?fsfflOpportunityState:null}catch(_){return null}};
  const panel=()=>document.querySelector("#generic-screen .panel");
  const context=()=>{try{return state?.context||window.state?.context||{}}catch(_){return{}}};
  const onMarket=()=>{try{return state?.route==="opportunities"||window.state?.route==="opportunities"}catch(_){return false}};
  const tradeRows=()=>opp()?.payload?.trade_discovery?.candidates||[];
  const marketDiscovery=payload=>payload?.market_discovery||opp()?.payload?.market_discovery||{};
  const opportunities=payload=>marketDiscovery(payload)?.opportunities||[];
  const forYouOpportunities=payload=>marketDiscovery(payload)?.for_you||[];
  const candidatePaths=payload=>marketDiscovery(payload)?.candidate_paths||[];
  const pathById=(payload,id)=>candidatePaths(payload).find(path=>String(path.path_id)===String(id))||null;
  const opportunityById=(payload,id)=>opportunities(payload).find(item=>String(item.opportunity_id)===String(id))||null;
  const representative=path=>path?.representative_package||null;
  const rowKey=row=>String(row?.counterparty_team_id||"")+":"+(row?.send||[]).map(x=>x.asset_ref).join("+")+":"+(row?.receive||[]).map(x=>x.asset_ref).join("+");
  const refs=items=>(items||[]).map(x=>x.asset_ref).filter(Boolean);
  const labels=items=>(items||[]).map(x=>x.label||x.asset_ref).filter(Boolean);
  const selectedIntent=()=>window.fsfflMarketIntent?.selected?.()||{intent:"",value:""};
  const selectedPosture=()=>window.fsfflOpportunityPosture?.selectedPosture?.()||"default_calculated";
  function authority(row){
    const action=String(row?.action_authority||row?.recommendation_authority||"").toLowerCase();
    const shape=String(row?.decision_shape||row?.focal_decision_shape||"").toLowerCase();
    if(action==="actionable"||action==="recommended")return{key:"recommended",label:"Recommended",copy:"Existing Decision authority supports action."};
    if(!row?.bilateral_decision_evaluated)return{key:"needs",label:"Needs full evaluation",copy:"Search found a plausible structure; Decision has not evaluated this package."};
    if(shape.includes("support")||shape.includes("counter")||shape.includes("review")||action==="market_test_only")return{key:"investigate",label:"Worth investigating",copy:"Governed Decision evidence supports deeper review without predicting acceptance."};
    return{key:"match",label:"Market match only",copy:"Search found a structural match without recommendation authority."};
  }
  function reason(row){
    if(row?.focal_position_strength_rank)return "Addresses "+esc(row.target_position||"a roster need")+" · current league position rank #"+esc(row.focal_position_strength_rank)+".";
    if(finite(row?.market_gap_ratio))return "Closest market match within the current governed Search neighborhood.";
    if((row?.send||[]).length>1)return "Consolidation path surfaced by the governed Search layer.";
    return authority(row).copy;
  }
  function ownerProfile(teamId){return(opp()?.behavior?.profiles||[]).find(x=>String(x.current_team_id)===String(teamId))||null}
  function ownerCoverage(teamId){
    const p=ownerProfile(teamId);
    if(!p)return"Owner history unavailable";
    const trades=Number(p.trade_count||0);
    return trades?trades+" observed completed trade"+(trades===1?"":"s"):(Number(p.event_count||0)+" observed events");
  }
  function packageMarkup(row){
    return "<div class='market-ns-package'><span><small>You give</small><strong>"+esc(labels(row?.send).join(" + ")||"Unavailable")+"</strong></span><i aria-hidden='true'>→</i><span><small>You get</small><strong>"+esc(labels(row?.receive).join(" + ")||row?.target_position||"Unavailable")+"</strong></span></div>";
  }
  function statusPill(row){const a=authority(row);return"<span class='market-ns-status "+a.key+"'>"+esc(a.label)+"</span>"}
  function tabNav(){
    return "<nav class='market-ns-tabs' role='tablist' aria-label='Market views'>"+TABS.map(([key,label,question])=>"<button type='button' data-market-tab='"+key+"' class='"+(market.tab===key?"active":"")+"' aria-selected='"+(market.tab===key?"true":"false")+"'><strong>"+label+"</strong><small>"+question+"</small></button>").join("")+"</nav>";
  }
  function shell(payload=null){
    const host=panel();if(!host)return;
    host.classList.add("market-ns-v2");
    host.innerHTML="<header class='market-ns-head'><div><p class='eyebrow'>Market</p><h1>Find something worth doing.</h1><p>FSFFL can surface relevant opportunities, or you can explore the league on your own terms.</p></div><span class='status-chip'>"+(market.readOnly?"Read-only discovery":"Governed discovery")+"</span></header>"+tabNav()+"<div id='market-ns-body'></div><details class='market-ns-authority'><summary>Authority & evidence</summary><p>Search discovers candidate structures. Trade Center owns bilateral Decision, package consequences and exact Simulation. Broad Market and FSFFL Intrinsic remain separate. Missing evidence stays unavailable; acceptance probability is not estimated.</p></details>";
    wireTabs();
    renderBody(payload||opp()?.payload||null);
  }
  function wireTabs(){
    panel()?.querySelectorAll("[data-market-tab]").forEach(button=>button.addEventListener("click",()=>openTab(button.dataset.marketTab)));
  }
  function consumeMarketDeepLink(){
    const pending=window.fsfflConsumeDeepLinkIntent?.("opportunities");
    if(!pending?.marketTab)return null;
    if(TABS.some(row=>row[0]===pending.marketTab))market.tab=pending.marketTab;
    if(pending.marketIntent&&window.fsfflMarketIntent?.set)window.fsfflMarketIntent.set(pending.marketIntent,pending.marketValue||"");
    return pending;
  }
  function openTab(key){
    if(!TABS.some(row=>row[0]===key))return;
    market.tab=key;market.detailKey="";market.pathKey="";market.detailSection="overview";
    if((key==="for_you"||key==="trade_finder")&&opp()?.payload?.status!=="ready"){
      market.readOnly=false;
      shell();
      const body=document.querySelector("#market-ns-body");if(body)body.innerHTML=loading("Loading governed Search","Market will become useful before deep Decision or exact Simulation work runs.");
      if(typeof loadOpportunityWorkspace==="function")void loadOpportunityWorkspace({showLoading:false});
      return;
    }
    shell();
  }
  function loading(title,copy){return"<section class='market-ns-empty'><i></i><strong>"+esc(title)+"</strong><span>"+esc(copy)+"</span></section>"}
  function unavailable(title,copy){return"<section class='market-ns-empty'><strong>"+esc(title)+"</strong><span>"+esc(copy)+"</span></section>"}
  function renderBody(payload){
    const body=document.querySelector("#market-ns-body");if(!body)return;
    if(market.tab==="for_you")return renderForYou(body,payload);
    if(market.tab==="trade_finder")return renderTradeFinder(body,payload);
    if(market.tab==="player_board")return renderPlayerBoard(body);
    if(market.tab==="free_agents")return renderFreeAgents(body);
  }

  function opportunityTitle(item,payload){
    const paths=(item?.representative_path_ids||[]).map(id=>pathById(payload,id)).filter(Boolean);
    const targets=unique(paths.map(path=>labels(representative(path)?.receive).join(" + ")).filter(Boolean));
    if(item?.objective_family==="upgrade_position"&&item?.need_dimension)return "Upgrade "+item.need_dimension+" starter quality";
    if(targets.length===1)return "Acquire "+targets[0];
    return item?.need_dimension&&item.need_dimension!=="UNKNOWN" ? item.need_dimension+" market opportunity" : "Strategic market opportunity";
  }
  function opportunityStatus(item){
    const value=String(item?.attention_status||"");
    if(value==="worth_attention")return{key:"investigate",label:"Worth attention",copy:"At least one path survived governed economic and bilateral screening."};
    if(value==="explorable")return{key:"needs",label:"Explorable",copy:"Strategically relevant, but not yet strong enough for For You."};
    if(value==="market_match_only")return{key:"match",label:"Market match only",copy:"Search found structures without enough governed support for scarce attention."};
    return{key:"match",label:"Suppressed",copy:"This family does not qualify for the attention frontier."};
  }
  function opportunityPill(item){const a=opportunityStatus(item);return"<span class='market-ns-status "+a.key+"'>"+esc(a.label)+"</span>"}
  function opportunityCard(item,payload){
    const a=opportunityStatus(item),paths=(item?.representative_path_ids||[]).map(id=>pathById(payload,id)).filter(Boolean),saved=storageSet(SAVE_KEY).has(String(item.opportunity_id));
    const targets=unique(paths.map(path=>labels(representative(path)?.receive).join(" + ")).filter(Boolean)).slice(0,3);
    const why=(item?.why_now||[])[0]||"A governed strategic path survived preliminary screening.";
    const risk=(item?.top_risks||[])[0]||"Exact competitive impact remains a Trade Center decision.";
    return"<article class='market-ns-opportunity "+a.key+"'><button type='button' data-market-open='"+esc(item.opportunity_id)+"'><span class='market-ns-orb'>↗</span><div><div class='market-ns-card-top'><small>"+esc(item.need_dimension||"Opportunity")+(saved?" · Saved":"")+"</small>"+opportunityPill(item)+"</div><h3>"+esc(opportunityTitle(item,payload))+"</h3><p>"+esc(why)+"</p><div class='market-ns-opportunity-evidence'><span><small>Candidate paths</small><strong>"+esc(paths.length)+" preliminarily screened</strong></span><span><small>Example targets</small><strong>"+esc(targets.join(" · ")||"See paths")+"</strong></span><span><small>Primary risk</small><strong>"+esc(risk)+"</strong></span></div><span class='market-ns-card-cta'>Open opportunity →</span></div></button></article>";
  }
  function renderForYou(body,payload){
    if(market.pathKey)return renderCandidatePathDetail(body,payload);
    if(market.detailKey)return renderOpportunityDetail(body,payload);
    if(!payload||payload.status!=="ready"){body.innerHTML=loading("Preparing your Market","For You waits for governed strategic, economic and bilateral evidence; it does not promote raw Search rows.");return}
    const readiness=payload?.surface_readiness?.for_you||{},rows=forYouOpportunities(payload);
    if(readiness.status==="blocked"){
      body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>For You</p><h2>Your best paths right now.</h2><p>Automatic opportunities remain gated until the required current team-utility and Value evidence is ready.</p></div></section>"+unavailable("For You is not ready yet","Trade Finder can still support explicit intent when its required evidence is available.");
      return;
    }
    body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>For You</p><h2>Your best paths right now.</h2><p>Distinct strategic opportunities that earned attention before exact Simulation.</p></div><small>"+rows.length+" worth-attention opportunit"+(rows.length===1?"y":"ies")+"</small></section><div class='market-ns-opportunity-list'>"+(rows.length?rows.map(item=>opportunityCard(item,payload)).join(""):unavailable("Nothing has earned For You space","Trade Finder and Player Board remain available without lowering the evidence bar."))+"</div>";
    body.querySelectorAll("[data-market-open]").forEach(button=>button.addEventListener("click",()=>{market.detailKey=button.dataset.marketOpen;market.pathKey="";market.detailSection="overview";renderBody(payload)}));
  }
  function pathsForOpportunity(item,payload){
    return (item?.representative_path_ids||[]).map(id=>pathById(payload,id)).filter(Boolean);
  }
  function renderOpportunityDetail(body,payload){
    const item=opportunityById(payload,market.detailKey);
    if(!item){market.detailKey="";return renderForYou(body,payload)}
    const paths=pathsForOpportunity(item,payload),section=market.detailSection,why=item.why_now||[],risks=item.top_risks||[];
    const overview="<div class='market-ns-detail-grid'><article><small>Why this exists</small><strong>"+esc(why[0]||"Governed strategic evidence")+"</strong><span>"+esc(why[1]||"Opportunity family established before package selection.")+"</span></article><article><small>Attention status</small><strong>"+esc(opportunityStatus(item).label)+"</strong><span>"+esc(opportunityStatus(item).copy)+"</span></article><article><small>Preliminary economics</small><strong>"+esc(words(item.preliminary_economic_band))+"</strong><span>Decision-owned screening; no synthetic opportunity score.</span></article><article><small>Bilateral plausibility</small><strong>"+esc(words(item.bilateral_plausibility))+"</strong><span>Not an acceptance probability.</span></article></div>";
    const pathMarkup="<div class='market-ns-paths'>"+paths.map(path=>{const row=representative(path);return"<article><div class='market-ns-path-heading'><div><small>"+esc(row?.counterparty_name||"Counterparty")+"</small><strong>"+esc(labels(row?.receive).join(" + ")||item.need_dimension)+"</strong></div><span>"+esc(words(path.bilateral_plausibility))+"</span></div><p>"+esc((path.risks||[])[0]||"Preliminary screen complete; exact competitive impact remains downstream.")+"</p><button type='button' class='secondary-button' data-market-path='"+esc(path.path_id)+"'>Open candidate path</button></article>"}).join("")+"</div>";
    const fit="<div class='market-ns-detail-grid'><article><small>Strategic need</small><strong>"+esc(item.need_dimension||"Unavailable")+"</strong></article><article><small>Target family</small><strong>"+esc(words(item.target_family||"Unavailable"))+"</strong></article><article><small>Path count</small><strong>"+esc(paths.length)+" screened</strong><span>"+esc(item.alternate_path_count||0)+" additional path(s) remain outside the first view.</span></article><article><small>Exact season impact</small><strong>Trade Center</strong><span>Simulation is not run merely to preview this Opportunity.</span></article></div>";
    body.innerHTML="<section class='market-ns-detail'><div class='market-ns-detail-top'><button type='button' class='text-button' data-market-back>‹ Back</button>"+opportunityPill(item)+"</div><div class='market-ns-detail-hero'><div><p class='eyebrow'>Opportunity Detail</p><h2>"+esc(opportunityTitle(item,payload))+"</h2><p class='market-ns-detail-copy'>Why first. Packages second. Exact transaction decisions remain downstream.</p></div><div class='market-ns-detail-actions'><button type='button' class='secondary-button' data-market-save>"+(storageSet(SAVE_KEY).has(String(item.opportunity_id))?"Saved ✓":"Save opportunity")+"</button></div></div><nav class='market-ns-detail-tabs'><button data-detail-section='overview' class='"+(section==="overview"?"active":"")+"'>Overview</button><button data-detail-section='paths' class='"+(section==="paths"?"active":"")+"'>Candidate Paths</button><button data-detail-section='fit' class='"+(section==="fit"?"active":"")+"'>Fit & Risk</button></nav>"+(section==="paths"?pathMarkup:section==="fit"?fit:overview)+(risks.length?"<div class='market-ns-risk-strip'><small>Top risk</small><strong>"+esc(risks[0])+"</strong></div>":"")+"</section>";
    body.querySelector("[data-market-back]")?.addEventListener("click",()=>{market.detailKey="";market.pathKey="";renderBody(payload)});
    body.querySelectorAll("[data-detail-section]").forEach(button=>button.addEventListener("click",()=>{market.detailSection=button.dataset.detailSection;renderOpportunityDetail(body,payload)}));
    body.querySelectorAll("[data-market-path]").forEach(button=>button.addEventListener("click",()=>{market.pathKey=button.dataset.marketPath;renderCandidatePathDetail(body,payload)}));
    body.querySelector("[data-market-save]")?.addEventListener("click",()=>{const set=storageSet(SAVE_KEY),key=String(item.opportunity_id);set.has(key)?set.delete(key):set.add(key);persistSet(SAVE_KEY,set);renderOpportunityDetail(body,payload)});
  }
  function renderCandidatePathDetail(body,payload){
    const path=pathById(payload,market.pathKey),item=opportunityById(payload,path?.opportunity_id),row=representative(path);
    if(!path||!item||!row){market.pathKey="";return renderOpportunityDetail(body,payload)}
    const alt=(path.alternate_packages||[])[0]||null,owner=path.owner_context_status==="observed_history"?"Observed history attached":"Owner history unavailable",risks=path.risks||[];
    body.innerHTML="<section class='market-ns-detail market-ns-path-detail'><div class='market-ns-detail-top'><button type='button' class='text-button' data-path-back>‹ Opportunity</button><span class='market-ns-status investigate'>Prelim screened</span></div><div class='market-ns-detail-hero'><div><p class='eyebrow'>Candidate Path Detail</p><h2>"+esc(labels(row.receive).join(" + ")||item.need_dimension)+" via "+esc(row.counterparty_name||"counterparty")+"</h2><p class='market-ns-detail-copy'>This route survived preliminary screening. It is not a final trade verdict.</p></div><div class='market-ns-detail-actions'><button type='button' class='primary-button' data-market-trade>Evaluate in Trade Center</button></div></div>"+packageMarkup(row)+"<div class='market-ns-detail-grid'><article><small>Strategic fit</small><strong>"+esc(item.need_dimension)+" · "+esc(item.strategic_relevance)+"</strong></article><article><small>Economics</small><strong>"+esc(words(path.economic_screen))+"</strong></article><article><small>Bilateral rationale</small><strong>"+esc(words(path.bilateral_plausibility))+"</strong><span>"+esc(words(path.negotiation_feasibility_shape||"unavailable"))+"</span></article><article><small>Owner context</small><strong>"+esc(owner)+"</strong><span>Descriptive only; no acceptance probability.</span></article></div>"+(risks.length?"<div class='market-ns-risk-strip'><small>Important sacrifice / risk</small><strong>"+esc(risks[0])+"</strong></div>":"")+(alt?"<div class='market-ns-alt-package'><small>Materially distinct alternative package</small>"+packageMarkup(alt)+"</div>":"")+"<p class='market-ns-deep-note'>Exact season impact has not been run for discovery. Trade Center owns full bilateral Decision and targeted 50,000-run Simulation.</p></section>";
    body.querySelector("[data-path-back]")?.addEventListener("click",()=>{market.pathKey="";renderOpportunityDetail(body,payload)});
    body.querySelector("[data-market-trade]")?.addEventListener("click",()=>window.fsfflOpenOpportunityInTradeCenter?.(row));
  }

  function currentCalculatedState(payload){
    return payload?.search_posture?.calculated_competitive_state||payload?.search_posture?.calculated_state||"unknown";
  }
  function finderMode(){
    const intent=selectedIntent().intent;
    return intent==="target"?"target":intent==="shop"?"shop":intent==="position"?"position":intent==="owner"?"owner":"improve";
  }
  function targetOptions(mode){
    const teamId=context().team_id;
    if(!market.playerLoaded)return[];
    if(mode==="shop")return market.playerRows.filter(row=>String(row.owner_team_id||"")===String(teamId));
    if(mode==="target")return market.playerRows.filter(row=>row.roster_status==="rostered"&&String(row.owner_team_id||"")!==String(teamId));
    return[];
  }
  function ownerOptions(){return(context().teams||[]).filter(team=>String(team.team_id)!==String(context().team_id)).map(team=>[team.team_id,team.display_name]).sort((a,b)=>String(a[1]).localeCompare(String(b[1])))}
  function intentValueControl(mode){
    const current=selectedIntent().value||"";
    if(mode==="position")return"<label><span>Position</span><select data-finder-intent-value><option value=''>Choose position</option>"+["QB","RB","WR","TE"].map(v=>"<option value='"+v+"'"+(current===v?" selected":"")+">"+v+"</option>").join("")+"</select></label>";
    if(mode==="owner")return"<label><span>Owner / team</span><select data-finder-intent-value><option value=''>Choose owner</option>"+ownerOptions().map(([id,name])=>"<option value='"+esc(id)+"'"+(String(current)===String(id)?" selected":"")+">"+esc(name)+"</option>").join("")+"</select></label>";
    if(mode==="target"||mode==="shop"){
      const rows=targetOptions(mode);
      return"<label><span>"+(mode==="target"?"Target player":"Player to shop")+"</span><select data-finder-intent-value><option value=''>Choose player</option>"+rows.map(row=>"<option value='player:"+esc(row.player_id)+"'"+(current==="player:"+row.player_id?" selected":"")+">"+esc(row.full_name)+" · "+esc(row.owner_team_name||row.roster_status)+"</option>").join("")+"</select></label>";
    }
    return"";
  }
  function pathAuthority(path){
    if(path?.bilateral_plausibility==="counterparty_dominated"||path?.bilateral_plausibility==="focal_dominated")return{key:"match",label:"High friction"};
    if(path?.deep_evaluation_status!=="prelim_screened")return{key:"needs",label:"Needs preliminary screen"};
    if(path?.bilateral_plausibility==="bilateral_supported")return{key:"investigate",label:"Prelim plausible"};
    if(path?.bilateral_plausibility==="bilateral_friction")return{key:"needs",label:"Bilateral friction"};
    return{key:"match",label:"Market match only"};
  }
  function finderPaths(payload){
    const f=market.finderFilters;let paths=[...candidatePaths(payload)];
    const row=path=>representative(path)||{};
    if(f.position)paths=paths.filter(path=>String(row(path).target_position||"")===f.position);
    if(f.team)paths=paths.filter(path=>String(path.counterparty_team_id||"")===f.team);
    if(f.status)paths=paths.filter(path=>pathAuthority(path).key===f.status);
    if(f.deal==="one")paths=paths.filter(path=>(row(path).send||[]).length===1);
    if(f.deal==="multi")paths=paths.filter(path=>(row(path).send||[]).length>1);
    if(f.assets==="players")paths=paths.filter(path=>[...(row(path).send||[]),...(row(path).receive||[])].every(item=>item.asset_kind==="player"));
    if(f.assets==="picks")paths=paths.filter(path=>[...(row(path).send||[]),...(row(path).receive||[])].some(item=>item.asset_kind==="pick"));
    if(f.sort==="closest")paths.sort((a,b)=>(row(a).market_gap_ratio??Infinity)-(row(b).market_gap_ratio??Infinity)||(row(a).search_distance??Infinity)-(row(b).search_distance??Infinity));
    if(f.sort==="need")paths.sort((a,b)=>(row(a).focal_position_strength_index??Infinity)-(row(b).focal_position_strength_index??Infinity));
    if(f.sort==="authority")paths.sort((a,b)=>({investigate:0,needs:1,match:2}[pathAuthority(a).key]-({investigate:0,needs:1,match:2}[pathAuthority(b).key)));
    return paths;
  }
  function renderTradeFinder(body,payload){
    if(market.pathKey)return renderCandidatePathDetail(body,payload);
    if(!payload||payload.status!=="ready"){body.innerHTML=loading("Loading Trade Finder","Server-owned Search is preparing the current candidate workspace.");return}
    if(!market.playerLoaded&&!market.playerLoading)void ensurePlayerUniverse();
    const mode=finderMode(),f=market.finderFilters,paths=finderPaths(payload),calc=words(currentCalculatedState(payload));
    const primary="<div class='market-ns-finder-primary'><label><span>Strategic lens</span><select data-finder-posture>"+POSTURES.map(([key,label])=>"<option value='"+key+"'"+(selectedPosture()===key?" selected":"")+">"+label+"</option>").join("")+"</select></label>"+intentValueControl(mode)+"</div>";
    const advanced="<details class='market-ns-advanced'><summary>Advanced filters</summary><div class='market-ns-finder-controls'><label><span>Position</span><select data-finder-filter='position'><option value=''>All positions</option>"+["QB","RB","WR","TE"].map(v=>"<option value='"+v+"'"+(f.position===v?" selected":"")+">"+v+"</option>").join("")+"</select></label><label><span>Owner / team</span><select data-finder-filter='team'><option value=''>All owners</option>"+ownerOptions().map(([id,name])=>"<option value='"+esc(id)+"'"+(String(f.team)===String(id)?" selected":"")+">"+esc(name)+"</option>").join("")+"</select></label><label><span>Package shape</span><select data-finder-filter='deal'><option value=''>Any</option><option value='one'"+(f.deal==="one"?" selected":"")+">1-for-1</option><option value='multi'"+(f.deal==="multi"?" selected":"")+">Consolidation</option></select></label><label><span>Assets</span><select data-finder-filter='assets'><option value=''>Players / picks</option><option value='players'"+(f.assets==="players"?" selected":"")+">Players only</option><option value='picks'"+(f.assets==="picks"?" selected":"")+">Includes picks</option></select></label><label><span>Status</span><select data-finder-filter='status'><option value=''>Any status</option><option value='investigate'"+(f.status==="investigate"?" selected":"")+">Prelim plausible</option><option value='needs'"+(f.status==="needs"?" selected":"")+">Needs review</option><option value='match'"+(f.status==="match"?" selected":"")+">Market match / friction</option></select></label><label><span>Sort</span><select data-finder-filter='sort'><option value='search'"+(f.sort==="search"?" selected":"")+">Current Search order</option><option value='closest'"+(f.sort==="closest"?" selected":"")+">Closest market match</option><option value='need'"+(f.sort==="need"?" selected":"")+">Biggest roster need addressed</option><option value='authority'"+(f.sort==="authority"?" selected":"")+">Strongest preliminary evidence</option></select></label><button type='button' class='text-button market-ns-reset' data-finder-reset>Reset filters</button></div></details>";
    body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>Trade Finder</p><h2>What are you trying to do?</h2><p>Intent first. Calculated competitive state remains "+esc(calc)+". Packages stay subordinate to Candidate Paths.</p></div><small>"+paths.length+" candidate path"+(paths.length===1?"":"s")+"</small></section><div class='market-ns-finder'><div class='market-ns-mode-grid'>"+[["improve","Improve my team"],["target","Target a player"],["shop","Shop a player"],["position","Target a position"],["owner","Explore an owner / team"]].map(([key,label])=>"<button type='button' data-finder-mode='"+key+"' class='"+(mode===key?"active":"")+"'>"+label+"</button>").join("")+"</div>"+primary+advanced+"</div><div class='market-ns-result-list'>"+(paths.length?paths.slice(0,80).map(path=>{const r=representative(path),a=pathAuthority(path);return"<article><button type='button' data-finder-open='"+esc(path.path_id)+"'><div><small>"+esc(r.target_position||"Trade path")+" · "+esc(r.counterparty_name||"Owner unavailable")+"</small><strong>"+esc(labels(r.receive).join(" + ")||"Target unavailable")+"</strong><span>"+esc(words(path.bilateral_plausibility))+" · "+esc(words(path.economic_screen))+"</span></div><span class='market-ns-status "+a.key+"'>"+esc(a.label)+"</span><b>"+esc((path.alternate_packages||[]).length+1)+" package variant"+(((path.alternate_packages||[]).length+1)===1?"":"s")+"</b></button></article>"}).join(""):unavailable("No paths match this view","Change the Search intent, strategic lens, or advanced filters."))+"</div>";
    wireFinder(body,payload,mode);
  }
  function wireFinder(body,payload,mode){
    body.querySelectorAll("[data-finder-mode]").forEach(button=>button.addEventListener("click",()=>{
      const next=button.dataset.finderMode;
      market.pathKey="";
      if(next==="improve")window.fsfflMarketIntent?.clear?.();else window.fsfflMarketIntent?.set?.(next,"");
      renderBody(payload);
    }));
    body.querySelector("[data-finder-intent-value]")?.addEventListener("change",event=>{if(mode!=="improve")window.fsfflMarketIntent?.set?.(mode,event.target.value||"")});
    body.querySelector("[data-finder-posture]")?.addEventListener("change",event=>{window.fsfflOpportunityPosture?.setPosture?.(event.target.value);window.fsfflMarketFocus?.refresh?.()});
    body.querySelectorAll("[data-finder-filter]").forEach(select=>select.addEventListener("change",()=>{market.finderFilters[select.dataset.finderFilter]=select.value;renderBody(payload)}));
    body.querySelector("[data-finder-reset]")?.addEventListener("click",()=>{market.finderFilters={position:"",team:"",status:"",deal:"",assets:"",sort:"search"};renderBody(payload)});
    body.querySelectorAll("[data-finder-open]").forEach(button=>button.addEventListener("click",()=>{const path=pathById(payload,button.dataset.finderOpen);market.pathKey=button.dataset.finderOpen;market.detailKey=path?.opportunity_id||"";renderCandidatePathDetail(body,payload)}));
  }

  function projectionFromPlayer(player){
    const forecasts=player?.forecasts||[];
    const obs=forecasts.find(item=>item.metric==="fantasy_points"&&item.horizon==="season")||forecasts.find(item=>item.metric==="fantasy_points");
    if(finite(obs?.distribution?.mean))return obs.distribution.mean;
    if(finite(player?.season_fantasy_points_projection))return player.season_fantasy_points_projection;
    return null;
  }
  function deriveRanks(rows){
    const ranked=[...rows].filter(row=>finite(row.market_index)).sort((a,b)=>b.market_index-a.market_index||String(a.full_name).localeCompare(String(b.full_name)));
    ranked.forEach((row,index)=>row.overall_rank=index+1);
    const positions=unique(ranked.map(row=>row.position));
    positions.forEach(position=>ranked.filter(row=>row.position===position).forEach((row,index)=>row.position_rank=index+1));
  }
  async function ensurePlayerUniverse(){
    if(market.playerLoaded||market.playerLoading)return;
    market.playerLoading=true;market.playerError=null;renderBody(opp()?.payload||null);
    try{
      const results=await Promise.all([api("/api/league/value-lenses?universe=all"),api("/api/league/team-views")]);
      const lenses=results[0]||{},league=results[1]||{};
      if(lenses.status==="loading")throw new Error(lenses.message||"Governed Value lenses are still preparing.");
      const analytics=new Map();
      (league.team_views||[]).forEach(team=>(team.players||[]).forEach(player=>analytics.set(String(player.player_id),{...player,analytics_team_id:team.team_id,analytics_team_name:team.display_name})));
      market.playerRows=(lenses.players||[]).map(row=>{
        const a=analytics.get(String(row.player_id)),projection=a?projectionFromPlayer(a):null;
        return{
          player_id:String(row.player_id),full_name:row.full_name,position:row.position,nfl_team:row.nfl_team||a?.nfl_team||null,age:row.age_years,
          owner_team_id:row.owner_team_id||null,owner_team_name:row.owner_team_name||null,roster_status:row.roster_status|| (row.owner_team_id?"rostered":"available"),
          projected_starter:a?.projected_starter===true,role:a?(a.projected_starter?"starter":"reserve"):"unavailable",
          projection,ppg:finite(projection)?projection/17:null,market_index:row.broad_market_value_index,intrinsic_index:row.intrinsic_value_index,
          market_percentile:row.broad_market_percentile,intrinsic_percentile:row.intrinsic_percentile,overall_rank:null,position_rank:null
        };
      });
      deriveRanks(market.playerRows);market.playerLoaded=true;
    }catch(error){market.playerError=error?.message||String(error)}finally{market.playerLoading=false;renderBody(opp()?.payload||null)}
  }
  function optionList(values,current){return unique(values).sort().map(value=>"<option value='"+esc(value)+"'"+(String(current)===String(value)?" selected":"")+">"+esc(value)+"</option>").join("")}
  function boardRows(){
    const f=market.boardFilters,query=f.query.trim().toLowerCase();let rows=market.playerRows.filter(row=>{
      if(query&&!((row.full_name+" "+(row.owner_team_name||"")+" "+(row.nfl_team||"")+" "+row.position).toLowerCase().includes(query)))return false;
      if(f.position&&row.position!==f.position)return false;
      if(f.owner&&String(row.owner_team_id||"")!==f.owner)return false;
      if(f.nfl&&String(row.nfl_team||"")!==f.nfl)return false;
      if(f.roster==="managed"&&String(row.owner_team_id||"")!==String(context().team_id))return false;
      if(f.roster==="rostered"&&row.roster_status!=="rostered")return false;
      if(f.roster==="available"&&row.roster_status!=="available")return false;
      if(f.role&&row.role!==f.role)return false;
      if(f.age==="u24"&&!(finite(row.age)&&row.age<24))return false;
      if(f.age==="24-26"&&!(finite(row.age)&&row.age>=24&&row.age<=26.99))return false;
      if(f.age==="27-29"&&!(finite(row.age)&&row.age>=27&&row.age<=29.99))return false;
      if(f.age==="30p"&&!(finite(row.age)&&row.age>=30))return false;
      return true;
    });
    const sort=market.boardSort,key=sort.key,dir=sort.direction==="asc"?1:-1;
    rows.sort((a,b)=>{const av=a[key],bv=b[key];if(av==null&&bv==null)return String(a.full_name).localeCompare(String(b.full_name));if(av==null)return 1;if(bv==null)return-1;if(typeof av==="number"&&typeof bv==="number")return(av-bv)*dir;return String(av).localeCompare(String(bv))*dir});
    return rows;
  }
  function playerActionContext(row){
    const managed=String(row.owner_team_id||"")===String(context().team_id);
    return"data-pi-owner-team-id='"+esc(row.owner_team_id||"")+"' data-pi-owner-team-name='"+esc(row.owner_team_name||"")+"' data-pi-roster-status='"+esc(row.roster_status)+"' data-pi-managed='"+(managed?"true":"false")+"'";
  }
  function playerRowMarkup(row){
    return"<tr><td class='market-ns-player-sticky'><button type='button' class='pi-player-link market-ns-player-link' data-player-intelligence-id='"+esc(row.player_id)+"' "+playerActionContext(row)+"><strong>"+esc(row.full_name)+"</strong><small>"+esc(row.position)+" · "+esc(row.nfl_team||"NFL team unavailable")+"</small></button></td><td>"+age(row.age)+"</td><td>"+esc(row.owner_team_name||(row.roster_status==="available"?"Available":"Unavailable"))+"</td><td>"+integer(row.market_index)+"</td><td>"+integer(row.intrinsic_index)+"</td><td>"+num(row.ppg,1)+"</td><td>"+num(row.projection,1)+"</td><td>"+(row.overall_rank?"#"+row.overall_rank:"Unavailable")+"</td><td>"+(row.position_rank?"#"+row.position_rank+" "+esc(row.position):"Unavailable")+"</td></tr>";
  }
  function renderPlayerBoard(body){
    if(!market.playerLoaded){body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>Player Board</p><h2>Explore the whole player market.</h2><p>Read-only league discovery with separate governed Value lenses.</p></div></section>"+(market.playerError?unavailable("Player Board unavailable",market.playerError):loading("Loading Player Board","Reading current State, Forecast team views and governed Value lenses. No Search or Decision work is launched."));if(!market.playerLoading&&!market.playerError)void ensurePlayerUniverse();return}
    const f=market.boardFilters,rows=boardRows(),positions=market.playerRows.map(x=>x.position),owners=market.playerRows.filter(x=>x.owner_team_id).map(x=>x.owner_team_name),nfl=market.playerRows.map(x=>x.nfl_team);
    body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>Player Board</p><h2>Let me discover for myself.</h2><p>Overall and position ranks are presentation ordering only. Broad Market and FSFFL Intrinsic remain separate.</p></div><div class='market-ns-section-actions'><small>"+rows.length+" players</small><button type='button' class='text-button' data-market-disagreement>Explore Value disagreement</button></div></section><div class='market-ns-board-controls'><input type='search' data-board-filter='query' value='"+esc(f.query)+"' placeholder='Search player, owner, NFL team or keyword'><select data-board-filter='position'><option value=''>All positions</option>"+optionList(positions,f.position)+"</select><select data-board-filter='age'><option value=''>All ages</option><option value='u24'"+(f.age==="u24"?" selected":"")+">Under 24</option><option value='24-26'"+(f.age==="24-26"?" selected":"")+">24-26</option><option value='27-29'"+(f.age==="27-29"?" selected":"")+">27-29</option><option value='30p'"+(f.age==="30p"?" selected":"")+">30+</option></select><select data-board-filter='owner'><option value=''>All fantasy teams</option>"+unique(market.playerRows.filter(x=>x.owner_team_id).map(x=>[x.owner_team_id,x.owner_team_name])).map(()=> "").join("")+"</select><select data-board-filter='nfl'><option value=''>All NFL teams</option>"+optionList(nfl,f.nfl)+"</select><select data-board-filter='roster'><option value=''>All roster statuses</option><option value='managed'"+(f.roster==="managed"?" selected":"")+">My roster</option><option value='rostered'"+(f.roster==="rostered"?" selected":"")+">Rostered</option><option value='available'"+(f.roster==="available"?" selected":"")+">Available</option></select><select data-board-filter='role'><option value=''>All projected roles</option><option value='starter'"+(f.role==="starter"?" selected":"")+">Projected starters</option><option value='reserve'"+(f.role==="reserve"?" selected":"")+">Projected reserves</option></select><select data-board-sort><option value='market_index'>Broad Market</option><option value='intrinsic_index'>FSFFL Intrinsic</option><option value='age'>Age</option><option value='ppg'>PPG</option><option value='projection'>17-game projection</option><option value='overall_rank'>Overall rank</option><option value='position_rank'>Position rank</option><option value='full_name'>Player name</option></select></div><div class='market-ns-board-meta'><span>Broad Market and FSFFL Intrinsic are shown side by side and never blended.</span><span>League Market Value: unavailable · Team Utility: not part of this board.</span></div><div class='market-ns-player-table'><table><thead><tr><th>Player</th><th>Age</th><th>Fantasy team</th><th>Broad Market</th><th>FSFFL Intrinsic</th><th>PPG</th><th>17-game projection</th><th>Overall rank</th><th>Position rank</th></tr></thead><tbody>"+(rows.length?rows.map(playerRowMarkup).join(""):"<tr><td colspan='9'>No players match these filters.</td></tr>")+"</tbody></table></div>";
    const ownerSelect=body.querySelector("[data-board-filter='owner']");if(ownerSelect){ownerSelect.innerHTML="<option value=''>All fantasy teams</option>"+[...new Map(market.playerRows.filter(x=>x.owner_team_id).map(x=>[String(x.owner_team_id),x.owner_team_name])).entries()].sort((a,b)=>String(a[1]).localeCompare(String(b[1]))).map(([id,name])=>"<option value='"+esc(id)+"'"+(f.owner===id?" selected":"")+">"+esc(name)+"</option>").join("")}
    const sort=body.querySelector("[data-board-sort]");if(sort)sort.value=market.boardSort.key;
    body.querySelectorAll("[data-board-filter]").forEach(control=>control.addEventListener(control.tagName==="INPUT"?"input":"change",()=>{market.boardFilters[control.dataset.boardFilter]=control.value;renderPlayerBoard(body)}));
    sort?.addEventListener("change",()=>{market.boardSort={key:sort.value,direction:["age","full_name","overall_rank","position_rank"].includes(sort.value)?"asc":"desc"};renderPlayerBoard(body)});
  }

  function freeRows(){
    const f=market.freeFilters,query=f.query.trim().toLowerCase();let rows=market.playerRows.filter(row=>row.roster_status==="available");
    rows=rows.filter(row=>(!query||(row.full_name+" "+row.position+" "+(row.nfl_team||"")).toLowerCase().includes(query))&&(!f.position||row.position===f.position)&&(!f.nfl||row.nfl_team===f.nfl));
    const sort=market.freeSort,key=sort.key,dir=sort.direction==="asc"?1:-1;rows.sort((a,b)=>{const av=a[key],bv=b[key];if(av==null&&bv==null)return String(a.full_name).localeCompare(String(b.full_name));if(av==null)return 1;if(bv==null)return-1;if(typeof av==="number"&&typeof bv==="number")return(av-bv)*dir;return String(av).localeCompare(String(bv))*dir});return rows;
  }
  function waiverResultMarkup(result){
    if(!result)return"";if(result.error)return"<div class='market-ns-waiver-result'><strong>Evaluation unavailable</strong><span>"+esc(result.error)+"</span></div>";
    const delta=result.team_delta||{},competitive=delta.competitive||{},assessment=result.material_assessment||{};
    return"<div class='market-ns-waiver-result'><div><small>Governed disposition</small><strong>"+esc(words(assessment.disposition||"Unavailable"))+"</strong><span>Action authority: "+esc(words(result.action_authority||"Unavailable"))+"</span></div><div><small>Expected wins</small><strong>"+(finite(competitive.expected_wins)?(competitive.expected_wins>0?"+":"")+competitive.expected_wins.toFixed(2):"Unavailable")+"</strong></div><div><small>Playoff odds</small><strong>"+(finite(competitive.playoff_probability)?(competitive.playoff_probability>0?"+":"")+(competitive.playoff_probability*100).toFixed(1)+" pp":"Unavailable")+"</strong></div><div><small>Simulation</small><strong>"+(result.scenario_simulation_count?Number(result.scenario_simulation_count).toLocaleString():"Unavailable")+"</strong></div></div>";
  }
  function waiverEvaluator(){
    const add=market.waiverPlayer;if(!add)return"";
    const managed=market.playerRows.filter(row=>String(row.owner_team_id||"")===String(context().team_id)).sort((a,b)=>(a.projected_starter?1:0)-(b.projected_starter?1:0)||String(a.full_name).localeCompare(String(b.full_name)));
    return"<section class='market-ns-waiver'><div class='market-ns-detail-top'><div><p class='eyebrow'>Add / Drop Detail</p><h3>Add "+esc(add.full_name)+"</h3><p>Choose a drop candidate. The governed evaluator runs only when you ask.</p></div><button type='button' class='text-button' data-waiver-close>Close</button></div><label><span>Drop from your roster</span><select data-waiver-drop><option value=''>Use open roster slot</option>"+managed.map(row=>"<option value='"+esc(row.player_id)+"'"+(market.waiverDrop===row.player_id?" selected":"")+">"+esc(row.full_name)+" · "+esc(row.position)+" · "+esc(row.role)+"</option>").join("")+"</select></label><button type='button' class='primary-button' data-waiver-run "+(market.waiverBusy?"disabled":"")+">"+(market.waiverBusy?"Running governed evaluation…":"Evaluate add/drop")+"</button>"+waiverResultMarkup(market.waiverResult)+"</section>";
  }
  function renderFreeAgents(body){
    if(!market.playerLoaded){body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>Free Agents</p><h2>What can I add without a trade?</h2><p>Available-player discovery is immediate; add/drop evaluation is explicit.</p></div></section>"+(market.playerError?unavailable("Free Agents unavailable",market.playerError):loading("Loading available players","Reading current State, Forecast and separate Value lenses."));if(!market.playerLoading&&!market.playerError)void ensurePlayerUniverse();return}
    const f=market.freeFilters,rows=freeRows(),nfl=market.playerRows.filter(x=>x.roster_status==="available").map(x=>x.nfl_team);
    body.innerHTML="<section class='market-ns-section-head'><div><p class='eyebrow'>Free Agents</p><h2>Available players</h2><p>No waiver priority is invented. Missing Forecast or Value evidence stays unavailable.</p></div><small>"+rows.length+" available</small></section>"+waiverEvaluator()+"<div class='market-ns-free-controls'><input type='search' data-free-filter='query' value='"+esc(f.query)+"' placeholder='Search available player'><select data-free-filter='position'><option value=''>All positions</option>"+optionList(["QB","RB","WR","TE"],f.position)+"</select><select data-free-filter='nfl'><option value=''>All NFL teams</option>"+optionList(nfl,f.nfl)+"</select><select data-free-sort><option value='market_index'>Broad Market</option><option value='intrinsic_index'>FSFFL Intrinsic</option><option value='projection'>17-game projection</option><option value='ppg'>PPG</option><option value='age'>Age</option><option value='position_rank'>Position rank</option></select></div><div class='market-ns-free-list'>"+(rows.length?rows.map(row=>"<article><button type='button' class='market-ns-free-player pi-player-link' data-player-intelligence-id='"+esc(row.player_id)+"' "+playerActionContext(row)+"><span><strong>"+esc(row.full_name)+"</strong><small>"+esc(row.position)+" · "+esc(row.nfl_team||"NFL team unavailable")+" · age "+age(row.age)+"</small></span><span><small>PPG</small><b>"+num(row.ppg,1)+"</b></span><span><small>17-game</small><b>"+num(row.projection,1)+"</b></span><span><small>Broad Market</small><b>"+integer(row.market_index)+"</b></span><span><small>Intrinsic</small><b>"+integer(row.intrinsic_index)+"</b></span></button><button type='button' class='secondary-button' data-free-evaluate='"+esc(row.player_id)+"'>Evaluate add/drop</button></article>").join(""):unavailable("No available players match","Change the filters to broaden the list."))+"</div>";
    const sort=body.querySelector("[data-free-sort]");if(sort)sort.value=market.freeSort.key;
    body.querySelectorAll("[data-free-filter]").forEach(control=>control.addEventListener(control.tagName==="INPUT"?"input":"change",()=>{market.freeFilters[control.dataset.freeFilter]=control.value;renderFreeAgents(body)}));
    sort?.addEventListener("change",()=>{market.freeSort={key:sort.value,direction:["age","position_rank"].includes(sort.value)?"asc":"desc"};renderFreeAgents(body)});
    body.querySelectorAll("[data-free-evaluate]").forEach(button=>button.addEventListener("click",()=>{market.waiverPlayer=market.playerRows.find(row=>row.player_id===button.dataset.freeEvaluate)||null;market.waiverDrop="";market.waiverResult=null;renderFreeAgents(body);document.querySelector(".market-ns-waiver")?.scrollIntoView({behavior:"smooth",block:"nearest"})}));
    body.querySelector("[data-waiver-close]")?.addEventListener("click",()=>{market.waiverPlayer=null;market.waiverResult=null;renderFreeAgents(body)});
    body.querySelector("[data-waiver-drop]")?.addEventListener("change",event=>{market.waiverDrop=event.target.value||""});
    body.querySelector("[data-waiver-run]")?.addEventListener("click",runWaiver);
  }
  async function runWaiver(){
    if(!market.waiverPlayer||market.waiverBusy)return;const id=++market.waiverSeq,ctx=context(),stateId=ctx.state_id;
    market.waiverBusy=true;market.waiverResult=null;renderBody(opp()?.payload||null);
    try{
      const result=await api("/api/opportunities/waiver",{method:"POST",body:JSON.stringify({add_player_id:market.waiverPlayer.player_id,drop_player_id:market.waiverDrop||null})});
      if(id!==market.waiverSeq||context().state_id!==stateId)return;market.waiverResult=result;
    }catch(error){if(id===market.waiverSeq)market.waiverResult={error:error?.message||String(error)}}finally{if(id===market.waiverSeq){market.waiverBusy=false;renderBody(opp()?.payload||null)}}
  }

  function openOwner(teamId){
    if(!teamId)return;
    window.fsfflSetDeepLinkIntent?.({route:"behavioral_intelligence",ownerTeamId:String(teamId)});
    if(typeof setRoute==="function")setRoute("behavioral_intelligence");
  }
  function openTradeFinder(intent,value){
    window.fsfflSetDeepLinkIntent?.({route:"opportunities",marketTab:"trade_finder",marketIntent:intent||"",marketValue:value||""});
    if(typeof setRoute==="function")setRoute("opportunities");
  }
  function openFreeAgent(playerId){
    window.fsfflSetDeepLinkIntent?.({route:"opportunities",marketTab:"free_agents",playerId:String(playerId||"")});
    if(typeof setRoute==="function")setRoute("opportunities");
  }
  function bootReadOnly(tab){
    market.readOnly=true;market.tab=tab==="free_agents"?"free_agents":"player_board";market.detailKey="";
    const pending=consumeMarketDeepLink();
    shell(null);void ensurePlayerUniverse();
    if(pending?.playerId&&market.tab==="free_agents"){
      const timer=setInterval(()=>{if(market.playerLoaded){clearInterval(timer);const row=market.playerRows.find(x=>x.player_id===String(pending.playerId));if(row){market.waiverPlayer=row;renderBody(null)}}},50);setTimeout(()=>clearInterval(timer),5000)
    }
  }
  function renderNorthStar(payload){
    market.readOnly=false;
    const pending=consumeMarketDeepLink();
    if(!pending&&market.tab==="player_board"&&payload?.status==="ready"){}else if(!pending&&!TABS.some(row=>row[0]===market.tab))market.tab="for_you";
    shell(payload);
    const focus=payload?.trade_discovery?.focus||null,intent=selectedIntent();
    if(market.tab==="trade_finder"&&intent.intent&&(!focus||focus.intent!==intent.intent||String(focus.value||"")!==String(intent.value||""))){
      setTimeout(()=>window.fsfflMarketFocus?.refresh?.(),0);
    }
  }
  function reset(){
    market.playerRows=[];market.playerLoaded=false;market.playerLoading=false;market.playerError=null;market.detailKey="";market.pathKey="";market.waiverPlayer=null;market.waiverResult=null;market.waiverSeq+=1;
  }

  window.fsfflMarketNorthStarV2=true;
  window.renderFsfflMarketNorthStar=renderNorthStar;
  window.fsfflMarketNorthStar={version:VERSION,bootReadOnly,openTab,openTradeFinder,openFreeAgent,openOwner,render:renderNorthStar};
  window.addEventListener("fsffl:product-context-updated",reset);
  window.addEventListener("fsffl:market-focus-applied",()=>{if(onMarket())shell(opp()?.payload||null)});
})();