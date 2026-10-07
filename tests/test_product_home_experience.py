import hashlib
from pathlib import Path


STATIC = Path("src/fsffl/product/static")
HOME = (STATIC / "home_dashboard.js").read_text(encoding="utf-8")
FRANCHISE = (STATIC / "my_team_dashboard.js").read_text(encoding="utf-8")
NORTH_STAR = FRANCHISE.split("/* Franchise North Star 2026-09-24.", 1)[1]
SHELL = (STATIC / "product_shell.js").read_text(encoding="utf-8")
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
NAV = (STATIC / "product_navigation.js").read_text(encoding="utf-8")


def _git_blob_prefix(path: Path) -> str:
    blob = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(blob)).encode() + bytes([0]) + blob
    ).hexdigest()[:12]


def test_managed_standalone_home_is_retired_from_delivered_shell() -> None:
    assert "/static/home_dashboard.js" not in INDEX
    assert "home-north-star-presentation-guard" not in INDEX
    assert "fsffl-home-north-star-active" not in INDEX
    assert "ensureHomeScript" not in SHELL
    assert "homeNorthStarStaticVersion" not in SHELL


def test_managed_home_compatibility_route_normalizes_to_franchise_without_remaining_in_nav() -> None:
    assert "function fsfflManagedLandingRoute(route)" in SHELL
    assert "route==='league'&&state?.context?.team_id?'my_team':route" in SHELL
    assert "if(state?.context?.team_id&&state?.route==='league')" in SHELL
    assert "{route:'league',label:'Home'" not in NAV
    assert "{route:'my_team',label:'Franchise'" in NAV
    assert "{route:'league_comparison',label:'League'" in NAV
    assert "{route:'opportunities',label:'Explore'" in NAV
    assert "{route:'trade_center',label:'Trade'" in NAV
    compatibility = NAV.split("const COMPATIBILITY=[", 1)[1].split("];", 1)[0]
    assert "{route:'league',label:'Franchise'" in compatibility


def test_unselected_league_bootstrap_remains_available() -> None:
    assert '<div id="league-screen" class="route-screen">' in INDEX
    assert 'id="connect-button"' in INDEX
    assert "Connect Sleeper League" in INDEX
    assert "route==='league'&&state?.context?.team_id" in SHELL


def test_franchise_overview_preserves_approved_home_visual_language() -> None:
    for label in (
        "Season Outlook · current Simulation",
        "What Matters Right Now",
        "Also worth knowing",
        "Expected wins",
        "Playoffs",
        "Championship",
    ):
        assert label in FRANCHISE
    for visual in (
        "franchise-home-identity",
        "franchise-home-outlook-card",
        "franchise-home-outlook-grid",
        "franchise-home-outlook-metric",
        "franchise-home-matters",
        "franchise-home-secondary-row",
        "conic-gradient(#35d399",
        "#36b4d7",
    ):
        assert visual in FRANCHISE


def test_franchise_overview_uses_canonical_current_and_simulation_not_home_specific_current() -> None:
    assert "current_position_depth" in NORTH_STAR
    assert "currentPositionDepth" in NORTH_STAR
    assert "view?.utility?.competitive_outcome" in NORTH_STAR
    assert "myTeamLeagueOutcomeRank('expected_wins')" in NORTH_STAR
    assert "api('/api/home')" not in NORTH_STAR
    assert "view?.position_strengths" not in NORTH_STAR
    assert "source:'franchise-overview-current'" in NORTH_STAR
    assert "acceptance_probability" not in NORTH_STAR


def test_franchise_roster_and_assets_tabs_remain_primary_siblings() -> None:
    nav = FRANCHISE.split('<nav class="franchise-ns-tabs"', 1)[1].split("</nav>", 1)[0]
    assert "myTeamTabButton('overview','Overview'" in nav
    assert "myTeamTabButton('roster','Roster'" in nav
    assert "myTeamTabButton('assets','Assets & Picks'" in nav
    assert "function franchiseNSRoster()" in FRANCHISE
    assert "function franchiseNSAssets()" in FRANCHISE


