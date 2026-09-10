from pathlib import Path


def test_posture_ui_does_not_intercept_global_fetch() -> None:
    source = Path("src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "window.fetch=" not in source
    assert "response.clone()" not in source
    assert "new Response(JSON.stringify" not in source
    assert "window.fsfflOpportunityPosture" in source


def test_opportunities_loader_applies_posture_without_response_rewrite() -> None:
    source = Path("src/fsffl/product/static/opportunities.js").read_text()
    assert "fsfflOpportunityPosture?.applyWorkspace" in source


def test_posture_views_publish_order_not_duplicate_candidates() -> None:
    source = Path("src/fsffl/product/opportunity_workspace.py").read_text()
    assert '"candidate_order"' in source
    assert '"candidates": ordered' not in source
