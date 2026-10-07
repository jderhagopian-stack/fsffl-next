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


def test_managed_home_route_normalizes_to_franchise_without_changing_nav_structure() -> None:
    assert "function fsfflManagedLandingRoute(route)" in SHELL
    assert "route==='league'&&state?.context?.team_id?'my_team':route" in SHELL
    assert "if(state?.context?.team_id&&state?.route==='league')" in SHELL
    # Bottom-nav structure remains a separate follow-on.
    assert "{route:'league',label:'Home'" in NAV
    assert "{route:'my_team',label:'Franchise'" in NAV
    assert "{route:'league_comparison',label:'League'" in NAV
    assert "{route:'opportunities',label:'Market'" in NAV


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
