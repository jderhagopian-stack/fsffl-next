from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
MARKET = Path("src/fsffl/product/static/opportunities.js").read_text(encoding="utf-8")


def test_home_pressure_point_does_not_reuse_or_launch_opportunity_workspace() -> None:
    assert "fsfflOpportunityState" not in HOME
    assert "/api/opportunities/workspace" not in HOME
    assert "most_promising_evaluated" not in HOME
    assert "recommendation_authority" not in HOME
    assert "Explore '+homeEscape(weakest.position)+' options" in HOME
    assert "route:'opportunities'" in HOME


def test_market_owns_search_after_home_navigation() -> None:
    assert "function oppApplyNavigationIntent()" in MARKET
    assert "fsfflConsumeNavigationIntent('opportunities')" in MARKET
    assert "fsfflOpportunityState.tab='trades'" in MARKET
    assert "fsfflOpportunityState.query=String(intent.position)" in MARKET
    assert "async function loadOpportunityWorkspace" in MARKET
    assert "api('/api/opportunities/workspace')" in MARKET


def test_home_never_claims_evaluated_recommendation_authority() -> None:
    forbidden = (
        "Best current action path",
        "Work this opportunity",
        "Strongest action-authoritative path",
        "Lead to investigate",
        "No fabricated recommendation",
        "high risk",
        "medium risk",
        "best trade",
    )
    for token in forbidden:
        assert token not in HOME
