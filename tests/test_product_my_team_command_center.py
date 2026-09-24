from pathlib import Path


SOURCE = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
SHELL = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
NORTH_STAR = SOURCE.split("/* Franchise North Star 2026-09-24.", 1)[1]


def test_franchise_north_star_consumes_only_existing_governed_read_paths() -> None:
    for endpoint in (
        "api('/api/my-team')",
        "api('/api/league/team-views')",
        "api('/api/home')",
        "api('/api/league/value-lenses')",
    ):
        assert endpoint in NORTH_STAR
    for evidence in (
        "calculated_competitive_state",
        "position_strengths",
        "roster_resilience",
        "projected_starter",
        "draft_picks",
        "Broad Market",
        "FSFFL Intrinsic",
    ):
        assert evidence in NORTH_STAR
    for forbidden in (
        "/api/opportunities/workspace",
        "/api/opportunities/trade",
        "/api/trade-center",
        "/api/what-if",
        "/api/intelligence/refresh-forecasts",
        "acceptance_probability",
    ):
        assert forbidden not in NORTH_STAR


def test_franchise_has_exactly_three_primary_tabs_and_no_strategy_or_history() -> None:
    nav = NORTH_STAR.split('<nav class="franchise-ns-tabs"', 1)[1].split("</nav>", 1)[0]
    assert nav.count("myTeamTabButton(") == 3
    assert "myTeamTabButton('overview','Overview'" in nav
    assert "myTeamTabButton('roster','Roster'" in nav
    assert "myTeamTabButton('assets','Assets & Picks'" in nav
    assert "History" not in nav
    assert "Strategy" not in nav
    assert "Diagnosis" not in nav


def test_franchise_overview_matches_approved_scan_first_structure() -> None:
    overview = NORTH_STAR.split("function franchiseNSOverview(){", 1)[1].split(
        "function franchiseNSRoster(){", 1
    )[0]
    for label in (
        "Expected wins",
        "Playoffs",
        "Championship",
        "League rank",
        "Position strength",
        "Rank",
        "Index",
        "What defines this franchise",
        "Foundation",
        "Pressure point",
        "Largest single-player exposure",
        "Projected starter age",
        "Full-roster age",
        "Draft capital",
        "Future runway",
        "Count",
        "Value",
        "Explore ",
    ):
        assert label in overview
    assert "Key Takeaways" not in overview
    assert "championship window" not in overview.lower()
    assert "dynasty score" not in overview.lower()


def test_franchise_same_state_simulation_is_reused_not_recomputed() -> None:
    assert "results[2]&&results[2].league_state_id===results[0]?.context?.league_state_id" in NORTH_STAR
    assert "home.simulation?.status!=='ready'" in NORTH_STAR
    assert "simulation?.expected_wins" in NORTH_STAR
    assert "simulation?.playoff_probability" in NORTH_STAR
    assert "simulation?.championship_probability" in NORTH_STAR
    assert "new Simulation" not in NORTH_STAR
    assert "simulation_loader" not in NORTH_STAR


def test_franchise_position_rings_expand_inline_player_and_fragility_evidence() -> None:
    for position in ("QB", "RB", "WR", "TE"):
        assert f"'{position}'" in NORTH_STAR
    assert "franchise-ns-position-ring" in NORTH_STAR
    assert "data-franchise-position" in NORTH_STAR
    assert "franchise-ns-position-detail" in NORTH_STAR
    assert "data-player-intelligence-id" in NORTH_STAR
    assert "Largest one-player lineup drop" in NORTH_STAR
    assert "Largest exposure" in NORTH_STAR


def test_franchise_roster_is_compact_filtered_and_uses_one_forecast_basis() -> None:
    roster = NORTH_STAR.split("function franchiseNSRoster(){", 1)[1].split(
        "function franchiseNSAssets(){", 1
    )[0]
    assert "franchiseRosterFilter:'starters'" in NORTH_STAR
    assert "Starters" in roster
    assert "Bench" in roster
    assert "All Players" in roster
    assert "franchise-ns-player-list" in roster
    assert "franchise-table-wrap" not in roster
    assert "FSFFL_FRANCHISE_GAME_BASIS=17" in NORTH_STAR
    assert "return season==null?null:season/FSFFL_FRANCHISE_GAME_BASIS" in NORTH_STAR
    assert "Proj · 17g" in NORTH_STAR
    assert "Broad Market" in NORTH_STAR
    assert "FSFFL Intrinsic" in NORTH_STAR
    assert "data-player-intelligence-id" in NORTH_STAR
    assert "roster.filter(franchiseNSProjectedStarter)" in roster
    assert "!franchiseNSProjectedStarter(player)" in roster


