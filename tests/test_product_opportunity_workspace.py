from pathlib import Path

from fastapi.testclient import TestClient

from fsffl.product.opportunity_workspace import _select_bilateral_evaluation_indices
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


def test_trade_opportunity_endpoint_fails_closed_without_runtime_context() -> None:
    response = TestClient(app).post(
        "/api/opportunities/trade",
        json={
            "counterparty_team_id": "other-team",
            "focal_asset_refs": ["player:a"],
            "counterparty_asset_refs": ["player:b"],
        },
    )
    assert response.status_code == 409
    assert "No league is loaded" in response.json()["detail"]


def test_opportunity_search_uses_authoritative_cardinal_value_only() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    search = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()
    assert "values.fsffl_cardinal_values" in source
    assert '"action_authority": "diagnostic_only"' in source
    assert '"unknown_acceptance"' in search
    assert '"materiality_not_evaluated"' in search
    assert '"recommendation_authority": False' in source
    assert 'status="building_intelligence"' in source
    assert 'status="blocked"' in source
    assert "provisional_fsffl_values" not in source
    assert "provisional_fsffl_values" not in search


def test_opportunity_search_is_roster_aware_and_not_just_nearest_one_for_one_value() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()
    workspace = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()
    assert "for row in view.position_strengths" in source
    assert "build_league_relative_position_strengths" not in source
    assert "focal_position_strength_rank" in source
    assert "focal_position_strength_index" in source
    assert "counterparty_receive_position_rank" in source
    assert "counterparty_receive_position_strength_index" in source
    assert '"package_shape": shape' in source
    assert '"two_for_one"' in source
    assert "combinations(valued_focal, 2)" in source
    assert "Lexicographic, explainable ordering" in source
    assert "composite_score" not in source
    assert "opportunity_score" not in source
    assert "build_roster_aware_trade_candidates" in workspace
    assert '"roster_aware_search": runtime.simulation_analytics is not None' in workspace
    assert '"two_for_one_consolidation_search": True' in workspace
    assert '"search_order_is_not_a_composite_opportunity_score": True' in workspace


def test_decision_budget_preserves_best_market_candidate_and_diversifies_counterparties() -> None:
    rows = [
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a1"}]},
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a2"}]},
        {"counterparty_team_id": "b", "receive": [{"asset_ref": "player:b1"}]},
        {"counterparty_team_id": "c", "receive": [{"asset_ref": "player:c1"}]},
        {"counterparty_team_id": "d", "receive": [{"asset_ref": "player:d1"}]},
    ]
    assert _select_bilateral_evaluation_indices(rows, limit=4) == (0, 2, 3, 4)


def test_decision_budget_uses_distinct_targets_before_duplicate_fill() -> None:
    rows = [
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a1"}]},
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a1"}]},
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a2"}]},
        {"counterparty_team_id": "a", "receive": [{"asset_ref": "player:a3"}]},
    ]
    assert _select_bilateral_evaluation_indices(rows, limit=3) == (0, 2, 3)


def test_opportunity_presentation_retries_runtime_readiness_without_inventing_authority() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunities.js").read_text()
    shell = (ROOT / "src/fsffl/product/static/product_shell.js").read_text()
    assert "/api/opportunities/workspace" in ui
    assert "building_intelligence" in ui
    assert "setTimeout(()=>loadOpportunityWorkspace" in ui
    assert "This view will check again automatically" in ui
    assert "Diagnostic only" in ui
    assert "not an acceptance probability" in ui
    assert "Numeric acceptance" in ui and "separately calibrated" in ui
    assert "renderFsfflOpportunities" in shell
    assert "opportunities.js" in shell
    assert "'opportunities','what_if','simulator','analytics'" in shell


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


def test_trade_opportunity_ui_promotes_only_to_server_returned_market_test_authority() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunities.js").read_text()
    webapp = (ROOT / "src/fsffl/product/webapp.py").read_text()
    runtime = (ROOT / "src/fsffl/product/trade_opportunity_runtime.py").read_text()
    assert "/api/opportunities/trade" in ui
    assert "/api/opportunities/trade" in webapp
    assert "build_trade_opportunity_evaluation" in webapp
    assert "build_post_trade_simulation_comparison" in runtime
    assert "candidate_from_trade_evaluation" in runtime
    assert "EvidenceCompleteness.COMPLETE" in runtime
    assert "acceptance=None" in runtime
    assert "MARKET_TEST_ONLY" in runtime
    assert "Evaluate offer" in ui
    assert "Worth sending as a market test" in ui
    assert "acceptance is uncalibrated" in ui.lower()
    assert "cannot become ACTIONABLE" in ui
    assert "acceptance_probability" not in ui
