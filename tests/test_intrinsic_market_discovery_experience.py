from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"
INDEX = STATIC / "index.html"
RELEASE = "20260925-state-first1"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_market_disagreement_experience_preserves_value_authority_boundaries() -> None:
    script = _text("intrinsic_market_discovery.js")
    assert "shared 0-10,000 Value Index is presentation-only" in script
    assert "Percentile remains secondary" in script
    assert "not a buy/sell instruction" in script
    assert "raw Market and raw Shapley quantities are never subtracted" in script
    assert "League Market Value remains unavailable" in script
    assert "Team Utility and acceptance evidence remain separate" in script
    assert "api('/api/opportunities/value-disagreements?minimum_gap=0.10&limit=24')" in script


def test_market_disagreement_experience_is_lazy_and_does_not_request_on_startup() -> None:
    script_path = json.dumps(str(STATIC / "intrinsic_market_discovery.js"))
    harness = f'''
const fs=require('fs'),vm=require('vm');
let calls=0;
global.window=global;
global.state={{route:'league',context:{{state_id:'state-1',team_id:'team-1'}}}};
global.api=()=>{{calls+=1;return Promise.resolve({{status:'ready',rows:[]}})}};
global.requestAnimationFrame=fn=>{{fn();return 1}};
global.document={{
  readyState:'complete',
  body:{{}},
  querySelector:()=>null
}};
global.MutationObserver=class{{constructor(cb){{this.cb=cb}} observe(){{}}}};
global.addEventListener=()=>{{}};
vm.runInThisContext(fs.readFileSync({script_path},'utf8'),{{filename:'intrinsic_market_discovery.js'}});
if(calls!==0)throw new Error('lazy discovery made '+calls+' API requests during startup');
'''
    result = subprocess.run(
        [_node(), "-e", harness],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_market_disagreement_handoff_uses_existing_server_owned_market_intent() -> None:
    discovery = _text("intrinsic_market_discovery.js")
    posture = _text("opportunity_posture_ui.js")
    assert "window.fsfflMarketIntent?.set" in discovery
    assert "setter(row.focus_intent,row.focus_value)" in discovery
    assert "set:(intent,value='')" in posture
    assert "broadcastIntent()" in posture
    assert "fsffl:market-intent-changed" in posture


def test_market_disagreement_discards_stale_context_responses() -> None:
    script = _text("intrinsic_market_discovery.js")
    assert "requestIsCurrent(requestGeneration,ctx.stateId,ctx.teamId)" in script
    assert "payload?.league_state_id&&payload.league_state_id!==ctx.stateId" in script
    assert "payload?.focal_team_id&&payload.focal_team_id!==ctx.teamId" in script
    assert "generation+=1" in script
    assert "fsffl:product-context-updated" in script


def test_market_disagreement_has_mobile_layout_and_release_wiring() -> None:
    css = _text("intrinsic_market_discovery.css")
    html = INDEX.read_text(encoding="utf-8")
    assert "@media(max-width:680px)" in css
    assert ".imd-row{grid-template-columns:1fr 1fr" in css
    assert f"/static/intrinsic_market_discovery.css?v={RELEASE}" in html
    assert f"/static/intrinsic_market_discovery.js?v={RELEASE}" in html


def test_market_disagreement_browser_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "intrinsic_market_discovery.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
