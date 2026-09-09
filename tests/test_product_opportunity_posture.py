from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_posture_ui_selects_only_server_owned_views() -> None:
    script = (ROOT / "src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    index = (ROOT / "src/fsffl/product/static/index.html").read_text()
    workspace = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()

    assert "const views=discovery&&discovery.posture_views" in script
    assert "fsffl.tradeFinderPosture" in script
    assert "This changes Trade Finder discovery order only" in script
    assert "opportunity_posture_ui.js?v=20260909-beta-feedback1" in index
    assert '"posture_views": posture_views' in workspace
    assert '"owner_strategic_posture_is_search_lens_only": True' in workspace
    assert '"browser_selects_server_owned_posture_views_only": True' in workspace
