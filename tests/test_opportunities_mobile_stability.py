from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_interactive_opportunity_workspace_bounds_fast_decision_work_and_defers_simulation() -> None:
    workspace = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    analysis = (ROOT / "src/fsffl/product/trade_analysis_runtime.py").read_text()

    assert "bilateral_evaluation_limit: int = 1" in workspace
    assert "bounded_lead_evaluation_for_interactive_workspace" in workspace
    assert "one bounded server-owned bilateral Decision" in workspace
    assert "Full changed-state Decision and Simulation remain behind the explicit Evaluate offer" in workspace
    assert '"competitive_outcomes": False' in analysis
    assert "until the post-trade state is run through Simulation authority" in analysis


def test_opportunity_posture_observer_cannot_rewrite_its_own_dom_recursively() -> None:
    source = (ROOT / "src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "requestAnimationFrame(renderSafely)" in source
    assert "observer.disconnect()" in source
    assert "if(control.innerHTML===markup)return" in source
    assert "new MutationObserver(()=>queueRender())" in source
    assert "new MutationObserver(renderControl)" not in source
