from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src/fsffl/product/waiver_action_runtime.py"


def test_waiver_action_runtime_joins_existing_authorities() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "build_waiver_simulation_comparison" in source
    assert "live_bounded_materiality_policy" in source
    assert "assess_waiver_materiality" in source
    assert "candidate_from_waiver_evaluation" in source
    assert '"market_value": "NEXT-3 Value authoritative Cardinal score"' in source
    assert '"competitive_outcomes": "NEXT-4 Simulation"' in source
    assert '"waiver_action": "NEXT-6 Opportunity candidate authority"' in source


def test_waiver_action_runtime_requires_complete_changed_state_evidence() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "competitive.expected_wins" in source
    assert "competitive.playoff_probability" in source
    assert "competitive.championship_probability" in source
    assert "resilience.largest_single_player_lineup_drop" in source
    assert "delta.asset_portfolio.mean_value" in source
    assert "EvidenceCompleteness.COMPLETE if _complete(delta) else EvidenceCompleteness.PARTIAL" in source


def test_waiver_action_runtime_uses_cardinal_delta_without_new_score() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "mean_delta = add.score - (drop.score if drop is not None else 0.0)" in source
    assert "presentation_calculation\": False" in source
    assert "master_score" not in source
    assert "acceptance_probability" not in source
    assert "multiplier" not in source
