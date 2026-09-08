from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BEHAVIOR = ROOT / "src/fsffl/product/behavioral_runtime.py"
FRONTIER = ROOT / "src/fsffl/product/frontier_runtime.py"


def test_behavior_runtime_resolves_stable_owner_profile_for_current_team() -> None:
    source = BEHAVIOR.read_text(encoding="utf-8")
    assert "def profile_for_team(" in source
    assert "current_owner_by_roster" in source
    assert "OwnerBehaviorProfile" in source
    assert "ref.provider == \"sleeper\"" in source
    assert "return None" in source


def test_negotiation_frontier_consumes_behavior_through_next5_evidence_contract() -> None:
    source = FRONTIER.read_text(encoding="utf-8")
    assert "counterparty_behavior_profile" in source
    assert "build_private_beta_trade_analysis" in source
    assert "counterparty_behavior_profile=counterparty_behavior_profile" in source
    assert '"behavioral_evidence": counterparty_behavior_profile is not None' in source
    assert '"acceptance_probability": False' in source
    assert '"market_value_rewritten": False' in source
