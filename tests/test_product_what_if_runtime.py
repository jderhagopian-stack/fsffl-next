from pathlib import Path

from fastapi.testclient import TestClient

from fsffl.product.webapp import app


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/what_if_runtime.py"
UI = ROOT / "src/fsffl/product/static/what_if.js"
SHELL = ROOT / "src/fsffl/product/static/product_shell.js"


def test_player_unavailable_what_if_reuses_state_and_simulation_authority() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"scenario_kind": "player_unavailable"' in source
    assert '"slot": RosterSlot.IR' in source
    assert "run_cached_scenario_simulation(" in source
    assert "simulation_loader=simulation_loader" in source
    assert "compare_team_utility_vectors" in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"scenario_delta": "NEXT-4 Team Utility"' in source
    assert '"scenario_cache": "performance-only exact-result reuse"' in source


def test_player_unavailable_what_if_preserves_ownership_and_does_not_revalue() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"value": "unchanged; ownership is preserved"' in source
    assert '"presentation_calculation": False' in source
    assert "apply_bilateral_trade" not in source
    assert "apply_waiver_move" not in source
    assert "cardinal" not in source.lower()
    assert "threshold" not in source.lower()


def test_player_unavailable_what_if_fails_closed_without_authoritative_prerequisites() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "Simulator requires a loaded league state" in source
    assert "Simulator requires a selected franchise" in source
    assert "Simulator requires current NEXT-2 forecast evidence" in source
    assert "Simulator requires a current NEXT-4 baseline simulation" in source
    assert "Simulator players must be rostered by the selected franchise" in source


def test_player_unavailable_endpoint_fails_closed_without_runtime_context() -> None:
    response = TestClient(app).post(
        "/api/what-if/player-unavailable",
        json={"player_id": "player:test"},
    )
    assert response.status_code == 409
    assert "loaded league state" in response.json()["detail"]


def test_what_if_ui_invokes_server_scenario_and_only_presents_returned_deltas() -> None:
    ui = UI.read_text(encoding="utf-8")
    shell = SHELL.read_text(encoding="utf-8")
    webapp = (ROOT / "src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    assert "/api/what-if/player-unavailable" in ui
    assert "/api/what-if/player-unavailable" in webapp
    assert "build_player_unavailable_scenario" in webapp
    assert "Run What-If" in ui
    assert "50,000-run stress test" in ui
    assert "Ownership and FSFFL Value are unchanged" in ui
    assert "Browser calculation: none" in ui
    assert "ensureWhatIfScript" in shell
    assert "what_if.js" in shell
    assert "window.renderFsfflWhatIf" in ui
    assert "acceptance_probability" not in ui
