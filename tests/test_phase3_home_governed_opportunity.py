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


def test_home_pressure_cta_navigates_to_market_without_running_search_on_home() -> None:
    assert "data-home-action=\"pressure\"" in HOME
    assert "route:'opportunities'" in HOME
    assert "source:'home-pressure'" in HOME
    assert "/api/opportunities/workspace" not in HOME
    assert "oppConsumeHomeIntent" in MARKET
    assert "fsfflOpportunityState.query=position" in MARKET
    assert "Market owns discovery and evaluation from here." in MARKET


def test_home_has_no_cross_family_master_priority_score() -> None:
    assert "homePressurePoint" in HOME
    assert "position_strengths" in HOME
    for forbidden in (
        "master score",
        "priority score",
        "composite score",
        "risk grade",
        "best trade",
        "owner interest",
    ):
        assert forbidden not in HOME.lower()