def test_franchise_assets_keep_market_intrinsic_and_pick_authority_separate() -> None:
    assets = NORTH_STAR.split("function franchiseNSAssets(){", 1)[1].split(
        "function renderFranchiseNorthStar(){", 1
    )[0]
    assert "Broad Market" in assets
    assert "FSFFL Intrinsic" in assets
    assert "Flexible assets" in assets
    assert "describes optionality; it is not a trade recommendation" in assets
    assert "Player lens selection never changes universal pick evidence." in assets
    assert "Picks" in assets
    assert "Value" in assets
    assert "blended" not in assets.lower()
    assert "Sell Candidates" not in assets
    assert "Movable Assets" not in assets


def test_franchise_degraded_forecast_is_compact_and_default_methods_clutter_is_removed() -> None:
    renderer = NORTH_STAR.split("function renderFranchiseNorthStar(){", 1)[1].split(
        "async function loadFranchiseNorthStarValueLenses", 1
    )[0]
    assert "franchise-ns-forecast-strip" in renderer
    assert "Forecast fallback active" in renderer
    assert "Preserved preseason projections in use · live source-health degraded." in renderer
    assert "fallback?" in renderer
    assert "Current governed Forecast" not in renderer
    assert "Methods & evidence" not in NORTH_STAR
    assert '<details class="franchise-ns-evidence">' not in NORTH_STAR


def test_franchise_missing_evidence_fails_visibly_without_substitute_metrics() -> None:
    for text in (
        "Position-strength evidence has not attached.",
        "Exposure unavailable",
        "Roster-resilience evidence has not attached.",
        "Broad Market pick Value evidence is unavailable",
        "Selected-lens player Value evidence is unavailable.",
        "Intrinsic unavailable",
    ):
        assert text in NORTH_STAR


def test_franchise_north_star_is_the_only_primary_franchise_renderer() -> None:
    assert "window.renderFsfflMyTeam=loadFranchiseNorthStar;" in NORTH_STAR
    assert NORTH_STAR.rfind("window.renderFsfflMyTeam=") == NORTH_STAR.rfind(
        "window.renderFsfflMyTeam=loadFranchiseNorthStar;"
    )
    assert "franchiseNorthStarStaticVersion='20260924-live-usability-hotfix1'" in SHELL
    assert "lazyProductScript(\'renderFsfflMyTeam\',\'/static/my_team_dashboard.js\'" in SHELL
    assert "franchiseNorthStarStaticVersion)" in SHELL


def test_franchise_mobile_layout_avoids_table_first_and_page_horizontal_scroll() -> None:
    assert "@media(max-width:760px)" in NORTH_STAR
    assert "@media(max-width:420px)" in NORTH_STAR
    assert "min-height:44px" in NORTH_STAR
    assert "touch-action:manipulation" in NORTH_STAR
    assert "overflow-x:auto" not in NORTH_STAR
    assert "grid-template-areas" in NORTH_STAR


def test_franchise_intrinsic_unavailable_is_explicit_not_a_dash() -> None:
    assert "franchiseNSIntrinsicReason" in NORTH_STAR
    assert "Governed FSFFL Intrinsic is unavailable for the current league state." in NORTH_STAR
    assert "fsffl_intrinsic?.reason" in NORTH_STAR


def test_franchise_roster_and_flexible_assets_share_canonical_starter_classification() -> None:
    helper = NORTH_STAR.split("function franchiseNSProjectedStarter(player){", 1)[1].split(
        "function franchiseNSPlayerRole(player){", 1
    )[0]
    assert "player?.projected_starter===true" in helper

    role = NORTH_STAR.split("function franchiseNSPlayerRole(player){", 1)[1].split(
        "function franchiseNSPlayerRow(player){", 1
    )[0]
    assert "franchiseNSProjectedStarter(player)" in role
    assert "return'Bench'" in role
    assert "roster_slot==='TAXI'" in role
    assert "roster_slot==='IR'" in role

    ranked = NORTH_STAR.split("function franchiseNSRankedAssets", 1)[1].split(
        "function franchiseNSAssetValue", 1
    )[0]
    assert "!franchiseNSProjectedStarter(player)" in ranked


def test_franchise_mobile_player_names_wrap_without_ellipsis_and_cards_are_only_modestly_tighter() -> None:
    assert ".franchise-ns-player-id strong{white-space:normal" in NORTH_STAR
    assert "text-overflow:clip" in NORTH_STAR
    assert "overflow-wrap:anywhere" in NORTH_STAR
    assert ".franchise-ns-player-row{width:100%;min-height:58px" in NORTH_STAR
    assert "padding:7px 9px" in NORTH_STAR
    player_style = NORTH_STAR.split(".franchise-ns-player-id strong{", 1)[1].split("}", 1)[0]
    assert "text-overflow:ellipsis" not in player_style
    assert "white-space:nowrap" not in player_style


def test_franchise_pick_labels_preserve_original_team_attribution_and_fail_closed_value() -> None:
    assert "pick.original_team_id" in SOURCE
    assert "myTeamTeamName(pick.original_team_id)" in SOURCE
    assert "Value unavailable" in NORTH_STAR
    assert "Broad Market pick Value evidence is unavailable" in NORTH_STAR
