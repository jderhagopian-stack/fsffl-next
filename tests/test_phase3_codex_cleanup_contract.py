from pathlib import Path


def test_home_stays_presentation_only_after_north_star_recomposition() -> None:
    home = Path("src/fsffl/product/static/home_dashboard.js").read_text()
    opportunities = Path("src/fsffl/product/static/opportunities.js").read_text()
    workspace = Path("src/fsffl/product/opportunity_workspace.py").read_text()

    assert "api('/api/home')" in home
    shell = Path("src/fsffl/product/static/product_shell.js").read_text()
    assert "api('/api/intelligence/status')" not in home
    assert "api('/api/intelligence/status')" in shell
    assert home.count("api(") == 1
    assert "most_promising_evaluated" not in home
    assert "/api/opportunities/workspace" not in home
    runtime = Path("src/fsffl/product/market_discovery_runtime.py").read_text()
    assert "DEFAULT_PRELIMINARY_DECISION_BUDGET = 2" in runtime
    assert "bilateral_evaluation_limit: int = DEFAULT_PRELIMINARY_DECISION_BUDGET" in workspace
    assert "build_market_discovery" in workspace
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


def test_behavioral_runtime_schema_validation_is_read_only_and_migration_owned() -> None:
    source = Path("src/fsffl/behavioral/postgres_store.py").read_text()
    lowered = source.lower()

    # Ordinary hosted runtime validates the governed schema; it never creates or
    # repairs schema/index/RLS state itself.
    assert "pg_class" in source
    assert "relrowsecurity" in source
    assert "to_regclass('fsffl.behavior_event_family_time_idx')" in source
    assert "missing=" in source
    assert "rls_disabled=" in source
    assert "apply governed migrations before serving traffic" in source
    assert "_RLS_BOOTSTRAP_LOCK" not in source
    assert "_RLS_BOOTSTRAPPED_DATABASE_URLS" not in source
    assert "create schema" not in lowered
    assert "create table" not in lowered
    assert "create index" not in lowered
    assert "alter table" not in lowered
    assert "drop table" not in lowered
    assert "drop index" not in lowered
