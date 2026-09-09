from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_interactive_opportunity_workspace_defers_deep_decision_work() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    assert "bilateral_evaluation_limit: int = 0" in source
    assert "explicit_evaluation_only_for_interactive_workspace" in source
    assert "Full changed-state Decision" in source


def test_opportunity_posture_observer_cannot_rewrite_its_own_dom_recursively() -> None:
    source = (ROOT / "src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "requestAnimationFrame(renderSafely)" in source
    assert "observer.disconnect()" in source
    assert "if(control.innerHTML===markup)return" in source
    assert "new MutationObserver(()=>queueRender())" in source
    assert "new MutationObserver(renderControl)" not in source
