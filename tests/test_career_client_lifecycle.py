"""Execute the production Career client, including its asynchronous fences."""
from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE = Path(__file__).parents[1] / "src/fsffl/product/static/my_team_dashboard.js"


def test_career_client_retries_and_rejects_obsolete_publications():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the browser lifecycle harness")
    prefix = SOURCE.read_text().split("function myTeamIntrinsic(id)", 1)[0]
    harness = r"""
const assert=require('node:assert/strict');
const state={route:'my_team',context:{state_id:'A'}};
const view={context:{league_state_id:'A'},publication_generation_id:'g1'};
fsfflMyTeamState.view=view;
let requests=0, release;
let api=async()=>{requests++;return {status:'building',league_state_id:'A'}};
const nativeTimer=setTimeout;
// Advance retries immediately; they must remain finite.
setTimeout=(f)=>nativeTimer(f,0);
(async()=>{
 await loadCareerIntrinsicForState('A');
 assert.equal(requests,16);
 assert.equal(fsfflMyTeamState.careerIntrinsic.status,'unavailable');
 api=async()=>{requests++;return {status:'ready',league_state_id:'A',publication_generation_id:'g1',estimates:[{player_id:'p',raw_career_forward_reference:12}]}};
 await loadCareerIntrinsicForState('A');
 assert.equal(requests,17); // prior timeout must not poison same-State cache
 assert.equal(myTeamCareerEstimate('p').raw_career_forward_reference,12);
 await loadCareerIntrinsicForState('A');assert.equal(requests,17);
 // Target B while Franchise still serves A: neither fetch nor display B.
 state.context.state_id='B';fsfflMyTeamState.view={...view,presentation_continuity:{served_league_state_id:'A'}};
 resetCareerRequestForState('B');
 assert.equal(myTeamCareerEstimate('p').raw_career_forward_reference,12); // preserve matching last-good evidence
 await loadCareerIntrinsicForState('B');assert.equal(requests,17);
 fsfflMyTeamState.careerIntrinsic={status:'ready',league_state_id:'B',publication_generation_id:'g1',estimates:[{player_id:'p'}]};
 assert.equal(myTeamCareerEstimate('p'),null);
 // Pending work coalesces, and navigation prevents late publication.
 state.context.state_id='A';fsfflMyTeamState.view=view;fsfflMyTeamState.careerIntrinsic=null;
 api=()=>{requests++;return new Promise(r=>{release=r})};
 const first=loadCareerIntrinsicForState('A'),second=loadCareerIntrinsicForState('A');
 assert.equal(requests,18);
 state.route='league_comparison';
 release({status:'ready',league_state_id:'A',publication_generation_id:'g1',estimates:[{player_id:'p'}]});
 assert.equal(await first,null);assert.equal(await second,null);
 assert.notEqual(fsfflMyTeamState.careerIntrinsic.status,'ready');
 // An unversioned view cannot borrow a newer publication's evidence.
 state.route='my_team';fsfflMyTeamState.view={context:{league_state_id:'A'}};
 await loadCareerIntrinsicForState('A');assert.equal(requests,18);
 assert.equal(myTeamCareerEstimate('p'),null);
 // Same-State but new publication must not reuse an old response.
 state.route='my_team';fsfflMyTeamState.view={...view,publication_generation_id:'g2'};
 api=async()=>({status:'ready',league_state_id:'A',publication_generation_id:'g1',estimates:[]});
 await loadCareerIntrinsicForState('A');
 assert.equal(fsfflMyTeamState.careerIntrinsic.status,'unavailable');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
    result = subprocess.run([node, "-e", prefix + harness], text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ready_three_year_render_does_not_wait_for_career_and_route_is_guarded():
    source = SOURCE.read_text()
    loader = source.split("async function loadFranchiseNorthStarValueLenses", 1)[1].split("async function loadFranchiseNorthStar()", 1)[0]
    assert "void loadCareerIntrinsicForState" in loader
    assert "await careerPromise" not in loader
    render = source.split("function renderFranchiseNorthStar(){", 1)[1]
    assert "if(state?.route!=='my_team')return;" in render[:100]


def test_simulation_outlook_labels_current_and_retained_evidence_honestly():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is required for the browser lifecycle harness')
    source = SOURCE.read_text()
    functions = source.split('function franchiseNSOutcome(){',1)[1].split('function franchiseNSCurrentContract(){',1)[0]
    script = "function franchiseNSOutcome(){" + functions
    script += r"""
const assert=require('node:assert/strict');
const state={context:{state_id:'new',publication_generation_id:'g1',capability_readiness:{simulation:{status:'full'}}}};
const fsfflMyTeamState={view:{context:{league_state_id:'new'},publication_generation_id:'g1',utility:{competitive_outcome:{expected_wins:7.5}}}};
assert.equal(franchiseNSSimulationPresentation().status,'current');
fsfflMyTeamState.view.publication_generation_id='g0';
assert.equal(franchiseNSSimulationPresentation().status,'retained');
fsfflMyTeamState.view.publication_generation_id='g1';
fsfflMyTeamState.view.presentation_continuity={served_league_state_id:'old'};
assert.equal(franchiseNSSimulationPresentation().status,'retained');
fsfflMyTeamState.view.presentation_continuity={served_league_state_id:'new'};
state.context.capability_readiness.simulation.status='unavailable';
assert.equal(franchiseNSSimulationPresentation().status,'retained');
assert.equal(franchiseNSSimulationPresentation().ready,true);
fsfflMyTeamState.view.utility.competitive_outcome=null;
assert.equal(franchiseNSSimulationPresentation().status,'unavailable');
"""
    result = subprocess.run([node, '-e', script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
