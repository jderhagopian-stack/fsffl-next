from pathlib import Path
import hashlib
import shutil
import subprocess

import pytest


def test_franchise_card_bundle_and_loader_have_content_specific_cache_keys():
    static = Path(__file__).parents[1] / "src/fsffl/product/static"

    def blob_prefix(name):
        data = (static / name).read_bytes()
        return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()[:12]

    assert f"const franchiseNorthStarStaticVersion='20261007-franchise-{blob_prefix('my_team_dashboard.js')}';" in (static / "product_shell.js").read_text()
    assert f"product_shell.js?v=20261004-safari-restore380&c=git-{blob_prefix('product_shell.js')}" in (static / "index.html").read_text()


def test_franchise_presents_separate_indexes_and_retains_raw_career():
    source = (
        Path(__file__).parents[1]
        / "src/fsffl/product/static/my_team_dashboard.js"
    ).read_text(encoding="utf-8")

    assert "3-Year Intrinsic Index (0–10,000)" in source
    assert "Career Intrinsic Index (0–10,000)" in source
    assert "3-Year Intrinsic · 0–10,000 index" in source
    assert "Career Intrinsic · 0–10,000 index" in source
    assert "career_intrinsic_index" in source
    assert "intrinsic_value_index" in source
    assert "api('/api/value/career-intrinsic-v1?'+query)" in source
    assert "payload?.league_state_id&&payload.league_state_id!==expectedStateId" in source
    assert "if(!myTeamCareerMatchesView(payload))" in source


def test_roster_card_separates_three_indexes_and_raw_career_on_mobile():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the production card harness")
    source = (Path(__file__).parents[1] / "src/fsffl/product/static/my_team_dashboard.js").read_text()
    prefix = source.split("function myTeamIntrinsic(id)", 1)[0]
    career = "function franchiseNSCareerDisplay(player){" + source.split("function franchiseNSCareerDisplay(player){", 1)[1].split("function franchiseNSProjectedStarter", 1)[0]
    row = "function franchiseNSPlayerRow(player){" + source.split("function franchiseNSPlayerRow(player){", 1)[1].split("function franchiseNSRankedAssets", 1)[0]
    harness = r"""
const assert=require('node:assert/strict');
const franchiseNSPpg=()=>12,franchiseNSSeasonProjection=()=>204;
const franchiseNSPlayerRole=()=> 'Bench';
const franchiseNSMarketDisplay=()=>'<strong>4,000</strong><small>40th pct</small>';
const franchiseNSIntrinsicDisplay=()=>'<strong>5,000</strong><small>50th pct</small>';
fsfflMyTeamState.view={context:{league_state_id:'A'},publication_generation_id:'g1'};
fsfflMyTeamState.careerIntrinsic={status:'ready',league_state_id:'A',publication_generation_id:'g1',estimates:[{player_id:'p',career_intrinsic_index:6789,raw_career_forward_reference:123.45}]};
const html=franchiseNSPlayerRow({player_id:'p',full_name:'A very long player name',position:'WR',age_years:23});
assert.equal((html.match(/class="franchise-ns-player-value /g)||[]).length,3);
assert.match(html,/class="franchise-ns-player-value career"[^>]*><small>Career Intrinsic<\/small><strong>6,789<\/strong><small>Raw Career 123.5<\/small>/);
assert.doesNotMatch(html,/<strong>[^<]*<small>/);
fsfflMyTeamState.careerIntrinsic.estimates[0].career_input_assumption='Low confidence: YTD-only <assumption>';
assert.match(franchiseNSCareerDisplay({player_id:'p'}),/Low confidence: YTD-only &lt;assumption&gt;/);
fsfflMyTeamState.careerIntrinsic.player_coverage_failures={q:'No admissible <projection>'};
const missing=franchiseNSCareerDisplay({player_id:'q'});
assert.match(missing,/Unavailable<\/strong>/);assert.match(missing,/No admissible &lt;projection&gt;/);
assert.doesNotMatch(missing,/Raw Career 0/);
fsfflMyTeamState.view.publication_generation_id='g2';
assert.doesNotMatch(franchiseNSCareerDisplay({player_id:'p'}),/6,789|123.5/);
"""
    result = subprocess.run([node, "-e", prefix + career + row + harness], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'grid-template-areas:"id ppg proj" "values values values"' in source
    assert '.franchise-ns-player-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))' in source
    assert '.franchise-ns-player-values{grid-area:values;' in source
    assert '"market market intrinsic"' not in source


def test_dynasty_reports_actual_complete_room_counts_without_fabricating_ranks():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for the production chart harness")
    source = (Path(__file__).parents[1] / "src/fsffl/product/static/league_comparison.js").read_text()
    function = "function laDynastyCoverageSummary(){" + source.split("function laDynastyCoverageSummary(){", 1)[1].split("function laRosterBreadth", 1)[0]
    harness = r"""
const assert=require('node:assert/strict');
const fsfflLeagueStructureState={dynastyRooms:{dynasty_rank_readiness:{coverage:{QB:{coverage_count:6,team_count:12},RB:{coverage_count:12,team_count:12},WR:{coverage_count:4,team_count:12},TE:{coverage_count:10,team_count:12}}}}};
assert.equal(laDynastyCoverageSummary(),'QB 6/12 complete rooms · RB 12/12 complete rooms · WR 4/12 complete rooms · TE 10/12 complete rooms');
fsfflLeagueStructureState.dynastyRooms=null;assert.equal(laDynastyCoverageSummary(),'');
"""
    result = subprocess.run([node, "-e", function + harness], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Each position is ranked once all its team rooms are complete" in source
    assert "if(!row.evidence_complete||typeof row.league_rank!=='number')" in source
