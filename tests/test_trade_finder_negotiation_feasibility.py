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
    assert '"acceptance_probability": None' in source
    assert '"recommendation_authority": False' in source
    assert '"negotiation_feasibility_is_not_acceptance_probability": True' in source
    assert "Feasibility describes calculated bilateral consequences" in source
