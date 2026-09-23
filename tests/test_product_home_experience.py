from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
SHELL = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
LEAGUE = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
MARKET = Path("src/fsffl/product/static/opportunities.js").read_text(encoding="utf-8")
INDEX = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")


def test_home_is_one_personalized_command_center_not_dashboard_duplicate() -> None:
    for label in (
        "What matters right now",
        "Season outlook",
        "Your roster at a glance",
        "Also worth knowing",
        "Around the league",
    ):
        assert label in HOME
    assert "home-command" in HOME
    assert "home-position-grid" in HOME
    assert "home-secondary-list" in HOME
    assert "home-workflows" not in HOME
    assert "home-pulse-list" not in HOME
    assert "data-home-tab" not in HOME
    assert "Key Insights" not in HOME
    assert "Next Moves" not in HOME


def test_home_uses_read_only_composition_and_does_not_launch_deep_work() -> None:
    assert "api('/api/home/command-center')" in HOME
    for forbidden in (
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center/analyze",
        "/api/trade-center/simulate",
        "/api/league/atlas",
        "/api/simulator",
    ):
        assert forbidden not in HOME
    assert "fsfflOpportunityState" not in HOME
    assert "homePrimaryAction" not in HOME
    assert "acceptance_probability" not in HOME
    assert "weekly win" not in HOME.lower()
    assert "injury" not in HOME.lower()
    assert "change since last visit" not in HOME.lower()


def test_home_has_exact_approved_primary_and_secondary_signals() -> None:
    assert "homeWeakestPosition" in HOME
    assert "['QB','RB','WR','TE']" not in HOME  # implementation uses fixed comparable set via object/order
    for position in ("QB", "RB", "WR", "TE"):
        assert position in HOME
    assert "Projected final wins" in HOME
    assert "Playoffs" in HOME
    assert "Championship" in HOME
    assert "Rank" in HOME
    assert "Strength Index" in HOME
    assert "Largest single-player exposure" in HOME
    assert "Expected finish:" in HOME
    assert HOME.count("home-secondary-row") >= 3  # class plus exactly two rendered rows
    assert "largest_single_player_lineup_drop" in HOME
    assert "largest_single_player_lineup_drop_player_ids" in HOME


def test_home_deep_links_are_contextual_and_destination_owned() -> None:
    assert "window.fsfflNavigate" in SHELL
    assert "window.fsfflConsumeNavigationIntent" in SHELL
    assert "route:'my_team'" in HOME
    assert "route:'opportunities'" in HOME
    assert "route:'league_comparison'" in HOME
    assert "section:'positions'" in HOME
    assert "section:'overview'" in HOME
    assert "metric:'expected_wins'" in HOME
    assert "metric:'playoff_probability'" in HOME
    assert "metric:'championship_probability'" in HOME
    assert "metric:'expected_finish'" in HOME
    assert "playerId:driver.primary.player_id" in HOME
    assert "applyLeagueNavigationIntent" in LEAGUE
    assert "fsfflConsumeNavigationIntent('opportunities')" in MARKET
    assert "fsfflOpportunityState.query=String(intent.position)" in MARKET


def test_home_is_mobile_first_and_preserves_safe_area() -> None:
    assert "@media(max-width:760px)" in HOME
    assert "overflow-x:hidden" in HOME
    assert "env(safe-area-inset-bottom,0px)" in HOME
    assert "grid-template-columns:repeat(3,1fr)" in HOME
    assert "grid-template-columns:repeat(4,1fr)" in HOME
    assert "min-height:72px" in HOME
    assert "min-height:64px" in HOME
    assert "/static/home_dashboard.js?v=20260923-home-north-star1" in INDEX
    assert "const homeStaticVersion='20260923-home-north-star1';" in SHELL


def test_home_hides_old_dashboard_and_pipeline_status() -> None:
    for selector in (".metric-grid", ".dashboard-grid", ".roster-panel"):
        assert selector in HOME
    assert "runtime.hidden=true" in HOME
    assert "hero.hidden=true" in HOME
