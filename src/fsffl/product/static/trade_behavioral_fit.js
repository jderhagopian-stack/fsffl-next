/* Trade Center Behavioral-fit presentation extension.
 * Presentation only: consumes behavioral_fit returned by the shared post-trade
 * runtime. It does not calculate acceptance, Value, disposition or authority.
 */

const fsfflBaseTradeSimulationRenderer=typeof renderTradeSimulationResult==='function'?renderTradeSimulationResult:null;

function tradeBehaviorFitWords(value){return String(value||'unknown').replaceAll('_',' ')}
function tradeBehaviorFitMarkup(fit){
  if(!fit)return`<section class="trade-behavior-fit"><div><p class="eyebrow">Behavioral fit</p><h3>Unknown</h3><p>Historical owner evidence is not ready or cannot be mapped to this franchise. FSFFL does not substitute a guessed profile.</p></div></section>`;
  const drivers=fit.drivers||[];
  return`<section class="trade-behavior-fit ${escapeHtml(fit.direction||'unknown')}">
    <div class="trade-behavior-fit-head"><div><p class="eyebrow">Behavioral fit for this exact package</p><h3>${escapeHtml(tradeBehaviorFitWords(fit.direction))}</h3><p>Directional inference from ${Number(fit.observed_trade_count||0).toLocaleString()} observed trade(s). This helps judge negotiation plausibility; it is not an acceptance probability.</p></div><span class="status-chip">${escapeHtml(tradeBehaviorFitWords(fit.evidence_level))}</span></div>
    ${drivers.length?`<div class="trade-behavior-driver-grid">${drivers.map(driver=>`<div><strong>${escapeHtml(tradeBehaviorFitWords(driver.direction))}</strong><span>${escapeHtml(tradeBehaviorFitWords(driver.kind))}</span><small>${escapeHtml(driver.description)}</small></div>`).join('')}</div>`:'<p>No individual Behavioral drivers are available for this package.</p>'}
    <p class="trade-behavior-boundary"><strong>Authority boundary:</strong> Behavioral fit cannot change FSFFL Value, the focal accept/decline disposition, competitive Simulation, or NEXT-6 action authority. Numeric acceptance remains unavailable until separately calibrated.</p>
  </section>`;
}

if(fsfflBaseTradeSimulationRenderer){
  renderTradeSimulationResult=function(result){
    fsfflBaseTradeSimulationRenderer(result);
    const target=qs('#trade-simulation-result');
    if(!target)return;
    target.insertAdjacentHTML('beforeend',tradeBehaviorFitMarkup(result?.behavioral_fit));
  };
}

(function installTradeBehaviorFitStyles(){
  if(document.querySelector('#trade-behavior-fit-style'))return;
  const style=document.createElement('style');style.id='trade-behavior-fit-style';style.textContent=`
    .trade-behavior-fit{border:1px solid var(--line);border-radius:12px;padding:14px;margin-top:12px;background:#0a1120}
    .trade-behavior-fit.elevated{border-color:var(--accent)}
    .trade-behavior-fit-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
    .trade-behavior-fit h3{margin:2px 0;text-transform:capitalize}
    .trade-behavior-fit p{color:var(--muted);font-size:12px;line-height:1.5;margin:5px 0}
    .trade-behavior-driver-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
    .trade-behavior-driver-grid>div{border:1px solid var(--line);border-radius:9px;padding:10px;display:grid;gap:4px}
    .trade-behavior-driver-grid strong{text-transform:capitalize}
    .trade-behavior-driver-grid span,.trade-behavior-driver-grid small{color:var(--muted);font-size:11px;line-height:1.4}.trade-behavior-driver-grid span{text-transform:capitalize}
    .trade-behavior-boundary{border-top:1px solid var(--line);padding-top:10px;margin-top:12px!important}
    @media(max-width:720px){.trade-behavior-fit-head{display:block}.trade-behavior-driver-grid{grid-template-columns:1fr}}
  `;document.head.appendChild(style);
})();
