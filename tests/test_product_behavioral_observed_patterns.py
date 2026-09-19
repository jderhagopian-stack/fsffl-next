from pathlib import Path


def test_behavioral_observed_summary_stays_descriptive_and_uses_existing_profiles() -> None:
    source = Path("src/fsffl/product/static/behavioral_intelligence.js").read_text(encoding="utf-8")
    for label in (
        "Observed-pattern summary",
        "What the completed record actually shows",
        "Most acquired position",
        "Most disposed position",
        "Most common completed trade shape",
        "Draft-pick flow",
        "Most frequent completed counterparty",
    ):
        assert label in source
    assert "completed actions only" in source.lower()
    assert "not a stable preference, acceptance probability, proposal fit, owner-adjusted Value, or strategy classification" in source
    assert source.count("api('/api/behavioral/profiles')") == 1
    assert "fsfflBehaviorProfiles=profiles" in source


def test_behavioral_counterparties_resolve_from_loaded_profile_names_without_new_authority() -> None:
    source = Path("src/fsffl/product/static/behavioral_intelligence.js").read_text(encoding="utf-8")
    assert "function fsfflBehaviorCounterpartyName" in source
    assert "fsfflBehaviorProfiles.find" in source
    assert "fsfflBehaviorName(profile)" in source
    assert "fsfflBehaviorCounterpartyName(owner)" in source
    assert "fsfflBehaviorCounterpartyName(counterparty[0])" in source
    assert "Acceptance probability</strong><small>Not estimable" in source
    assert "Universal FSFFL Market Value remains unchanged" in source


def test_behavioral_summary_does_not_create_score_or_acceptance_math() -> None:
    source = Path("src/fsffl/product/static/behavioral_intelligence.js").read_text(encoding="utf-8")
    assert "behavior_score" not in source
    assert "owner_score" not in source
    assert "acceptance_score" not in source
    assert "acceptance_probability=" not in source
    assert "owner_adjusted_value=" not in source
