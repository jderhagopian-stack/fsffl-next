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


def test_value_lens_uses_governed_intrinsic_api_and_market_cardinal_magnitude():
    script = _text("intrinsic_value_experience.js")
    assert "api('/api/value/intrinsic-v1')" in script
    assert "provisional_fsffl_values" not in script
    assert "fsffl_cardinal_values" in script
    assert "MARKET_CARDINAL_SCALE='fsffl-market-cardinal'" in script
    assert "FSFFL Cardinal Value" in script
    assert "replaceTextWithin(document.querySelector('.franchise-shell'),'FSFFL Value','FSFFL Cardinal Value')" in script


def test_value_lens_shows_dynasty_values_primarily_and_rank_secondarily():
    script = _text("intrinsic_value_experience.js")
    assert "intrinsic_dynasty_value" in script
    assert "Broad Market Value" in script
    assert "weighted surplus points" in script
    assert "0–10,000" in script
    assert "rank—not raw point subtraction" in script
    assert "market-independent monotonic transform" in script
    assert " pts`" not in script


def test_value_lens_disagreement_remains_rank_based_and_not_a_master_score():
    script = _text("intrinsic_value_experience.js")
    assert "const delta=intrinsicRank-marketRank" in script
    assert "FSFFL materially higher" in script
    assert "FSFFL moderately higher" in script
    assert "Broad market moderately higher" in script
    assert "Broad market materially higher" in script
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


def test_value_lens_surfaces_confidence_provenance_and_raw_internal_value_secondarily():
    script = _text("intrinsic_value_experience.js")
    assert "Confidence" in script
    assert "Evidence & provenance" in script
    assert "raw_intrinsic_value" in script
    assert "forecast_policy_version" in script
    assert "base_forecast_model_version" in script
    assert "replacement_context_version" in script
    assert "What exactly is FSFFL Intrinsic Value?" in script


def test_value_lens_distinguishes_valid_zero_from_unavailable():
    script = _text("intrinsic_value_experience.js")
    assert "Valid zero:" in script
    assert "this is not missing evidence" in script
    assert "Missing Forecast or replacement evidence is shown as <strong>Unavailable</strong>" in script
    assert "availability==='available'" in script


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
global.fsfflMyTeamState={{view:{{players:[]}},values:{{fsffl_cardinal_values:[]}}}};
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
  resolvers.shift()({{model_version:'stale-model',players:[{{player_id:'stale',availability:'available',intrinsic_dynasty_value:999,percentile:.9}}]}});
  await first;
  if(host.innerHTML!==loading)throw new Error('obsolete request mutated the DOM');
  const second=window.fsfflIntrinsicValueExperience.load();
  if(calls!==2)throw new Error('obsolete request repopulated cache or blocked a new request');
  resolvers.shift()({{model_version:'current-model',display_scale:{{version:'1'}},players:[{{player_id:'current',availability:'available',intrinsic_dynasty_value:5000,percentile:.5}}]}});
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
    experience_version = "20260913-intrinsic-dynasty-scale1"
    assert f'/static/league_position_strength.js?v={shell_version}' in html
    assert f"const version='{experience_version}'" in bootstrap
    assert f"const VERSION='{experience_version}'" in experience
    assert f'/static/intrinsic_value_experience.css?v=${{version}}' in bootstrap
    assert f'/static/intrinsic_value_experience.js?v=${{version}}' in bootstrap
