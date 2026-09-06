/* NEXT-8 product presentation bridge.
 * Presentation only: consumes authoritative API/runtime output and does not
 * calculate Value, utility, simulation outcomes, trade grades, or acceptance.
 */

function fsfflCardinalScoreFor(assetId){
  return (state.valueCatalog?.fsffl_cardinal_values||[]).find(item=>item.asset_id===assetId)||null;
}

function cardinalValueDetails(item){
  if(!item)return'';
  const source=item.evidence_source_id||'governed NEXT-3 evidence';
  const scale=item.scale?.unit_label||'FSFFL Value points';
  return `Authoritative NEXT-3 FSFFL Cardinal Market Score.\nModel: ${item.model_version}\nAuthority: ${item.authority_status}\nEvidence: ${source}\nScale: ${scale}`;
}

provisionalScoreFor=fsfflCardinalScoreFor;
provisionalValueCell=function(assetId){
  const item=fsfflCardinalScoreFor(assetId);
  if(!item||typeof item.score!=='number')return'—';
  return `<span title="${escapeHtml(cardinalValueDetails(item))}"><strong>${fmtFsfflValue(item.score)}</strong><br><small>Authoritative market-cardinal value</small></span>`;
};

tradeValueMarkup=function(option){
  const item=tradeAssetScore(option);
  if(!item||typeof item.score!=='number')return'<span class="asset-kind">FSFFL Value —</span>';
  return `<span class="asset-kind" title="${escapeHtml(cardinalValueDetails(item))}">FSFFL ${fmtFsfflValue(item.score)}</span>`;
};

function coreIntelligenceReady(context){
  return Boolean(context?.league_id&&context?.forecast_ready&&context?.simulation_ready&&context?.value_ready);
}

function presentRuntimeCapabilities(){
  const context=state?.context;
  if(!context?.league_id)return;
  const summary=document.querySelector('#runtime-status-summary');
  const title=document.querySelector('#runtime-status-title');
  const grid=document.querySelector('#runtime-stage-grid');
  if(coreIntelligenceReady(context)){
    if(summary)summary.textContent='Core ready';
    if(title&&/ready/i.test(title.textContent||''))title.textContent='Core intelligence is ready.';
  }
  if(!grid)return;
  [...grid.querySelectorAll('.runtime-stage')].forEach(node=>{
    const label=node.querySelector('strong')?.textContent?.trim().toLowerCase();
    if(label==='trade decision'||label==='opportunity'){
      node.classList.add('capability-next');
      const mark=node.querySelector('.runtime-stage-mark');
      if(mark)mark.textContent='→';
      const detail=node.querySelector('small');
      if(detail){
        detail.textContent=label==='trade decision'
          ?'Decision capability is being connected to the product; it is not a missing core-intelligence prerequisite.'
          :'Opportunity discovery activates downstream of the completed Trade Decision product connection.';
      }
    }
  });
}

function selectedTradeAssets(side){
  const team=tradeSideTeam(side);
  const selected=selectedRefs(side);
  if(!team)return[];
  return [...selected].map(ref=>team.assets.find(item=>item.asset_ref===ref)).filter(Boolean);
}

function assetNames(items){
  return items.length?items.map(item=>escapeHtml(item.label)).join(', '):'None selected';
}

function directionSentence(label,value,direction){
  if(typeof value!=='number')return `${label}: evidence unavailable.`;
  const readable=tradeDirectionText(direction);
  return `${label}: ${signedTradeNumber(value,2)} (${readable}).`;
}

function sidePlainEnglish(result,teamId){
  const side=analysisSide(result,teamId);
  const resilience=side.evaluation?.delta?.resilience;
  if(!resilience)return 'Roster consequence evidence is not available for this side yet.';
  const pieces=[
    directionSentence('Largest single-player lineup exposure',resilience.largest_single_player_lineup_drop,side.decision?.largest_single_player_lineup_drop),
    directionSentence('Forecast-supported bench depth',resilience.bench_forecasted_count,side.decision?.bench_forecasted_count),
  ];
  if((resilience.unavailable_count||0)>0)pieces.push(`${resilience.unavailable_count} unavailable player(s) remain in the changed roster.`);
  if((resilience.missing_forecast_count||0)>0)pieces.push(`${resilience.missing_forecast_count} rostered player(s) are missing forecast evidence.`);
  return pieces.join(' ');
}

function marketComparison(side){
  const sent=side.economics?.sent_market?.mean_value;
  const received=side.economics?.received_market?.mean_value;
  if(typeof sent!=='number'||typeof received!=='number')return 'Market comparison is not available for every asset in this package.';
  const delta=received-sent;
  if(Math.abs(delta)<1e-9)return 'Governed market evidence is essentially even between the assets sent and received.';
  return `Governed market evidence is ${delta>0?'higher':'lower'} on the received side than on the sent side in the current market representation.`;
}

