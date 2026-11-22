from pathlib import Path
import shutil
import subprocess
import json
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "fsffl" / "product" / "static"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed in this test environment")
    return node


def test_owner_dossier_leads_with_observed_patterns_not_count_grid() -> None:
    source = _text("behavioral_intelligence.js")
    dossier_start = source.index("function fsfflBehaviorDossier")
    dossier_end = source.index("function fsfflBehaviorShell", dossier_start)
    dossier = source[dossier_start:dossier_end]

    assert "fsfflBehaviorScan(profile)" in dossier
    assert "fsfflBehaviorActivityEvidence(profile)" in dossier
    assert dossier.index("fsfflBehaviorScan(profile)") < dossier.index(
        "fsfflBehaviorActivityEvidence(profile)"
    )
    assert "Owner history" in dossier
    assert dossier.index("fsfflBehaviorHistoryCases(profile)") < dossier.index("fsfflBehaviorScan(profile)")


def test_owner_dossier_keeps_unavailable_inference_out_of_the_rendered_product() -> None:
    html = _render_dossier({"owner_id":"owner","as_of":"2026-11-17T00:00:00Z","historical_trade_cases":[
        {"completed_at":"2026-10-01T00:00:00Z","sent":["Receiver A"],"received":["2027 Round 1"],
         "context_sentences":["They were 6–2 through Week 8."],"situation":"6–2 through Week 8"}]})
    assert "Receiver A" in html and "They were 6–2 through Week 8." in html
    assert "Acceptance probability</strong>" not in html
    assert "What FSFFL can" not in html
    assert "Team/Owner-Adjusted Value" not in html
    assert html.index("Past decisions, in context") < html.index("Trading history at a glance")
    source = _text("behavioral_intelligence.js")
    assert "acceptance_probability" not in source


def test_owner_dossier_demotes_raw_counts_into_secondary_disclosure() -> None:
    source = _text("behavioral_intelligence.js")
    assert 'class="panel behavior-activity-evidence"' in source
    assert "<summary>Activity counts & supporting evidence</summary>" in source
    assert "Trading history at a glance" in source


def test_owner_dossier_uses_existing_observed_evidence_only() -> None:
    source = _text("behavioral_intelligence.js")
    assert "fsfflBehaviorCompletedShape(profile)" in source
    assert "fsfflBehaviorTopEntry(profile?.acquired_positions)" in source
    assert "fsfflBehaviorTopEntry(profile?.disposed_positions)" in source
    assert "fsfflBehaviorTopEntry(profile?.counterparty_trade_counts)" in source
    assert "profile?.seasons_observed" in source


def test_owner_dossier_is_mobile_first() -> None:
    css = _text("behavioral_intelligence.css")
    assert ".behavior-scan-signals{display:grid;grid-template-columns:repeat(4" in css
    assert "@media(max-width:760px)" in css
    assert ".behavior-scan-signals{grid-template-columns:1fr}" in css
    assert ".behavior-grid{grid-template-columns:1fr}" in css


def test_behavioral_lazy_asset_has_current_release_token() -> None:
    shell = _text("product_shell.js")
    source = _text("behavioral_intelligence.js")
    assert "'20260924-live-usability-hotfix1'" in shell
    script_version = re.search(r"const fsfflBehaviorUiVersion='([^']+)'", source).group(1)
    shell_version = re.search(r"const ownerHistoryStaticVersion='([^']+)'", shell).group(1)
    assert script_version == shell_version
    loader = shell.split("function ensureBehavioralIntelligenceScript()",1)[1].split("\n",1)[0]
    assert "ownerHistoryStaticVersion" in loader
    assert "c=contextual-owner-20261122" in _text("index.html")


def test_owner_dossier_browser_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "behavioral_intelligence.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _render_dossier(profile):
    code = r"""
const fs=require('fs'),vm=require('vm');
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const context=vm.createContext({window:{},state:{context:{}},escapeHtml});
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
context.supplied=JSON.parse(process.argv[2]);
process.stdout.write(vm.runInContext('fsfflBehaviorDossier(supplied)',context));
"""
    result = subprocess.run([_node(),"-e",code,str(STATIC/"behavioral_intelligence.js"),json.dumps(profile)],
        capture_output=True,text=True,check=True)
    return result.stdout


def test_owner_case_names_and_narrative_are_escaped_in_actual_renderer():
    html = _render_dossier({"owner_id":"owner","current_team_name":"<script>bad()</script>",
        "historical_trade_cases":[{"completed_at":"2026-10-01T00:00:00Z","sent":["<img src=x onerror=bad()>"],
            "received":["2027 Round 1"],"context_sentences":["<script>bad()</script>"]}]})
    assert "<script>" not in html and "<img " not in html
    assert "&lt;img " in html and "&lt;script&gt;" in html
