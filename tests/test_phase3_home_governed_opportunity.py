from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
MARKET = Path("src/fsffl/product/static/opportunities.js").read_text(encoding="utf-8")


def test_home_does_not_reuse_or_promote_market_recommendations() -> None:
    for forbidden in (
        "fsfflOpportunityState",
        "most_promising_evaluated",
        "recommendation_authority",
        "Best current action path",
        "No evaluated lead stands out yet",
        "Find my best moves",
    ):
        assert forbidden not in HOME


def test_home_suppresses_legacy_position_pressure_output_pending_consolidation() -> None:
    assert "data-home-action=\"pressure\"" not in HOME
    assert "source:'home-pressure'" not in HOME
    assert "position_strengths" not in HOME
    assert "homePressurePoint" not in HOME
    assert "/api/opportunities/workspace" not in HOME
    assert "oppConsumeHomeIntent" in MARKET
    assert "Market owns discovery and evaluation from here." in MARKET


def test_home_has_no_cross_family_master_priority_score() -> None:
    assert "homePressurePoint" not in HOME
    assert "position_strengths" not in HOME
    for forbidden in (
        "master score",
        "priority score",
        "composite score",
        "risk grade",
        "best trade",
        "owner interest",
    ):
        assert forbidden not in HOME.lower()
