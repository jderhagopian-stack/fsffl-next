from pathlib import Path


def test_reports_workspace_reuses_existing_authoritative_endpoints() -> None:
    source = Path("src/fsffl/product/static/reports.js").read_text(encoding="utf-8")
    assert "api('/api/my-team')" in source
    assert "api('/api/league/team-views')" in source
    assert "api('/api/values')" in source
    assert "api('/api/intelligence/status')" in source
    assert "/api/league/chart?metric=" in source
    assert "No report-only score or adjustment is added here." in source


def test_reports_expose_team_league_and_evidence_views() -> None:
    source = Path("src/fsffl/product/static/reports.js").read_text(encoding="utf-8")
    for label in ("My Team", "League", "Evidence & Sources"):
        assert label in source
    for metric in (
        "expected_wins",
        "playoff_probability",
        "championship_probability",
        "optimized_expected_points",
        "asset_portfolio_mean",
        "draft_pick_count",
    ):
        assert metric in source
    assert "calculated_competitive_state" in source
    assert "Market percentile" in source
    assert "successful_sources" in source
    assert "failed_sources" in source
    assert "cardinal_player_coverage" in source


def test_reports_use_full_nfl_season_player_projection_only() -> None:
    source = Path("src/fsffl/product/static/reports.js").read_text(encoding="utf-8")
    assert "season_fantasy_points_projection" in source
    assert "item.horizon==='season'" in source
    assert "fantasy_regular_season" not in source
    assert "NFL season projection" in source


def test_reports_are_presentation_only_and_mobile_responsive() -> None:
    source = Path("src/fsffl/product/static/reports.js").read_text(encoding="utf-8")
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "ensureReportsScript" in shell
    assert "renderFsfflReports" in shell
    assert "master score" in source
    assert "Starter age is descriptive presentation math, not a utility input or team grade." in source
    assert "Power ranking order is expected wins only" in source
    assert "No report-only coefficient, blend, or subjective adjustment" in source
    assert "master_score" not in source
    assert "composite_score" not in source
    assert "acceptance_probability" not in source
    assert "@media(max-width:760px)" in source
    assert "@media(max-width:460px)" in source
