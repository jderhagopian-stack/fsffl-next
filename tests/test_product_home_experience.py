from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
SHELL = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
LEAGUE = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
MARKET = Path("src/fsffl/product/static/opportunities.js").read_text(encoding="utf-8")


def test_home_matches_north_star_single_screen_information_architecture() -> None:
    for label in (
        "What matters right now",
        "Season outlook · current Simulation",
        "Your roster at a glance",
        "Also worth knowing",
        "Around the league",
        "Projected final wins",
        "Playoffs",
        "Championship",
        "Largest single-player exposure",
        "Current outlook",
    ):
        assert label in HOME
    assert "home-north-star" in HOME
    assert "home-position-grid" in HOME
    assert "home-outlook-grid" in HOME
    assert "home-secondary-row" in HOME
    assert "home-workflows" not in HOME
    assert "Franchise pulse" not in HOME
    assert "Best next action" not in HOME


def test_home_pressure_point_uses_only_governed_position_strength_family() -> None:
    assert "function homePressurePoint()" in HOME
    assert "position_strengths" in HOME
    assert "league_rank" in HOME
    assert "strength_index" in HOME
    assert "Explore '+homeEscape(pressure.position)+' options" in HOME
    for forbidden in (
        "recommendation_authority",
        "acceptance_probability",
        "most_promising_evaluated",
        "risk grade",
        "weekly win",
        "injury",
    ):
        assert forbidden.lower() not in HOME.lower()


def test_home_outlook_is_exact_current_simulation_or_unavailable() -> None:
    assert "payload.simulation?.status==='ready'" in HOME
    assert "simulation_count" in HOME
    assert "expected_wins" in HOME
    assert "playoff_probability" in HOME
    assert "championship_probability" in HOME
    assert "Matching current Simulation unavailable" in HOME


def test_home_cold_load_calls_only_home_composition_endpoint() -> None:
    assert "api('/api/home')" in HOME
    for forbidden in (
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center",
        "/api/what-if",
        "/api/intelligence/refresh-forecasts",
        "/api/league/value-lenses",
    ):
        assert forbidden not in HOME
    assert "launches no Opportunity Search, bilateral Decision evaluation, Value build, Forecast refresh, or changed-state Simulation" in HOME


def test_home_contextual_navigation_contract_is_presentation_owned() -> None:
    assert "fsfflNavigateTo" in HOME
    assert "fsfflSetDeepLinkIntent" in SHELL
    assert "fsfflConsumeDeepLinkIntent" in SHELL
    assert "route:'my_team'" in HOME
    assert "route:'opportunities'" in HOME
    assert "route:'league_comparison'" in HOME
    assert "section:'positions'" in HOME
    assert "section:'overview'" in HOME
    assert "metric:'expected_finish'" in HOME
    assert "fragilityDriver:true" in HOME
    assert "laConsumeDeepLinkIntent" in LEAGUE
    assert "oppConsumeHomeIntent" in MARKET


def test_home_is_mobile_first_without_horizontal_scrolling() -> None:
    assert "@media(max-width:760px)" in HOME
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in HOME
    assert "padding:4px 10px calc(76px + env(safe-area-inset-bottom,0px))" in HOME
    assert "touch-action:manipulation" in HOME
    assert "overflow-x:auto" not in HOME
