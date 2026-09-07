from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/frontier_runtime.py"


def test_frontier_runtime_reuses_next6_search_and_next5_decision() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "explore_negotiation_frontier" in source
    assert "build_team_trade_inventory" in source
    assert "build_private_beta_trade_analysis" in source
    assert "assess_negotiation_feasibility" in source
    assert "candidate_from_trade_evaluation" in source


def test_frontier_does_not_rewrite_market_value_or_invent_acceptance() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"acceptance_probability": False' in source
    assert '"materiality_evaluated": False' in source
    assert '"market_value_rewritten": False' in source
    assert "price =" not in source
    assert "acceptance_probability =" not in source


def test_frontier_search_bounds_are_exposed_not_hidden_model_coefficients() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"policy": policy.model_dump(mode="json")' in source
    assert '"bounds": bounds.model_dump(mode="json")' in source
    assert "max_depth=max_depth" in source
    assert "max_evaluations=max_evaluations" in source
