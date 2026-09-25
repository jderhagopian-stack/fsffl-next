from pathlib import Path


MOBILE = Path("src/fsffl/product/static/mobile_safari_recovery.js").read_text(encoding="utf-8")
SHELL = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
FRANCHISE = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
WEBAPP = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
INDEX = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")


def test_cross_league_switch_acknowledges_requested_identity_before_import() -> None:
    interactive = MOBILE.split("async function interactiveConnect()", 1)[1]
    lifecycle_index = interactive.index("publishLeagueLifecycle('switching'")
    import_index = interactive.index("waitForBackgroundImport(normalized")
    assert lifecycle_index < import_index
    assert "requested_league_id:normalized" in interactive
    assert "operation:'switch_league'" in interactive
    assert "League switch failed; the prior league remains active." in interactive


def test_refresh_league_uses_same_global_lifecycle_contract() -> None:
    refresh = MOBILE.split("async function refreshStoredLeague", 1)[1].split(
        "async function restoreSavedSession", 1
    )[0]
    assert "publishLeagueLifecycle('refreshing_state'" in refresh
    assert "publishLeagueLifecycle('state_ready'" in refresh
    assert "publishLeagueLifecycle('failed'" in refresh
    assert "last valid State remains usable" in refresh


def test_shell_names_served_identity_and_exact_failed_stage() -> None:
    assert "fsffl:league-context-changed" in SHELL
    assert "failureStage=job?.failure_stage||null" in SHELL
    assert "Forecast blocked — current league roster remains available" in SHELL
    assert "League lifecycle action failed; prior usable State is retained." in SHELL


def test_franchise_never_reuses_cross_league_cached_view() -> None:
    load = FRANCHISE.split("async function loadFranchiseNorthStar()", 1)[1]
    assert "cachedLeagueId===state?.context?.league_id" in load
    assert "fsffl:league-context-changed" in FRANCHISE
    assert "fsfflMyTeamState.view=null" in FRANCHISE


def test_state_only_franchise_roster_does_not_collapse_to_empty_starters() -> None:
    roster = FRANCHISE.split("function franchiseNSRoster()", 1)[1].split(
        "function franchiseNSAssets", 1
    )[0]
    assert "const filter=lineupReady?requestedFilter:'all'" in roster
    assert "Current roster is loaded from league State." in roster
    assert "No players are present in the current league State." in roster
    assert "No players in this roster view." not in roster


def test_intelligence_status_exposes_state_and_provisional_authority_boundary() -> None:
    assert '"served_state"' in WEBAPP
    assert '"state_ready"' in WEBAPP
    assert '"intelligence_complete"' in WEBAPP
    assert '"failure_stage"' in WEBAPP
    assert '"provisional_k_dst"' in WEBAPP
    assert '"simulation_authorized": False' in WEBAPP
    assert '"value_authorized": False' in WEBAPP
    assert "no provisional rows are attached to the active runtime" in WEBAPP


def test_lifecycle_assets_are_independently_cache_busted() -> None:
    for asset in (
        "mobile_safari_recovery.js",
        "forecast_refresh.js",
        "product_shell.js",
    ):
        assert (
            f"/static/{asset}?v=20260925-market-corrective1&lc=20260925-lifecycle1"
            in INDEX
        )
