from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/what_if_runtime.py"


def test_player_unavailable_what_if_reuses_state_and_simulation_authority() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"scenario_kind": "player_unavailable"' in source
    assert '"slot": RosterSlot.IR' in source
    assert "simulation_loader(changed_state, forecast_evidence)" in source
    assert "compare_team_utility_vectors" in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"scenario_delta": "NEXT-4 Team Utility"' in source


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
    assert "What-If requires a loaded league state" in source
    assert "What-If requires a selected franchise" in source
    assert "What-If requires current NEXT-2 forecast evidence" in source
    assert "What-If requires a current NEXT-4 baseline simulation" in source
    assert "What-If player must be rostered by the selected franchise" in source
