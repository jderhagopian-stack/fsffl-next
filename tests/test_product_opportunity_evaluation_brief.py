from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_evaluation_brief_loads_after_triage_with_same_static_version():
    html = (STATIC / "index.html").read_text()
    assert html.index('/static/opportunity_evaluation_brief.js?v=') > html.index('/static/opportunity_decision_triage.js?v=')


def test_evaluation_brief_answers_three_primary_user_questions():
    source = (STATIC / "opportunity_evaluation_brief.js").read_text()
    assert "What is attractive" in source
    assert "What is stopping it" in source
    assert "What to do next" in source
    assert "Worth taking to Trade Center" in source
    assert "Restructure the package" in source
    assert "Keep searching" in source
    assert "Treat this as unresolved" in source


def test_evaluation_brief_only_interprets_returned_governed_evidence():
    source = (STATIC / "opportunity_evaluation_brief.js").read_text()
    assert "team_deltas" in source
    assert "candidate.reasons" in source
    assert "result?.negotiation?.shape" in source
    assert "result?.disposition?.disposition" in source
    assert "result?.action_authority" in source
    assert "api('/api/" not in source
    assert "fetch(" not in source
    assert "does not rerank Search" in source
    assert "invent acceptance odds" in source


def test_evaluation_brief_supports_lazy_opportunities_lifecycle():
    source = (STATIC / "opportunity_evaluation_brief.js").read_text()
    assert "window.installFsfflOpportunityEvaluationBrief=install" in source
    assert "new MutationObserver" in source
    assert "includes('/static/opportunities.js')" in source
    assert "node.addEventListener('load'" in source
