(function(){
  const actionLabels={
    accept:'Pursue this trade',
    support:'Pursue this trade',
    reject:'Do not make this trade',
    decline:'Do not make this trade',
    counter:'Counter',
    counter_or_review:'Counter or review',
    hold:'Hold',
    review:'Review before acting',
    no_clear_advantage:'No clear advantage',
    insufficient_evidence:'Not enough evidence to act',
  };

  function esc(value){return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}
  function words(value){return String(value||'').replaceAll('_',' ')}
  function packageLabel(items){return(items||[]).map(item=>item.label).filter(Boolean).join(' + ')||'—'}
  function dispositionAction(result){return result?.disposition?.action||result?.disposition?.disposition||result?.disposition?.shape||''}
  function driverLabel(value){const text=words(value);if(!text)return'';return text.charAt(0).toUpperCase()+text.slice(1)}
  function dispositionDrivers(result){
    const evidence=result?.disposition?.evidence||{};
    const gains=(evidence.material_gains||[]).map(item=>`Gain: ${driverLabel(item)}`);
    const losses=(evidence.material_losses||[]).map(item=>`Risk: ${driverLabel(item)}`);
    const missing=(evidence.unavailable_metrics||[]).map(item=>`Missing: ${driverLabel(item)}`);
    return[...gains,...losses,...missing];
  }
  function actionLabel(action){return actionLabels[action]||driverLabel(action)||'No action yet'}

  function decisionCard(result){
    const action=dispositionAction(result);
    if(!action)return'';
    const drivers=dispositionDrivers(result).slice(0,6);
    const simulations=Number(result.scenario_simulation_count||0);
    const negotiation=words(result?.disposition?.evidence?.negotiation_shape||'');
    return`<section class="authoritative-trade-decision" style="border:1px solid var(--accent);border-radius:14px;padding:16px;margin:0 0 14px;background:#0a1120">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap">
        <div><p class="eyebrow" style="margin-bottom:5px">FSFFL decision</p><h2 style="margin:0">${esc(actionLabel(action))}</h2><p style="color:var(--muted);margin:7px 0 0;max-width:760px">This is the focal-team NEXT-5 disposition after the changed roster ran through NEXT-4 Simulation, governed materiality and package economics. Counterparty feasibility is shown separately as negotiation context and does not reverse a clean advantage for your team.</p></div>
        <span class="status-chip">${simulations?`${simulations.toLocaleString()} scenario runs`:'Changed-state simulation complete'}</span>
      </div>
      ${drivers.length?`<div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:12px">${drivers.map(item=>`<span class="opp-badge">${esc(item)}</span>`).join('')}</div>`:''}
      ${negotiation?`<p style="font-size:12px;color:var(--muted);margin:10px 0 0"><strong>Negotiation context:</strong> ${esc(negotiation)}. This describes the bilateral shape, not whether your team should reject an otherwise favorable offer.</p>`:''}
      <p style="font-size:11px;color:var(--muted);margin:12px 0 0">The reasons above are copied from governed disposition evidence. FSFFL Value remains market context. Owner history may inform negotiation context, but no acceptance probability is invented here.</p>
    </section>`;
  }

  function installPreliminaryRead(result){
    const root=document.querySelector('#trade-analysis-empty > div');if(!root)return;
    root.querySelector('.trade-preliminary-read')?.remove();
    const focalId=result?.focal_team_id;
    const focal=[result?.decision?.side_a,result?.decision?.side_b].find(side=>side?.team_id===focalId);
    const other=[result?.decision?.side_a,result?.decision?.side_b].find(side=>side&&side.team_id!==focalId);
    const card=document.createElement('section');card.className='trade-preliminary-read';card.style.cssText='border:1px solid var(--line);border-radius:12px;padding:14px;margin:0 0 14px;background:#0a1120';
    card.innerHTML=`<p class="eyebrow" style="margin-bottom:5px">Preliminary read</p><h3 style="margin:0">Run the changed-roster simulation to finish the recommendation</h3><p style="color:var(--muted);font-size:12px;margin:7px 0 0">Fast bilateral Decision evidence currently reads <strong style="color:var(--text)">you: ${esc(words(focal?.shape||'incomplete'))}</strong>${other?` · other team: <strong style="color:var(--text)">${esc(words(other.shape||'incomplete'))}</strong>`:''}. This is not the final action disposition because competitive materiality has not yet been recomputed on the changed roster.</p>`;
    root.insertBefore(card,root.firstChild);
  }

  function elevateFinalDecision(result){
    const root=document.querySelector('#trade-analysis-empty > div');if(!root)return;
    root.querySelector('.trade-preliminary-read')?.remove();
    root.querySelector('.authoritative-trade-decision')?.remove();
    const markup=decisionCard(result);if(!markup)return;
    root.insertAdjacentHTML('afterbegin',markup);
  }

  function frontierSummary(result){
    const points=(result?.points||[]).filter(point=>!point.is_seed);
    const mutual=points.filter(point=>point.feasibility_shape==='mutual_gain_candidate').sort((a,b)=>(a.search_distance??Infinity)-(b.search_distance??Infinity)||a.depth-b.depth);
    const nearest=mutual[0];
    if(nearest){
      return`<section class="frontier-interpretation" style="border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px;background:#0a1120"><p class="eyebrow" style="margin-bottom:5px">Best path to investigate</p><h3 style="margin:0">Closest mutual-gain package candidate</h3><p style="margin:8px 0 0"><strong>You send:</strong> ${esc(packageLabel(nearest.focal_assets))}<br><strong>You receive:</strong> ${esc(packageLabel(nearest.counterparty_assets))}</p><p style="color:var(--muted);font-size:12px;margin:8px 0 0">${mutual.length} mutual-gain candidate${mutual.length===1?'':'s'} found in the adjacent frontier. This is diagnostic price discovery, not an acceptance forecast or action recommendation; unknown materiality or acceptance evidence still fails closed.</p></section>`;
    }
    return`<section class="frontier-interpretation" style="border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px;background:#0a1120"><p class="eyebrow" style="margin-bottom:5px">Negotiation read</p><h3 style="margin:0">No nearby mutual-gain package surfaced</h3><p style="color:var(--muted);font-size:12px;margin:8px 0 0">NEXT-6 tested ${Number(result?.evaluated_count||0).toLocaleString()} adjacent package variations. The current diagnostic frontier did not find a nearby package positive for both sides; that is evidence to widen the search or reconsider the target, not proof that a deal is impossible.</p></section>`;
  }

  function install(){
    if(typeof window.renderTradeAnalysis==='function'){
      const original=window.renderTradeAnalysis;
      window.renderTradeAnalysis=function(result){original(result);installPreliminaryRead(result)};
    }
    if(typeof window.renderTradeSimulationResult==='function'){
      const original=window.renderTradeSimulationResult;
      window.renderTradeSimulationResult=function(result){original(result);elevateFinalDecision(result)};
    }
    if(typeof window.renderTradeFrontierResult==='function'){
      const original=window.renderTradeFrontierResult;
      window.renderTradeFrontierResult=function(result){original(result);const target=document.querySelector('#trade-frontier-result');if(target)target.insertAdjacentHTML('afterbegin',frontierSummary(result))};
    }
  }

  install();
})();
