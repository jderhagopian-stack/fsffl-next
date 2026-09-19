from pathlib import Path
import json
import shutil
import subprocess

import pytest


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_value_lens_preserves_four_value_coordinates_and_unavailability():
    script = _text("intrinsic_value_experience.js")
    assert "Broad Market Value" in script
    assert "FSFFL Intrinsic Value" in script
    assert "League Market Value" in script
    assert "Team Utility" in script
    assert "Not production-ready" in script
    assert "No substitute number is shown" in script
    assert "will not silently use one in place of Intrinsic" in script


def test_value_lens_uses_governed_intrinsic_api_and_does_not_rebrand_legacy_value():
    script = _text("intrinsic_value_experience.js")
    assert "api('/api/value/intrinsic-v1')" in script
    assert "provisional_fsffl_values" not in script
    assert "fsffl_cardinal_values" not in script
    assert "older generic “FSFFL Value”" in script
    assert "is not this Intrinsic value" in script
    assert "FSFFL Cardinal Value" in script
    assert "replaceTextWithin(document.querySelector('.franchise-shell'),'FSFFL Value','FSFFL Cardinal Value')" in script
    assert "replaceTextWithin(document.querySelector('.league-structure-panel'),'Total FSFFL value','Total FSFFL Cardinal Value')" in script


def test_value_lens_comparison_is_rank_only_and_not_a_fake_common_scale():
    script = _text("intrinsic_value_experience.js")
    assert "percentile rank only as a presentation aid" in script
    assert "Broad Market and Intrinsic use different units" in script
    assert "does <strong>not</strong> subtract the raw numbers" in script
    assert "not an automatic buy signal" in script
    assert "not an automatic sell signal" in script


def test_value_lens_is_lazy_and_does_not_add_an_intrinsic_request_to_first_paint():
    script = _text("intrinsic_value_experience.js")
    bootstrap = _text("league_position_strength.js")
    assert "button.addEventListener('click',()=>activate(shell))" in script
    assert "function activate(panel)" in script
    assert "load()" in script
    assert "api('/api/value/intrinsic-v1')" in script
    assert "/api/value/intrinsic-v1" not in bootstrap
    assert "the lens itself performs no API work until the customer opens its tab" in bootstrap


def test_value_lens_surfaces_confidence_and_provenance_secondarily():
    script = _text("intrinsic_value_experience.js")
    assert "Confidence" in script
    assert "Evidence & provenance" in script
    assert "forecast_policy_version" in script
    assert "base_forecast_model_version" in script
    assert "replacement_context_version" in script
    assert "What exactly is FSFFL Intrinsic Value?" in script


def test_value_lens_has_intentional_mobile_layout():
    css = _text("intrinsic_value_experience.css")
    assert "@media(max-width:680px)" in css
    assert ".value-lens-coordinates{grid-template-columns:1fr}" in css
    assert ".value-lens-player summary{grid-template-columns:1fr 1fr" in css
    assert ".franchise-tabs{overflow-x:auto" in css


def test_value_lens_browser_script_parses():
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "intrinsic_value_experience.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_value_lens_discards_stale_response_and_current_context_still_renders():
    script_path = json.dumps(str(STATIC / "intrinsic_value_experience.js"))
    harness = f"""
const fs=require('fs'),vm=require('vm');
const host={{innerHTML:'',querySelector:()=>null}};
const listeners={{}};
let calls=0,resolvers=[];
global.window=global;
global.state={{context:{{state_id:'state-old'}}}};
global.document={{
  readyState:'complete',body:{{}},
  querySelector:(selector)=>selector==='[data-franchise-view=\"value_lens\"]'?host:null,
  createTreeWalker:()=>({{nextNode:()=>false}})
}};
global.NodeFilter={{SHOW_TEXT:4}};
global.MutationObserver=class{{constructor(cb){{this.cb=cb}} observe(){{}}}};
global.addEventListener=(name,handler)=>{{listeners[name]=handler}};
global.setTimeout=(fn)=>{{fn();return 1}};
global.api=()=>{{calls+=1;return new Promise(resolve=>resolvers.push(resolve))}};
vm.runInThisContext(fs.readFileSync({script_path},'utf8'),{{filename:'intrinsic_value_experience.js'}});
(async()=>{{
  const first=window.fsfflIntrinsicValueExperience.load();
  if(calls!==1)throw new Error(`expected one request, got ${{calls}}`);
  const loading=host.innerHTML;
  state.context.state_id='state-new';
  listeners['fsffl:product-context-updated']();
  resolvers.shift()({{model_version:'stale-model',estimates:[{{player_id:'stale',value:999}}]}});
  await first;
  if(host.innerHTML!==loading)throw new Error('obsolete request mutated the DOM');
  const second=window.fsfflIntrinsicValueExperience.load();
  if(calls!==2)throw new Error('obsolete request repopulated cache or blocked a new request');
  resolvers.shift()({{model_version:'current-model',estimates:[{{player_id:'current',value:10}}]}});
  await second;
  if(!host.innerHTML.includes('current-model'))throw new Error('current-context response did not render');
  if(host.innerHTML.includes('stale-model'))throw new Error('stale response remained visible');
}})().catch(error=>{{console.error(error);process.exit(1)}});
"""
    result = subprocess.run(
        [_node(), "-e", harness],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_value_lens_request_generation_guard_is_authoritative():
    script = _text("intrinsic_value_experience.js")
    assert "requestGeneration=0" in script
    assert "requestIsCurrent(generation,sid)" in script
    assert "if(!requestIsCurrent(generation,sid))return" in script
    assert "requestGeneration+=1" in script
    assert "if(inFlight?.generation===generation&&inFlight?.stateId===sid)inFlight=null" in script


def test_value_lens_bootstrap_cache_key_is_bumped_consistently():
    html = _text("index.html")
    bootstrap = _text("league_position_strength.js")
    experience = _text("intrinsic_value_experience.js")
    shell_version = "20260913-phase3-latency1"
    experience_version = "20260913-phase3-intrinsic2"
    assert f'/static/league_position_strength.js?v={shell_version}' in html
    assert '/static/league_position_strength.js?v=20260913-phase3-intrinsic2' not in html
    assert f"const version='{experience_version}'" in bootstrap
    assert f"const VERSION='{experience_version}'" in experience
    assert f'/static/intrinsic_value_experience.css?v=${{version}}' in bootstrap
    assert f'/static/intrinsic_value_experience.js?v=${{version}}' in bootstrap
