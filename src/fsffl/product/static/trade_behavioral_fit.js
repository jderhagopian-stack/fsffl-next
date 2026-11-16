/* Trade Center Behavioral-fit presentation extension.
 * Presentation only: consumes behavioral_fit returned by the shared post-trade
 * runtime. It does not calculate acceptance, Value, disposition or authority.
 */

const fsfflBaseTradeSimulationRenderer=typeof renderTradeSimulationResult==='function'?renderTradeSimulationResult:null;

function tradeBehaviorFitWords(value){return String(value||'unknown').replaceAll('_',' ')}
function tradeBehaviorFitMarkup(fit){
  if(!fit||!fit.drivers?.length)return '';
  return `<details class="trade-behavior-fit"><summary>Recorded trading history · ${Number(fit.observed_trade_count||0)} completed trades</summary>${fit.drivers.slice(0,3).map(driver=>`<p>${escapeHtml(driver.description)}</p>`).join('')}</details>`;
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
