from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/trade_simulation_runtime.py"


def test_post_trade_simulation_uses_existing_authoritative_contracts() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "apply_bilateral_trade" in source
    assert "resolve_mandatory_roster_cuts" in source
    assert "simulation_loader(legal_after, forecast_evidence)" in source
    assert "compare_team_utility_vectors" in source
    assert '"mandatory_roster_cuts": "NEXT-5 Trade Decision"' in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"scenario_delta": "NEXT-4 Team Utility"' in source
    assert '"presentation_calculation": False' in source


def test_post_trade_simulation_requires_baseline_forecast_and_simulation_evidence() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "requires current NEXT-2 forecast evidence" in source
    assert "requires a current NEXT-4 baseline simulation" in source
    assert "focal team must be one side of the trade" in source


def test_post_trade_simulation_does_not_import_value_search_or_presentation_logic() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "fsffl.value" not in source
    assert "fsffl.opportunity" not in source
    assert "acceptance_probability" not in source
    assert "recommendation" not in source.lower()
