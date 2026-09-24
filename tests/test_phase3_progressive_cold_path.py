from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Lock
import json
import shutil
import subprocess
import time

import pytest

from fsffl.product import scenario_cache


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"
STATIC = PRODUCT / "static"
RELEASE = "20260924-live-usability-hotfix1"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_market_quick_path_uses_same_workspace_builder_without_decision_enrichment() -> None:
    routes = _text(PRODUCT / "progressive_delivery_routes.py")
    persistent = _text(PRODUCT / "persistent_webapp.py")
    assert '"/api/opportunities/workspace/quick"' in routes
    assert "workspace_builder(runtime, bilateral_evaluation_limit=0)" in routes
    assert '"completeness": "search_only"' in routes
    assert '"decision_enrichment_pending"' in routes
    assert "workspace_builder=_webapp.build_opportunity_workspace" in persistent
    assert "make_cached_opportunity_workspace" in persistent


def test_trade_quick_path_is_partial_and_does_not_create_simulation_or_decision_truth() -> None:
    routes = _text(PRODUCT / "progressive_delivery_routes.py")
    assert '"/api/trade-center/quick"' in routes
    assert "apply_bilateral_trade" in routes
    assert "summarize_bilateral_trade_economics" in routes
    assert '"completeness": "partial_package_economics"' in routes
    assert '"final_disposition_available": False' in routes
    assert '"full_simulation_pending": True' in routes
    for forbidden in (
        "run_live_simulation_analytics",
        "build_post_trade_simulation_comparison",
        "classify_bilateral_trade_decision",
        "decide_trade_disposition",
    ):
        assert forbidden not in routes


def test_browser_delivers_quick_then_deeper_authoritative_trade_evidence() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    quick = script.index("/api/trade-center/quick")
    analysis = script.index("/api/trade-center/analyze")
    simulation = script.index("/api/trade-center/simulate")
    assert quick < analysis < simulation
    assert "Quick view ready" in script
    assert "Full 50,000-run season simulation running" in script
    assert "scenario_cache_hit" in script
    assert "they are not a final trade recommendation" in script


def test_progressive_results_are_context_guarded_and_duplicate_trade_clicks_are_coalesced() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    assert "tradeGeneration+=1" in script
    assert "key===draftKey()" in script
    assert "if(!currentTrade(generation,key))return" in script
    assert script.count("if(!currentTrade(generation,key))return") >= 4
    assert "if(activeTradeKey===key)return" in script
    assert "contextStillCurrent" in script
    assert "oppPayloadMatchesCapturedContext(quick,captured)" in script
    assert "oppPayloadMatchesCapturedContext(full,captured)" in script
    assert "resetTradeForContext" in script


def test_market_quick_result_renders_before_full_decision_request_finishes() -> None:
    script = _text(STATIC / "progressive_delivery.js")
    quick_await = script.index("const quick=await request('/api/opportunities/workspace/quick')")
    quick_render = script.index("renderOpportunityWorkspace();", quick_await)
    full_request = script.index("request('/api/opportunities/workspace').then", quick_render)
    assert quick_await < quick_render < full_request
    assert "Quick view remains available" in script
    assert "Updated analysis ready" in script


def test_progressive_assets_use_one_fresh_hosted_release_generation() -> None:
    html = _text(STATIC / "index.html")
    versions = {token.split("?v=")[1].split('"')[0] for token in html.split() if "?v=" in token}
    assert versions == {RELEASE}
    assert f"progressive_delivery.css?v={RELEASE}" in html
    assert f"progressive_delivery.js?v={RELEASE}" in html
    assert html.rfind("progressive_delivery.js") > html.rfind("market_trade_drilldown.js")


def test_progressive_mobile_layout_keeps_first_answer_compact() -> None:
    css = _text(STATIC / "progressive_delivery.css")
    assert "@media(max-width:680px)" in css
    assert ".fsffl-progressive-sides{grid-template-columns:1fr}" in css
    assert ".fsffl-market-progress" in css
    assert "flex-direction:column" in css


