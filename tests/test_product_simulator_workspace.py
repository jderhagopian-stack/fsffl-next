from pathlib import Path

from fastapi.testclient import TestClient

from fsffl.product.webapp import app


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/what_if_runtime.py"
UI = ROOT / "src/fsffl/product/static/simulator.js"
SHELL = ROOT / "src/fsffl/product/static/product_shell.js"
INDEX = ROOT / "src/fsffl/product/static/index.html"


def test_simulator_runtime_builds_one_simultaneous_changed_state() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "build_players_unavailable_scenario" in source
    assert '"scenario_kind": "players_unavailable"' in source
    assert "item.player_id in selected" in source
    assert '"slot": RosterSlot.IR' in source
    assert "run_cached_scenario_simulation" in source
    assert '"scenario_cache_hit": cache_hit' in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"value": "unchanged; ownership is preserved"' in source
    assert '"presentation_calculation": False' in source


def test_simulator_transport_envelope_reuses_hosted_governed_endpoint() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    assert '_SIMULATOR_ENVELOPE_PREFIX = "simulator:"' in runtime
    assert "encoded.split(\",\")" in runtime
    assert "build_players_unavailable_scenario" in runtime
    assert "/api/what-if/player-unavailable" in ui
    assert "simulator:${playerIds.join(',')}" in ui
    assert "50,000-run Simulation" in ui
    assert "scenario_cache_hit" in ui
    assert "Ownership and FSFFL Value remain unchanged" in ui
    assert "acceptance_probability" not in ui


def test_simulator_compares_only_server_returned_scenarios_without_new_score() -> None:
    ui = UI.read_text(encoding="utf-8")
    assert "retainSimulatorScenario" in ui
    assert "history.slice(0,4)" in ui
    assert "Scenario comparison" in ui
    assert "server-returned deltas" in ui
    assert "browser does not create a winner score" in ui
    assert "no cross-scenario composite" in ui
    assert "team_delta?.competitive" in ui
    assert "composite_score" not in ui
    assert "master_score" not in ui


def test_simulator_is_first_class_team_scoped_product_route() -> None:
    shell = SHELL.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    assert "{route:'simulator',label:'Simulator',teamScoped:true}" in shell
    assert "ensureSimulatorScript" in shell
    assert "/static/simulator.js" in shell
    assert "route==='simulator'" in shell
    assert "'what_if','simulator','analytics'" in shell
    assert "20260907-simulator2" in shell
    assert "20260907-simulator2" in index


def test_simulator_endpoint_fails_closed_without_runtime_context() -> None:
    response = TestClient(app).post(
        "/api/what-if/player-unavailable",
        json={"player_id": "simulator:player:a,player:b"},
    )
    assert response.status_code == 409
    assert "loaded league state" in response.json()["detail"]
