from pathlib import Path


def test_posture_ui_does_not_intercept_global_fetch() -> None:
    source = Path("src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "window.fetch=" not in source
    assert "response.clone()" not in source
    assert "new Response(JSON.stringify" not in source
    assert "window.fsfflOpportunityPosture" in source


def test_posture_switch_reuses_loaded_workspace() -> None:
    source = Path("src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "applyCurrentWorkspace" in source
    assert "fsfflOpportunityState.payload=updated" in source
    assert "renderOpportunityWorkspace" in source
