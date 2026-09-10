from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text()


def test_home_reuses_governed_opportunity_workspace_without_deep_analysis() -> None:
    assert "api('/api/opportunities/workspace')" in HOME
    assert "most_promising_evaluated" in HOME
    assert "/api/trade-center/analyze" not in HOME
    assert "/api/trade-center/simulate" not in HOME
    assert "/api/opportunities/trade" not in HOME


def test_home_labels_opportunity_as_server_selected_not_acceptance_prediction() -> None:
    assert "server-selected Decision-evaluated lead" in HOME
    assert "not an acceptance prediction" in HOME


def test_home_keeps_no_lead_state_explicit_instead_of_fabricating_one() -> None:
    assert "No evaluated lead available" in HOME
    assert "FSFFL will not invent an opportunity" in HOME