function humanTradeSide(result,teamId,sideKey){
  const side=analysisSide(result,teamId);
  const sending=selectedTradeAssets(sideKey);
  const receiving=selectedTradeAssets(sideKey==='focal'?'counterparty':'focal');
  const name=tradeTeamName(teamId);
  return `<article class="human-trade-side">
    <p class="eyebrow">${escapeHtml(name)}</p>
    <h3>Franchise impact</h3>
    <div class="human-trade-package"><strong>Sends</strong><span>${assetNames(sending)}</span></div>
    <div class="human-trade-package"><strong>Receives</strong><span>${assetNames(receiving)}</span></div>
    <div class="human-trade-takeaway"><strong>What changes now</strong><p>${escapeHtml(sidePlainEnglish(result,teamId))}</p></div>
    <div class="human-trade-takeaway"><strong>Market context</strong><p>${escapeHtml(marketComparison(side))}</p></div>
  </article>`;
}

renderTradeAnalysis=function(result){
  const panel=qs('#trade-analysis-empty');
  if(!panel)return;
  const focalId=result.focal_team_id;
  const counterpartyId=result.counterparty_team_id;
  const competitiveReady=Boolean(result.availability?.competitive_outcomes);
  const rosterReady=Boolean(result.availability?.roster_consequences);
  const warnings=result.warnings||[];
  panel.innerHTML=`<div class="human-trade-report">
    <div class="human-trade-report-header">
      <div><p class="eyebrow">Trade analysis</p><h3>What this deal changes</h3><p>This view explains the governed evidence currently available. It is not inventing a trade grade or acceptance probability.</p></div>
      <span class="status-chip">${rosterReady?'Roster analysis ready':'Partial analysis'}</span>
    </div>
    <div class="human-trade-summary-grid">
      ${humanTradeSide(result,focalId,'focal')}
      ${humanTradeSide(result,counterpartyId,'counterparty')}
    </div>
    <section class="human-trade-next">
      <div><strong>Competitive impact</strong><span>${competitiveReady?'Simulation evidence attached':'Post-trade simulation not connected yet'}</span><small>${competitiveReady?'The changed roster has simulation-backed competitive evidence.':'Expected wins, playoff odds and first-place odds will appear here once the changed roster is run through NEXT-4 Simulation authority.'}</small></div>
      <div><strong>Behavioral plausibility</strong><span>Not estimated yet</span><small>Acceptance and negotiation behavior will appear only from a governed Decision/API contract.</small></div>
    </section>
    <details class="technical-evidence"><summary>Technical evidence & limitations</summary>
      <div class="technical-evidence-grid">${sideAnalysisMarkup(result,focalId)}${sideAnalysisMarkup(result,counterpartyId)}</div>
      ${warnings.length?`<ul>${warnings.map(item=>`<li>${escapeHtml(item)}</li>`).join('')}</ul>`:''}
    </details>
  </div>`;
};

function installProductPolish(){
  const rosterLead=document.querySelector('.roster-panel .lead');
  if(rosterLead){
    rosterLead.removeAttribute('title');
    rosterLead.innerHTML='<strong>FSFFL Value uses the authoritative NEXT-3 market-cardinal score.</strong> Market percentile remains a separate governed market-position measure.';
  }
  const style=document.createElement('style');
  style.textContent=`
    .runtime-stage.capability-next{opacity:.78;border-style:dashed}
    .human-trade-report{width:100%;text-align:left}
    .human-trade-report-header{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px}
    .human-trade-report-header h3{margin:0 0 6px;font-size:1.45rem}
    .human-trade-report-header p{color:var(--muted);margin:0;line-height:1.45}
    .human-trade-summary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
    .human-trade-side{border:1px solid var(--line);border-radius:14px;padding:16px;background:#0a1120;min-width:0}
    .human-trade-side h3{margin:0 0 14px}
    .human-trade-package{display:grid;grid-template-columns:72px 1fr;gap:8px;padding:9px 0;border-bottom:1px solid var(--line);line-height:1.4}
    .human-trade-package span{overflow-wrap:anywhere}
    .human-trade-takeaway{margin-top:14px}
    .human-trade-takeaway p{margin:5px 0 0;color:var(--muted);line-height:1.55}
    .human-trade-next{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:14px}
    .human-trade-next>div{border:1px solid var(--line);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:6px}
    .human-trade-next span{font-weight:700}
    .human-trade-next small{color:var(--muted);line-height:1.45}
    .technical-evidence{margin-top:14px;color:var(--muted)}
    .technical-evidence summary{cursor:pointer;color:var(--accent);padding:8px 0}
    .technical-evidence-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:10px}
    @media(max-width:720px){
      .human-trade-report-header{display:block}.human-trade-report-header .status-chip{display:inline-flex;margin-top:12px}
      .human-trade-summary-grid,.human-trade-next,.technical-evidence-grid{grid-template-columns:1fr}
      .human-trade-side{padding:14px}
      .human-trade-package{grid-template-columns:64px minmax(0,1fr)}
    }
  `;
  document.head.appendChild(style);
  presentRuntimeCapabilities();
  const observer=new MutationObserver(()=>presentRuntimeCapabilities());
  const grid=document.querySelector('#runtime-stage-grid');
  if(grid)observer.observe(grid,{childList:true,subtree:true,characterData:true});
  setInterval(presentRuntimeCapabilities,2000);
}

window.addEventListener('load',installProductPolish);
