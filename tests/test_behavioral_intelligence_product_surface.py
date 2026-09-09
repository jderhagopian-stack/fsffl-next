from pathlib import Path


JS = Path("src/fsffl/product/static/behavioral_intelligence.js")
CSS = Path("src/fsffl/product/static/behavioral_intelligence.css")


def test_behavioral_dashboard_has_end_state_information_architecture() -> None:
    source = JS.read_text(encoding="utf-8")
    for phrase in (
        "Observed history",
        "Context-controlled inference",
        "Decision use",
        "Evidence & provenance",
        "Team/Owner-Adjusted Value",
        "Proposal fit",
        "Acceptance probability",
        "Inference quality",
    ):
        assert phrase in source


def test_behavioral_dashboard_does_not_fake_context_controlled_outputs() -> None:
    source = JS.read_text(encoding="utf-8")
    assert "strictly pre-action canonical State history" in source
    assert "Current-state or post-action data will not be substituted" in source
    assert "No calibrated acceptance model has been promoted" in source
    assert "transaction counts into fake acceptance odds" in source


def test_behavioral_dashboard_routes_proposal_specific_use_to_trade_center() -> None:
    source = JS.read_text(encoding="utf-8")
    assert "data-behavior-open-trade" in source
    assert "setRoute('trade_center')" in source
    assert "Package-shape Behavioral evidence belongs in the Trade Decision lane" in source


def test_behavioral_dashboard_is_mobile_responsive() -> None:
    source = CSS.read_text(encoding="utf-8")
    assert "@media(max-width:1050px)" in source
    assert "@media(max-width:760px)" in source
    assert ".behavior-owner-list{display:flex;overflow:auto" in source


def test_behavioral_dashboard_keeps_observed_and_inferred_visual_states_distinct() -> None:
    source = JS.read_text(encoding="utf-8")
    assert "Observed evidence live" in source
    assert "Awaiting PIT history" in source
    assert "Not estimable" in source
    assert "Not estimated" in source
