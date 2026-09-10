from pathlib import Path


def test_home_stays_presentation_only_after_codex_cleanup() -> None:
    home = Path("src/fsffl/product/static/home_dashboard.js").read_text()
    opportunities = Path("src/fsffl/product/static/opportunities.js").read_text()
    workspace = Path("src/fsffl/product/opportunity_workspace.py").read_text()

    assert "api(" not in home
    assert "most_promising_evaluated" in home
    assert "bilateral_evaluation_limit: int = 1" in workspace
    assert "_evaluate_structural_trade" in workspace
    assert "oppContextSnapshot" in opportunities
    assert "oppPayloadMatchesCapturedContext" in opportunities
    assert "requestSequence" in opportunities
    assert "requestId!==fsfflOpportunityState.requestSequence" in opportunities
    assert "invalidateOpportunityWorkspaceContext" in opportunities


def test_opportunity_context_change_invalidates_inflight_actions_and_old_rows() -> None:
    opportunities = Path("src/fsffl/product/static/opportunities.js").read_text()

    assert "actionSequence:0" in opportunities
    assert "oppActionContextIsCurrent" in opportunities
    assert "actionId=++fsfflOpportunityState.actionSequence" in opportunities
    assert "fsfflOpportunityState.actionSequence+=1" in opportunities
    assert "fsfflOpportunityState.waiverLoading=false" in opportunities
    assert "fsfflOpportunityState.tradeEvaluationLoading=false" in opportunities
    assert "fsfflOpportunityState.tradeEvaluationKey=null" in opportunities
    assert "if(state?.route==='opportunities'){oppLoading();" in opportunities
