from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIT = ROOT / "src/fsffl/product/behavioral_fit_runtime.py"
TRADE = ROOT / "src/fsffl/product/trade_opportunity_runtime.py"
UI = ROOT / "src/fsffl/product/static/opportunities.js"
RUNTIME = ROOT / "src/fsffl/product/behavioral_runtime.py"


def test_behavioral_fit_uses_observed_history_and_current_context_without_probability() -> None:
    source = FIT.read_text(encoding="utf-8")
    assert "counterparty_profile.consolidation_trade_count" in source
    assert "counterparty_profile.acquired_pick_count" in source
    assert "counterparty_profile.acquired_positions" in source
    assert "calculated_competitive_state" in source
    assert "counterparty_trade_counts" in source
    assert "BehavioralEvidenceLevel.INFERRED" in source
    assert "acceptance_probability" not in source
    assert "calibration_model_version" not in source


def test_behavioral_fit_is_advisory_and_does_not_rewrite_trade_authority() -> None:
    source = TRADE.read_text(encoding="utf-8")
    assert "build_trade_behavioral_fit" in source
    assert '"behavioral_fit"' in source
    assert "acceptance=None" in source
    assert "candidate_from_trade_evaluation" in source
    assert "does not rewrite Value, disposition, or action authority" in source
    assert '"acceptance": "not calibrated or numerically estimated"' in source


def test_behavioral_profile_cache_is_read_only_and_fails_missing() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert "cached_behavior_profile_for_team" in source
    assert "return _profile_cache.get((league_state.state_id, team_id))" in source
    assert "does not" in source and "substitute evidence" in source
    assert "_publish_profiles_for_state(league_state, result)" in source


def test_opportunity_ui_explains_directional_fit_without_fake_acceptance_probability() -> None:
    source = UI.read_text(encoding="utf-8")
    assert "Behavioral fit" in source
    assert "This is not an acceptance probability" in source
    assert "behavioral_fit" in source
    assert "every driver" not in source  # presentation renders returned drivers directly
    assert "driver.description" in source
    assert "Numeric acceptance remains unavailable until separately calibrated" in source
    assert "acceptance_probability" not in source
