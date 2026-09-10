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

    assert "waiverSequence:0" in opportunities
    assert "tradeSequence:0" in opportunities
    assert "actionSequence:0" not in opportunities
    assert "oppWaiverContextIsCurrent" in opportunities
    assert "oppTradeContextIsCurrent" in opportunities
    assert "actionId=++fsfflOpportunityState.waiverSequence" in opportunities
    assert "actionId=++fsfflOpportunityState.tradeSequence" in opportunities
    assert "fsfflOpportunityState.waiverSequence+=1" in opportunities
    assert "fsfflOpportunityState.tradeSequence+=1" in opportunities
    assert "fsfflOpportunityState.waiverLoading=false" in opportunities
    assert "fsfflOpportunityState.tradeEvaluationLoading=false" in opportunities
    assert "fsfflOpportunityState.tradeEvaluationKey=null" in opportunities
    assert "if(state?.route==='opportunities'){oppLoading();" in opportunities


def test_behavioral_rls_bootstrap_is_process_once_and_retryable_on_failure() -> None:
    source = Path("src/fsffl/behavioral/postgres_store.py").read_text()

    assert "_RLS_BOOTSTRAP_LOCK = Lock()" in source
    assert "_RLS_BOOTSTRAPPED_DATABASE_URLS: set[str] = set()" in source
    assert "if self._database_url not in _RLS_BOOTSTRAPPED_DATABASE_URLS:" in source
    assert "_RLS_BOOTSTRAPPED_DATABASE_URLS.add(self._database_url)" in source
    assert source.index("cursor.execute(f\"alter table fsffl.{table_name} enable row level security\")") < source.index("_RLS_BOOTSTRAPPED_DATABASE_URLS.add(self._database_url)")
