from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_opportunity_decision_triage_is_loaded_with_coherent_static_version():
    html = (STATIC / "index.html").read_text()
    assert '/static/opportunity_decision_triage.js?v=20260909-beta-feedback1' in html


def test_triage_uses_existing_bilateral_shapes_without_new_score():
    source = (STATIC / "opportunity_decision_triage.js").read_text()
    assert "negotiation_feasibility_evaluated" in source
    assert "mutual_gain_candidate" in source
    assert "counterparty_dominated" in source
    assert "mixed" in source
    assert "neutral" in source
    assert "not_evaluated" in source
    assert "composite Opportunity score" in source
    assert "api('/api/" not in source
    assert "fetch(" not in source


def test_triage_preserves_existing_search_order_and_only_filters_presented_rows():
    source = (STATIC / "opportunity_decision_triage.js").read_text()
    assert "const originalOppTradeRows=oppTradeRows" in source
    assert "return triageFilter==='all'?rows:rows.filter" in source
    assert ".filter(row=>category(row)==='mutual_gain').slice(0,3)" in source
    assert "existing Search order" in source
    assert ".sort(" not in source


def test_triage_surfaces_plain_language_actionable_buckets_and_trade_handoff():
    source = (STATIC / "opportunity_decision_triage.js").read_text()
    assert "Both sides gain" in source
    assert "Needs restructuring" in source
    assert "Mixed / neutral" in source
    assert "Not fully evaluated" in source
    assert "Start here" in source
    assert "Work this deal" in source
    assert "fsfflOpenOpportunityInTradeCenter" in source
    assert "not an acceptance forecast" in source


def test_triage_installs_after_lazy_opportunities_script_loads():
    source = (STATIC / "opportunity_decision_triage.js").read_text()
    assert "window.installFsfflOpportunityDecisionTriage=installFsfflOpportunityDecisionTriage" in source
    assert "new MutationObserver" in source
    assert "includes('/static/opportunities.js')" in source
    assert "node.addEventListener('load'" in source
    assert "installFsfflOpportunityDecisionTriage();observer.disconnect()" in source