def test_shared_readiness_remains_shell_owned_and_does_not_launch_model_work() -> None:
    assert "FSFFL_SHARED_READINESS_STEPS=7" in SHELL
    assert "api('/api/intelligence/status')" in SHELL
    assert "fsffl-shared-readiness-strip" in SHELL
    readiness = SHELL.split("const FSFFL_SHARED_READINESS_STEPS=7;", 1)[1].split(
        "function productSurfaceError", 1
    )[0]
    for forbidden in (
        "/api/intelligence/jobs",
        "/api/intelligence/refresh-forecasts",
        "/api/what-if",
        "/api/opportunities/workspace",
        "/api/trade-center/analyze",
        "/api/trade-center/simulate",
    ):
        assert forbidden not in readiness


def test_franchise_and_shell_delivery_keys_are_content_bound() -> None:
    franchise_prefix = _git_blob_prefix(STATIC / "my_team_dashboard.js")
    shell_prefix = _git_blob_prefix(STATIC / "product_shell.js")
    assert (
        f"const franchiseNorthStarStaticVersion='20261007-franchise-{franchise_prefix}';"
        in SHELL
    )
    assert (
        f"/static/product_shell.js?v=20261004-safari-restore380&c=git-{shell_prefix}"
        in INDEX
    )


def test_shared_readiness_keeps_compact_governed_status_contract() -> None:
    for label in (
        "Preparing current intelligence…",
        "Building projections…",
        "Refreshing league state…",
        "Running season outlook…",
        "Building market values…",
        "Attaching current intelligence…",
        "Build lifecycle complete",
        "Current core runtime fully available",
    ):
        assert label in SHELL
    assert "min-height:32px" in SHELL
    assert "height:2px" in SHELL
    assert "function fsfflSharedReadinessHost()" in SHELL
    assert "document.querySelector('#fsffl-sync-state')" in SHELL
    assert "fsffl-shared-readiness-host" in SHELL
    assert "display:block!important;pointer-events:auto;overflow:hidden" in SHELL
    assert "white-space:normal" in SHELL
    assert "overflow-wrap:anywhere" not in SHELL
    assert "overflow-wrap:normal;word-break:normal" in SHELL


def test_shared_readiness_tracks_status_on_every_route_without_starting_model_work() -> None:
    readiness = SHELL.split("const FSFFL_SHARED_READINESS_STEPS=7;", 1)[1].split(
        "function productSurfaceError", 1
    )[0]
    assert "fsffl:intelligence-status-updated" in SHELL
    assert "fsffl:product-context-updated" in SHELL
    assert "fsffl:sync-state" in SHELL
    assert "setInterval(" in readiness
    assert "2500" in readiness
    assert "if(!status.connected" in readiness
    assert "node.hidden=true" in readiness
    assert "fsfflSharedReadinessJobActive" in readiness
    for forbidden in (
        "/api/intelligence/jobs",
        "/api/intelligence/refresh-forecasts",
        "/api/what-if",
        "/api/opportunities/workspace",
        "/api/trade-center/analyze",
        "/api/trade-center/simulate",
    ):
        assert forbidden not in readiness


def test_manual_readiness_refresh_still_invokes_governed_intelligence_lifecycle() -> None:
    refresh = (STATIC / "forecast_refresh.js").read_text(encoding="utf-8")
    assert "window.fsfflManualIntelligenceRefresh?.()" in SHELL
    assert "window.fsfflManualIntelligenceRefresh=manualIntelligenceRefresh" in refresh


def test_unrelated_static_delivery_keys_remain_intact_during_home_retirement() -> None:
    assert "/static/app.js?v=20261004-safari-restore380" in INDEX
    mobile_prefix = _git_blob_prefix(STATIC / "mobile_safari_recovery.js")
    assert (
        f"/static/mobile_safari_recovery.js?v=20261004-safari-restore380&c=git-{mobile_prefix}"
        in INDEX
    )


def test_document_shell_contains_no_literal_escape_text() -> None:
    assert r"\n" not in INDEX
    head = INDEX.split("</head>", 1)[0]
    assert r"\n" not in head
