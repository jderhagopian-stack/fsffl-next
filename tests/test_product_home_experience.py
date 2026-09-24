from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
SHELL = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
LEAGUE = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
MARKET = Path("src/fsffl/product/static/opportunities.js").read_text(encoding="utf-8")
INDEX = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
APP = Path("src/fsffl/product/static/app.js").read_text(encoding="utf-8")


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


def test_home_cold_load_uses_only_bounded_read_endpoints_and_no_deep_work() -> None:
    assert "api('/api/home')" in HOME
    assert "api('/api/intelligence/status')" in HOME
    for forbidden in (
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center",
        "/api/what-if",
        "/api/intelligence/refresh-forecasts",
        "/api/league/value-lenses",
    ):
        assert forbidden not in HOME
    assert "It does not launch Opportunity Search, Decision, Value or new Simulation work." in HOME


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


def test_home_north_star_suppresses_all_legacy_home_modules_from_first_paint() -> None:
    assert 'class="route-screen fsffl-home-north-star-active"' in INDEX
    assert 'data-home-surface="north-star"' in INDEX
    assert '<section id="home-attention" class="home-attention"' in INDEX
    assert 'id="home-north-star-presentation-guard"' in INDEX
    for selector in (
        "#league-screen.fsffl-home-north-star-active > .hero-row",
        "#league-screen.fsffl-home-north-star-active > #runtime-status",
        "#league-screen.fsffl-home-north-star-active > .metric-grid",
        "#league-screen.fsffl-home-north-star-active > .dashboard-grid",
        "#league-screen.fsffl-home-north-star-active > .roster-panel",
        "#league-screen.fsffl-home-north-star-active > #home-quick-actions",
    ):
        assert selector in INDEX
    assert "display: none !important;" in INDEX
    assert "leagueScreen.classList.add('fsffl-home-north-star-active')" in HOME


def test_home_north_star_has_no_literal_escape_text_in_document_shell() -> None:
    assert r"\n" not in INDEX
    head = INDEX.split("</head>", 1)[0]
    assert r"\n" not in head


def test_home_north_star_accepted_sections_and_drill_ins_remain_intact_after_cleanup() -> None:
    for label in (
        "What matters right now",
        "Season outlook · current Simulation",
        "Your roster at a glance",
        "Also worth knowing",
        "Around the league",
    ):
        assert label in HOME
    for action in (
        "data-home-action=\"franchise\"",
        "data-home-action=\"pressure\"",
        "data-home-action=\"outlook\"",
        "data-home-action=\"position\"",
        "data-home-action=\"exposure\"",
    ):
        assert action in HOME


def test_home_replaces_methods_evidence_dropdown_with_compact_readiness_strip() -> None:
    assert '<details class="home-evidence">' not in HOME
    assert "Evidence & readiness" not in HOME
    assert "home-readiness-strip" in HOME
    assert "HOME_READINESS_STEPS=7" in HOME
    for label in (
        "Preparing current intelligence…",
        "Building projections…",
        "Refreshing league state…",
        "Running season outlook…",
        "Building market values…",
        "Attaching current intelligence…",
        "Intelligence current",
    ):
        assert label in HOME
    assert "min-height:32px" in HOME
    assert "height:2px" in HOME
    assert "function homeReadinessHost()" in HOME
    assert "document.querySelector(\'#fsffl-sync-state\')" in HOME
    assert "home-readiness-host" in HOME
    assert "function homeReleaseReadinessHost()" in HOME
    assert "window.fsfflHomeReadinessRouteChanged" in HOME
    rendered = HOME[HOME.index("container.innerHTML=`<section class=\\\"home-north-star\\\">"):HOME.index("homeWireActions(container);")]
    assert "${homeReadinessMarkup()}" not in rendered


def test_home_readiness_strip_tracks_canonical_intelligence_status_without_launching_work() -> None:
    assert "api('/api/intelligence/status')" in HOME
    assert "fsffl:intelligence-status-updated" in HOME
    assert "fsffl:intelligence-status-updated" in APP
    assert "setInterval(" in HOME
    assert "2500" in HOME
    for forbidden in (
        "/api/intelligence/jobs",
        "/api/intelligence/refresh-forecasts",
        "/api/what-if",
        "/api/opportunities/workspace",
    ):
        assert forbidden not in HOME


def test_home_readiness_assets_are_cache_busted_without_splitting_release_generation() -> None:
    assert "/static/app.js?v=20260924-home-readiness-top1" in INDEX
    assert "/static/home_dashboard.js?v=20260924-home-readiness-top1" in INDEX
