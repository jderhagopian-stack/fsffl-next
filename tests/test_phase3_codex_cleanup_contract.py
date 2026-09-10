from pathlib import Path


def test_home_stays_presentation_only_after_codex_cleanup() -> None:
    home = Path("src/fsffl/product/static/home_dashboard.js").read_text()
    opportunities = Path("src/fsffl/product/static/opportunities.js").read_text()
    workspace = Path("src/fsffl/product/opportunity_workspace.py").read_text()

    assert "api(" not in home
    assert "most_promising_evaluated" in home
    assert "bilateral_evaluation_limit: int = 1" in workspace
    assert "_evaluate_structural_trade" in workspace
    assert "oppContextKey" in opportunities
    assert "requestContext" in opportunities
    assert "currentContext!==requestContext" in opportunities
