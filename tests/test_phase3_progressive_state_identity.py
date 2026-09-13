from pathlib import Path
import json
import shutil
import subprocess

import pytest


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"
SCRIPT = STATIC / "progressive_delivery.js"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_trade_progression_pins_every_stage_to_the_same_authoritative_state() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "startingStateId=currentStateId()" in source
    assert "responseMatchesState(quick,startingStateId)" in source
    assert "flowStateId=quick.state_id_before||startingStateId" in source
    assert "responseMatchesState(analysis,flowStateId)" in source
    assert "responseMatchesState(simulation,flowStateId)" in source


def test_background_runtime_refresh_cannot_mix_trade_stages() -> None:
    script_path = json.dumps(str(SCRIPT))
    harness = f"""
const fs=require('fs'),vm=require('vm');
const listeners={{}},resolvers={{}},calls=[];
let analysisRenders=0,simulationRenders=0;
const draft={{counterparty_team_id:'team-b',focal_asset_refs:['p1'],counterparty_asset_refs:['p2']}};
const button={{disabled:false,textContent:'Analyze Trade'}};
const host={{innerHTML:'',querySelector:()=>null,appendChild:()=>{{}}}};
global.window=global;
global.state={{context:{{league_id:'league',team_id:'team-a',state_id:'state-one'}}}};
global.tradeDraftPayload=()=>draft;
global.invalidateTradeScenario=()=>{{}};
global.updateAnalyzeTradeState=()=>{{button.disabled=false}};
global.renderTradeAnalysis=()=>{{analysisRenders+=1}};
global.renderTradeSimulationResult=()=>{{simulationRenders+=1}};
global.document={{
  querySelector:(selector)=>selector==='#trade-analysis-empty'?host:selector==='#analyze-trade'?button:null,
  createElement:()=>({{className:'',dataset:{{}},textContent:''}})
}};
global.addEventListener=(name,handler)=>{{listeners[name]=handler}};
global.setInterval=()=>1;global.clearInterval=()=>{{}};global.setTimeout=()=>1;
global.api=(path)=>{{calls.push(path);return new Promise((resolve,reject)=>{{resolvers[path]={{resolve,reject}}}})}};
vm.runInThisContext(fs.readFileSync({script_path},'utf8'),{{filename:'progressive_delivery.js'}});
const event={{target:{{closest:(selector)=>selector==='#analyze-trade'?button:null}},preventDefault:()=>{{}},stopImmediatePropagation:()=>{{}}}};
(async()=>{{
  const running=listeners.click(event);
  resolvers['/api/trade-center/quick'].resolve({{state_id_before:'state-one',economics:null}});
  await new Promise(resolve=>setImmediate(resolve));
  if(!host.innerHTML.includes('Quick view ready'))throw new Error('quick view did not render');
  if(!calls.includes('/api/trade-center/analyze'))throw new Error('analysis did not start');
  // Simulate a server-side runtime refresh that the browser has not yet observed.
  resolvers['/api/trade-center/analyze'].resolve({{state_id_before:'state-two',decision_completeness:{{}}}});
  await running;
  if(analysisRenders!==0)throw new Error('analysis from a different league state rendered');
  if(simulationRenders!==0||calls.includes('/api/trade-center/simulate'))throw new Error('mixed-state flow advanced to simulation');
  if(!host.innerHTML.includes('League data changed during roster analysis'))throw new Error('state mismatch was not explained');
}})().catch(error=>{{console.error(error);process.exit(1)}});
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
