from pathlib import Path
import shutil
import subprocess

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
    assert "Owner dossier" in dossier
    assert "Start with what the completed record shows" in dossier


def test_owner_dossier_keeps_behavioral_authority_boundaries_explicit() -> None:
    source = _text("behavioral_intelligence.js")
    assert "not as a permanent preference label" in source
    assert "does not turn this record into acceptance odds" in source
    assert "Team/Owner-Adjusted Value" in source
    assert "Acceptance probability" in source
    assert "Not estimable" in source
    assert "Universal FSFFL Market Value remains unchanged" in source
    assert "cannot rewrite Value or Decision truth" in source
    assert "acceptance_probability" not in source


def test_owner_dossier_demotes_raw_counts_into_secondary_disclosure() -> None:
    source = _text("behavioral_intelligence.js")
    assert 'class="panel behavior-activity-evidence"' in source
    assert "<summary>Activity counts & supporting evidence</summary>" in source
    assert "Counts support the observed record; they are not a strategy score" in source


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
    assert "'20260920-owner-dossier1'" in shell
    assert "const fsfflBehaviorUiVersion='20260920-owner-dossier1'" in source


def test_owner_dossier_browser_script_parses() -> None:
    result = subprocess.run(
        [_node(), "--check", str(STATIC / "behavioral_intelligence.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
