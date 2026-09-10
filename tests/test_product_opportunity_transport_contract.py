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


def test_posture_observer_is_scoped_to_opportunity_surface() -> None:
    source = Path("src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "observer.observe(screen,{subtree:true,childList:true})" in source
    assert "observer.observe(document.body" not in source
    assert "attributeFilter:['hidden','class']" not in source


def test_posture_transport_reuses_one_canonical_candidate_collection() -> None:
    server = Path("src/fsffl/product/opportunity_workspace.py").read_text()
    client = Path("src/fsffl/product/static/opportunity_posture_ui.js").read_text()

    assert '"candidate_indices": [index_by_identity[id(row)] for row in ordered]' in server
    assert '"candidates": ordered' not in server
    assert "candidate_indices" in client
    assert "canonical[index]" in client
    assert "view?.candidates" in client
