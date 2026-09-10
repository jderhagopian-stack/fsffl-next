from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text()


def test_home_reuses_already_loaded_governed_opportunity_workspace_without_api_work() -> None:
    assert "homeLoadedOpportunityWorkspace" in HOME
    assert "fsfflOpportunityState" in HOME
    assert "most_promising_evaluated" in HOME
    assert "api(" not in HOME
    assert "fetch(" not in HOME
    assert "/api/trade-center/analyze" not in HOME
    assert "/api/trade-center/simulate" not in HOME
    assert "/api/opportunities/trade" not in HOME


def test_home_labels_loaded_opportunity_as_server_selected_not_acceptance_prediction() -> None:
    assert "server-selected Decision-evaluated lead" in HOME
    assert "not an acceptance prediction" in HOME
    assert "Strongest evaluated path already loaded by Market" in HOME


def test_home_keeps_unloaded_and_no_lead_states_explicit_without_fabrication() -> None:
    assert "Scan the personalized market" in HOME
    assert "Market has not been opened in this session yet" in HOME
    assert "No evaluated lead stands out yet" in HOME
    assert "FSFFL will not invent an opportunity" in HOME
    assert "No fabricated recommendation" in HOME


def test_home_makes_the_governed_next_action_visually_dominant() -> None:
    assert "homePrimaryAction" in HOME
    assert "home-priority" in HOME
    assert "Work this opportunity" in HOME
    assert "Find my best moves" in HOME
