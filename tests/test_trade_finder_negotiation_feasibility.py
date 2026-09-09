from pathlib import Path


def test_fast_trade_analysis_uses_decision_owned_negotiation_feasibility() -> None:
    source = Path("src/fsffl/product/trade_analysis_runtime.py").read_text(encoding="utf-8")

    assert "assess_negotiation_feasibility" in source
    assert "negotiation_feasibility = assess_negotiation_feasibility" in source
    assert 'acceptance=None' in source
    assert '"negotiation_feasibility"' in source
    assert '"acceptance_probability": False' in source
    assert "not an acceptance probability" in source


def test_trade_finder_surfaces_feasibility_without_inventing_acceptance() -> None:
    source = Path("src/fsffl/product/opportunity_workspace.py").read_text(encoding="utf-8")

    assert 'analysis.get("negotiation_feasibility")' in source
    assert '"negotiation_feasibility_shape": feasibility.get("shape")' in source
    assert '"negotiation_feasibility_evaluated": bool(feasibility)' in source
    assert '"acceptance_probability": None' in source
    assert '"recommendation_authority": False' in source
    assert '"negotiation_feasibility_is_not_acceptance_probability": True' in source


def test_trade_finder_presents_feasibility_in_plain_english_without_acceptance_odds() -> None:
    source = Path("src/fsffl/product/static/trade_finder_feasibility.js").read_text(encoding="utf-8")
    index = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")

    assert "mutual_gain_candidate:'Both sides show calculated gains'" in source
    assert "counterparty_dominated:'Other team takes a calculated loss'" in source
    assert "mixed:'Mixed bilateral impact'" in source
    assert "neutral:'Near-neutral bilateral impact'" in source
    assert "incomplete:'Decision evidence incomplete'" in source
    assert "negotiation_feasibility_evaluated" in source
    assert "negotiation_feasibility_shape" in source
    assert "not an acceptance probability" in source
    assert "acceptance_probability" not in source
    assert "trade_finder_feasibility.js" in index
    assert "ensureOpportunitiesScript" in shell
    assert "/static/opportunities.js" in shell
    assert '/static/opportunities.js?v=20260909-beta-feedback1' not in index