def test_progressive_browser_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "progressive_delivery.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_context_change_discards_stale_trade_analysis_and_resets_action_button() -> None:
    script_path = json.dumps(str(STATIC / "progressive_delivery.js"))
    harness = f"""
const fs=require('fs'),vm=require('vm');
const listeners={{}},resolvers={{}},calls=[];
let analysisRenders=0,simulationRenders=0;
let draft={{counterparty_team_id:'team-b',focal_asset_refs:['p1'],counterparty_asset_refs:['p2']}};
const button={{disabled:false,textContent:'Analyze Trade'}};
const host={{innerHTML:'',querySelector:()=>null,appendChild:()=>{{}}}};
global.window=global;
global.state={{context:{{league_id:'league',team_id:'team-a',state_id:'state-old'}}}};
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
  if(calls[0]!=='/api/trade-center/quick')throw new Error('quick stage did not start first');
  resolvers['/api/trade-center/quick'].resolve({{state_id_before:'state-old',economics:null}});
  await new Promise(resolve=>setImmediate(resolve));
  if(!host.innerHTML.includes('Quick view ready'))throw new Error('quick view did not render');
  if(!calls.includes('/api/trade-center/analyze'))throw new Error('deeper analysis did not start');
  state.context.state_id='state-new';
  listeners['fsffl:product-context-updated']();
  if(button.textContent!=='Analyze Trade'||button.disabled)throw new Error('context invalidation did not reset action button');
  resolvers['/api/trade-center/analyze'].resolve({{state_id_before:'state-old',decision_completeness:{{}}}});
  await running;
  if(analysisRenders!==0)throw new Error('stale analysis rendered after context change');
  if(simulationRenders!==0||calls.includes('/api/trade-center/simulate'))throw new Error('stale flow advanced to simulation');
}})().catch(error=>{{console.error(error);process.exit(1)}});
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


class _FakeEvidence:
    model_version = "forecast-test-v1"
    successful_source_ids = ()
    league_scored_forecasts = ()


class _FakeState:
    def __init__(self, state_id: str):
        self.state_id = state_id


def _fake_result(state_id: str):
    return SimpleNamespace(league_view=SimpleNamespace(context=SimpleNamespace(league_state_id=state_id)))


def test_identical_concurrent_simulations_share_one_authoritative_run_and_near_repeat_misses() -> None:
    scenario_cache.configure_scenario_cache_persistence(None)
    scenario_cache.clear_scenario_cache()
    evidence = _FakeEvidence()
    state = _FakeState("changed-state-a")
    started = Event()
    release = Event()
    count_lock = Lock()
    calls = 0

    def loader(current_state, _evidence):
        nonlocal calls
        with count_lock:
            calls += 1
        started.set()
        assert release.wait(2)
        return _fake_result(current_state.state_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(
            scenario_cache.run_cached_scenario_simulation,
            state,
            evidence,
            simulation_loader=loader,
        )
        assert started.wait(1)
        follower = pool.submit(
            scenario_cache.run_cached_scenario_simulation,
            state,
            evidence,
            simulation_loader=loader,
        )
        time.sleep(0.05)
        release.set()
        first = leader.result(timeout=2)
        second = follower.result(timeout=2)

    assert calls == 1
    assert first[0] is second[0]
    assert sorted((first[1], second[1])) == [False, True]
    status = scenario_cache.scenario_cache_status()
    assert status["coalesced_hits"] == 1
    assert status["inflight"] == 0

    near_repeat = _FakeState("changed-state-b")
    third, cache_hit = scenario_cache.run_cached_scenario_simulation(
        near_repeat,
        evidence,
        simulation_loader=loader,
    )
    assert third.league_view.context.league_state_id == "changed-state-b"
    assert cache_hit is False
    assert calls == 2
    scenario_cache.clear_scenario_cache()
