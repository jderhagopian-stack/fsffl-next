from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_interactive_opportunity_workspace_bounds_fast_decision_work_and_defers_simulation() -> None:
    workspace = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    analysis = (ROOT / "src/fsffl/product/trade_analysis_runtime.py").read_text()

    runtime = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    assert "DEFAULT_PRELIMINARY_DECISION_BUDGET = 8" in runtime
    assert "bilateral_evaluation_limit: int = DEFAULT_PRELIMINARY_DECISION_BUDGET" in workspace
    assert "bounded_family_first_pre_simulation_decision_screen" in workspace
    assert "Representative Candidate Paths receive the existing pre-Simulation" in workspace
    assert "changed-state Simulation remains behind explicit transaction-level escalation" in workspace
    assert '"competitive_outcomes": False' in analysis
    assert "until the post-trade state is run through Simulation authority" in analysis


def test_opportunity_posture_observer_cannot_rewrite_its_own_dom_recursively() -> None:
    source = (ROOT / "src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    assert "requestAnimationFrame(renderSafely)" in source
    assert "observer.disconnect()" in source
    assert "if(control.innerHTML===markup)return" in source
    assert "new MutationObserver(()=>queueRender())" in source
    assert "new MutationObserver(renderControl)" not in source
