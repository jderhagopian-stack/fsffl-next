from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/trade_simulation_runtime.py"


def test_post_trade_simulation_uses_existing_authoritative_contracts() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "apply_bilateral_trade" in source
    assert "resolve_mandatory_roster_cuts" in source
    assert "run_progressive_scenario_simulation(" in source
    assert "simulation_loader=simulation_loader" in source
    assert "compare_counterfactual_simulation_results" in source
    assert "competitive_delta_a=simulation_delta_a" in source
    assert "competitive_delta_b=simulation_delta_b" in source
    assert "compare_team_utility_vectors" in source
    assert '"simulation_counterfactual_deltas"' in source
    assert '"mandatory_roster_cuts": "NEXT-5 Trade Decision"' in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"competitive_delta": "NEXT-4 Simulation common-world comparison when replay/topology coordinates match"' in source
    assert '"scenario_delta": "NEXT-4 Team Utility consumes Simulation competitive delta and adds non-competitive channels"' in source
    assert '"scenario_cache": "performance-only exact-result reuse"' in source
    assert '"scenario_computation"' in source
    assert "if computation.authoritative:" in source
    assert '"non_authoritative_scenario_preview"' in source
    assert '"final_trade_disposition": decision_complete and computation.authoritative' in source
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
