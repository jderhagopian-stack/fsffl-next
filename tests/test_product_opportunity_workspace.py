from pathlib import Path

from fastapi.testclient import TestClient

from fsffl.product.webapp import app


ROOT = Path(__file__).resolve().parents[1]


def test_opportunity_api_exposes_readiness_without_transport_failure() -> None:
    response = TestClient(app).get("/api/opportunities/workspace")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_league"
    assert payload["retryable"] is False
    assert payload["trade_discovery"]["candidates"] == []
    assert payload["authority"]["recommendation_authority"] is False


def test_waiver_action_endpoint_fails_closed_without_runtime_context() -> None:
    response = TestClient(app).post(
        "/api/opportunities/waiver",
        json={"add_player_id": "free-agent", "drop_player_id": None},
    )
    assert response.status_code == 409
    assert "No league is loaded" in response.json()["detail"]


def test_opportunity_search_uses_authoritative_cardinal_value_only() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    assert "values.fsffl_cardinal_values" in source
    assert '"action_authority": "diagnostic_only"' in source
    assert '"unknown_acceptance"' in source
    assert '"materiality_not_evaluated"' in source
    assert '"recommendation_authority": False' in source
    assert 'status="building_intelligence"' in source
    assert 'status="blocked"' in source
    assert "provisional_fsffl_values" not in source


def test_opportunity_presentation_retries_runtime_readiness_without_inventing_authority() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunities.js").read_text()
    shell = (ROOT / "src/fsffl/product/static/product_shell.js").read_text()
    assert "/api/opportunities/workspace" in ui
    assert "building_intelligence" in ui
    assert "setTimeout(()=>loadOpportunityWorkspace" in ui
    assert "This view will check again automatically" in ui
    assert "Diagnostic only" in ui
    assert "create a recommendation" in ui
    assert "acceptance percentage" in ui
    assert "renderFsfflOpportunities" in shell
    assert "opportunities.js" in shell
    assert "'opportunities','analytics'" in shell


def test_opportunity_waiver_ui_requires_server_action_authority() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunities.js").read_text()
    webapp = (ROOT / "src/fsffl/product/webapp.py").read_text()
    assert "/api/opportunities/waiver" in ui
    assert "/api/opportunities/waiver" in webapp
    assert "build_actionable_waiver_comparison" in webapp
    assert "simulation_loader=simulation_loader" in webapp
    assert "Evaluate waiver move" in ui
    assert "scenario_simulation_count" in ui
    assert "material_assessment" in ui
    assert "action_authority==='actionable'" in ui
    assert "State, Value, Simulation and materiality remain server-owned" in ui
    assert "acceptance_probability" not in ui
