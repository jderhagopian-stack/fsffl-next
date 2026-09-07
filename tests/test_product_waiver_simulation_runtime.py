from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/waiver_simulation_runtime.py"


def test_waiver_runtime_reuses_next6_state_and_next4_simulation() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "apply_waiver_move" in source
    assert "simulation_loader(changed_state, forecast_evidence)" in source
    assert "compare_team_utility_vectors" in source
    assert '"candidate_search": "NEXT-6 Opportunity"' in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source


def test_waiver_runtime_does_not_invent_materiality_or_ui_math() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert '"materiality": None' in source
    assert '"materiality_evaluated": False' in source
    assert '"presentation_calculation": False' in source
    assert "CompetitiveMaterialityPolicy(" not in source
    assert "threshold =" not in source
