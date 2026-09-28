from __future__ import annotations

import subprocess
import textwrap
from threading import Event
from time import monotonic, sleep

from fsffl.product.hosted_connect import LeagueConnectCoordinator, LeagueConnectStatus
from fsffl.product.persistent_webapp import app


def test_background_connect_returns_without_waiting_for_provider_work() -> None:
    coordinator = LeagueConnectCoordinator(max_workers=1)
    release = Event()
    started = Event()

    def work() -> None:
        started.set()
        release.wait(timeout=2)

    before = monotonic()
    job = coordinator.start(user_id="u", league_external_id="123", work=work)
    elapsed = monotonic() - before

    assert elapsed < 0.25
    assert job.status == LeagueConnectStatus.QUEUED
    assert started.wait(timeout=1)
    current = coordinator.current("u")
    assert current is not None
    assert current.status == LeagueConnectStatus.RUNNING

    duplicate = coordinator.start(user_id="u", league_external_id="123", work=work)
    assert duplicate.job_id == current.job_id

    release.set()
    deadline = monotonic() + 2
    while monotonic() < deadline:
        current = coordinator.current("u")
        if current is not None and current.status == LeagueConnectStatus.COMPLETED:
            break
        sleep(0.01)
    assert current is not None
    assert current.status == LeagueConnectStatus.COMPLETED


def test_background_refresh_is_labeled_but_uses_same_single_flight_coordinator() -> None:
    coordinator = LeagueConnectCoordinator(max_workers=1)
    release = Event()
    started = Event()

    def work() -> None:
        started.set()
        release.wait(timeout=2)

    job = coordinator.start(
        user_id="u",
        league_external_id="123",
        work=work,
        operation="refresh",
    )
    assert job.operation == "refresh"
    assert started.wait(timeout=1)
    duplicate = coordinator.start(
        user_id="u",
        league_external_id="123",
        work=work,
        operation="connect",
    )
    assert duplicate.job_id == job.job_id
    release.set()


def test_hosted_app_exposes_short_start_poll_and_refresh_routes() -> None:
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/api/connect/sleeper/background" in paths
    assert "/api/connect/sleeper/background/refresh" in paths
    assert "/api/connect/sleeper/background/current" in paths


def test_mobile_connect_uses_background_import_and_transport_recovery() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "fsfflMobileSafariRecoveryDisabled=true" in source
    assert "/api/connect/sleeper/background'" in source
    assert "/api/connect/sleeper/background/refresh'" in source
    assert "/api/connect/sleeper/background/current" in source
    assert "Load failed|Failed to fetch|Network request failed|network error" in source
    assert "document.addEventListener('click'" in source
    assert "event.stopImmediatePropagation()" in source
    assert "window.fsfflRestoreSession=restoreSavedSession" in source
    assert "Loading league…" in source
    assert "visibilitychange" not in source
    assert "pageshow" not in source


def test_mobile_connect_has_one_poll_owner_and_uses_state_before_terminal_connect() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "let activeConnectPromise=null" in source
    assert "let activeLeagueId=null" in source
    assert "activeConnectPromise&&activeLeagueId===leagueId" in source
    assert "const existing=await recoverCurrentJob(leagueId,operation)" in source
    assert "['queued','running'].includes(existing.status)" in source
    assert "current.status==='completed'&&current.operation===operation" in source
    perform = source.split("async function performBackgroundImport", 1)[1].split(
        "function waitForBackgroundImport", 1
    )[0]
    assert "let nextContextProbeAt=0" in perform
    assert "operation==='connect'&&Date.now()>=nextContextProbeAt" in perform
    assert "const usable=await usableConnectedContext(leagueId)" in perform
    assert "if(usable)return usable" in perform
    assert perform.index("if(usable)return usable") < perform.index("job?.status==='completed'")
    assert "const context=await resilientApi('/api/product-context',{},3)" in perform
    assert "pollDelay=Math.min(2200" in source
    assert "League import completed without activating the requested Sleeper league." in source
    assert "if(!contextMatchesLeague(context,normalized)||!context?.state_id)" in source


def test_saved_session_restores_before_provider_refresh() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    restore = source.split("async function restoreSavedSession()", 1)[1].split(
        "async function interactiveConnect()", 1
    )[0]

    product_context_index = restore.index("/api/product-context")
    apply_index = restore.index("applyConnectedContext(context)")
    refresh_index = restore.index("void refreshStoredLeague")
    assert product_context_index < apply_index < refresh_index
    assert "waitForBackgroundImport(leagueId,null,'connect')" in restore
    assert "Stale-while-revalidate" in restore


def test_session_startup_hands_durable_context_to_hosted_revalidation() -> None:
    source = open(
        "src/fsffl/product/static/session_recovery.js",
        encoding="utf-8",
    ).read()
    startup = source.rsplit("window.addEventListener('load'", 1)[1]

    assert "const restored=await fsfflRestoreSession()" in startup
    assert "if(!state.context?.league_id)" not in startup
    assert "handed it to hosted revalidation" in startup


def test_stale_while_revalidate_is_visible_and_explains_stored_state() -> None:
    recovery = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    refresh = recovery.split("async function refreshStoredLeague", 1)[1].split(
        "async function restoreSavedSession", 1
    )[0]
    checking_index = refresh.index("publishSyncState('checking')")
    refresh_index = refresh.index("waitForBackgroundImport(leagueId,null,'refresh')")
    current_index = refresh.index("publishSyncState('current')")
    stale_index = refresh.index("publishSyncState('stale'")
    assert checking_index < refresh_index < current_index < stale_index

    script = textwrap.dedent(
        r"""
        const fs=require('fs');
        const vm=require('vm');
        const assert=require('assert');
        const nodes={};
        function element(tag){
          return {
            tagName:tag.toUpperCase(), id:'', className:'', hidden:true,
            dataset:{}, attributes:{}, innerHTML:'', textContent:'',
            setAttribute(name,value){this.attributes[name]=String(value)},
            insertAdjacentElement(_where,node){if(node.id)nodes['#'+node.id]=node},
          };
        }
        const topbar=element('div');
        const head={appendChild(node){if(node.id)nodes['#'+node.id]=node}};
        global.document={
          head,
          querySelector(selector){
            if(selector==='.topbar')return topbar;
            return nodes[selector]||null;
          },
          createElement:element,
        };
        global.window={addEventListener(){},fsfflPendingSyncState:null};
        vm.runInThisContext(fs.readFileSync('src/fsffl/product/static/phase1_sync_state.js','utf8'));
        const expected={
          checking:['Checking league updates','Stored league is usable while Sleeper is revalidated.'],
          current:['League data current','Latest provider check completed successfully.'],
          stale:['Using stored league','Your last valid stored league remains usable.'],
        };
        for(const [state,[title,copy]] of Object.entries(expected)){
          window.fsfflSyncState.set(state);
          const node=nodes['#fsffl-sync-state'];
          assert(node,'sync-state node should be rendered');
          assert.strictEqual(node.attributes.role,'status');
          assert.strictEqual(node.attributes['aria-live'],'polite');
          assert.strictEqual(node.dataset.state,state);
          assert.strictEqual(node.hidden,false);
          assert(node.innerHTML.includes(title));
          assert(node.innerHTML.includes(copy));
        }
        window.fsfflSyncState.clear();
        assert.strictEqual(nodes['#fsffl-sync-state'].hidden,true);
        """
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_hosted_refresh_only_rebuilds_behavior_when_material_state_changed() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    refresh = source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split('@application.get("/api/connect/sleeper/background/current")', 1)[0]

    assert "league_material_fingerprint" in refresh
    assert "changed =" in refresh
    assert "runtime_store.set_league_state_if_generation" in refresh
    assert "if changed:" in refresh
    assert "behavioral_coordinator.start" in refresh


def test_hosted_connect_persists_partial_state_off_request_path() -> None:
    source = open(
        "src/fsffl/product/persistent_runtime.py",
        encoding="utf-8",
    ).read()

    set_state = source.split("def set_league_state", 1)[1].split("def set_forecast_evidence", 1)[0]
    assert "self._checkpoint_async(user_id, context)" in set_state
    assert "ThreadPoolExecutor" in source
    assert "max_workers=1" in source
    assert "self._checkpoint_executor_for(user_id).submit" in source
    assert "_retire_checkpoint_executor" in source
    assert "context.forecast_evidence is not None" not in source
    assert "context.simulation_analytics is not None" not in source
    assert "context.value_evidence is not None" not in source


def test_hosted_connect_reuses_restored_matching_league_before_provider_reload() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()

    assert "already_loaded = _matches_sleeper_league" in source
    assert "if already_loaded:" in source
    assert "return" in source.split("if already_loaded:", 1)[1].split("league_state = state_loader", 1)[0]


def test_mobile_connect_commits_league_after_identity_and_requires_fresh_team_choice() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    previous_index = interactive.index("const previousLeagueId=localStorage.getItem(LEAGUE_KEY)")
    feedback_index = interactive.index("button.textContent='Starting import…'")
    canonical_index = interactive.index("canonicalBefore=await resilientApi('/api/product-context'")
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    verify_index = interactive.index("if(!contextMatchesLeague(context,normalized)||!context?.state_id)")
    save_index = interactive.index("localStorage.setItem(LEAGUE_KEY,normalized)")
    clear_team_index = interactive.index("localStorage.removeItem(TEAM_KEY)", save_index)
    apply_index = interactive.index("applyConnectedContext(context)")
    assert previous_index < feedback_index < canonical_index < wait_index < verify_index < save_index < clear_team_index < apply_index
    assert "restoreSelectedTeam(context,canonicalBefore)" not in interactive
    assert "League is ready. Select the franchise you manage to continue." in interactive
    assert "if(previousLeagueId===null)localStorage.removeItem(LEAGUE_KEY)" in interactive
    assert "else localStorage.setItem(LEAGUE_KEY,previousLeagueId)" in interactive
    assert "if(previousTeamId===null)localStorage.removeItem(TEAM_KEY)" in interactive
    assert "else localStorage.setItem(TEAM_KEY,previousTeamId)" in interactive


def test_hosted_connect_validates_requested_identity_and_blocks_superseded_write() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]
    refresh = source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split('@application.get("/api/connect/sleeper/background/current")', 1)[0]

    assert "if not _matches_sleeper_league(league_state, league_external_id)" in connect
    assert "if not _matches_sleeper_league(league_state, league_external_id)" in refresh
    assert "current_job = jobs.current(user_id)" in connect
    assert "current_job = jobs.current(user_id)" in refresh
    assert "current_job.league_external_id != league_external_id" in connect
    assert "current_job.league_external_id != league_external_id" in refresh


def test_current_static_release_busts_first_load_recovery_cache() -> None:
    source = open("src/fsffl/product/static/index.html", encoding="utf-8").read()
    hotfix = "20260928-first-load-recovery1"
    base = "20260927-market-nonblocking1"
    assert f"mobile_safari_recovery.js?v={base}&r={hotfix}" in source
    assert f"forecast_refresh.js?v={base}&r={hotfix}" in source


def test_hosted_connect_completes_from_in_memory_state_without_checkpoint_wait() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]
    activate_index = connect.index('"activate_league_state_for_connect"')
    verify_index = connect.index("active_state = runtime_store.get(user_id).league_state")
    behavioral_index = connect.index("behavioral_coordinator.start")
    reconcile_index = connect.index("intelligence_reconciler(user_id)", behavioral_index)
    assert activate_index < verify_index < behavioral_index < reconcile_index
    assert "wait_for_checkpoint" not in connect
    assert "Sleeper league activation could not be durably checkpointed" not in connect
    assert 'raise RuntimeError("Sleeper league activation lost requested identity")' in connect


def test_hosted_refresh_is_bound_to_starting_league_generation() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    refresh = source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split('@application.get("/api/connect/sleeper/background/current")', 1)[0]

    capture_index = refresh.index("refresh_generation = runtime_store.league_generation(user_id)")
    guard_index = refresh.index("runtime_store.league_generation(user_id) != refresh_generation")
    active_index = refresh.index("not _matches_sleeper_league(active_state, league_external_id)")
    write_index = refresh.index("runtime_store.set_league_state_if_generation(")
    assert capture_index < guard_index < write_index
    assert capture_index < active_index < write_index
    assert "FSFFL Sleeper refresh superseded before activation" in refresh
    assert "expected_generation=refresh_generation" in refresh
    assert "FSFFL Sleeper refresh superseded at activation" in refresh


def test_manual_connect_acknowledges_before_context_read_and_rejects_same_active_league() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    active_index = interactive.index("const activeBefore=")
    feedback_index = interactive.index("button.textContent='Starting import…'")
    canonical_index = interactive.index("canonicalBefore=await resilientApi('/api/product-context'")
    same_index = interactive.index("if(contextMatchesLeague(canonicalBefore,normalized))")
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    assert active_index < feedback_index < canonical_index < same_index < wait_index
    assert "publishSyncState('checking','Starting import…')" in interactive
    assert "same_active" in interactive
    assert "Enter a different league ID to switch leagues." in interactive
    assert "'requested='+normalized+';active='" in interactive


def test_connect_request_target_is_emitted_on_visible_performance_logger() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]
    assert '_performance_logger = logging.getLogger("fsffl.product.performance")' in source
    assert "FSFFL Sleeper connect request user=%s requested=%s active=%s already_loaded=%s" in connect


def test_saved_team_restore_is_exact_session_only_and_manual_switch_stays_unselected() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    helper = source.split("async function restoreSelectedTeam", 1)[1].split(
        "async function refreshStoredLeague", 1
    )[0]
    restore = source.split("async function restoreSavedSession()", 1)[1].split(
        "async function interactiveConnect()", 1
    )[0]
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    assert "localStorage.getItem(TEAM_KEY)" in helper
    assert "(context.teams||[]).some(team=>team.team_id===teamId)" in helper
    assert "resilientApi('/api/select-team'" in helper
    assert "previousName" not in helper
    assert "matches.length" not in helper
    assert "restoreSelectedTeam(context)" in restore
    assert "restoreSelectedTeam(" not in interactive
    assert "localStorage.removeItem(TEAM_KEY)" in interactive
    assert "applyConnectedContext(context)" in interactive
    assert "League is ready. Select the franchise you manage to continue." in interactive


def test_hosted_switch_activates_state_before_starting_intelligence_reconciliation() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]

    state_index = connect.index('"activate_league_state_for_connect"')
    verify_index = connect.index("active_state = runtime_store.get(user_id).league_state")
    reconcile_index = connect.index("intelligence_reconciler(user_id)", verify_index)
    assert state_index < verify_index < reconcile_index
    assert "wait_for_checkpoint" not in connect
    assert "intelligence_reconciler" in connect


def test_hosted_refresh_reconciles_missing_intelligence_even_when_state_probe_is_unchanged() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    refresh = source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split('@application.get("/api/connect/sleeper/background/current")', 1)[0]

    reused = refresh.split(
        "FSFFL Sleeper incremental sync reused stored state", 1
    )[1].split("except Exception as exc", 1)[0]
    assert "intelligence_reconciler(user_id)" in reused
    activated = refresh.split(
        "runtime_store.set_league_state_if_generation(", 1
    )[1]
    assert "intelligence_reconciler(user_id)" in activated



def test_market_context_guard_accepts_only_governed_stale_presentation_contract() -> None:
    shell = open(
        "src/fsffl/product/static/product_shell.js",
        encoding="utf-8",
    ).read()
    opportunities = open(
        "src/fsffl/product/static/opportunities.js",
        encoding="utf-8",
    ).read()

    assert "function fsfflPresentationPayloadMatchesContext" in shell
    assert "freshness.status==='stale_last_good'" in shell
    assert "continuity.mode==='stale_last_good'" in shell
    assert "continuity.target_league_state_id===context.state_id" in shell
    assert "window.fsfflPresentationPayloadMatchesContext" in opportunities



def test_shared_postgres_state_upserts_reject_older_cross_user_writes() -> None:
    source = open(
        "src/fsffl/persistence/postgres.py",
        encoding="utf-8",
    ).read()

    league = source.split("def put_league_snapshot", 1)[1].split(
        "def get_team_snapshot", 1
    )[0]
    team = source.split("def put_team_snapshot", 1)[1].split(
        "def get_sync_cursor", 1
    )[0]

    assert "fsffl.league_snapshot.source_updated_at" in league
    assert "excluded.recorded_at >= fsffl.league_snapshot.recorded_at" in league
    assert "fsffl.team_snapshot.source_updated_at" in team
    assert "excluded.recorded_at >= fsffl.team_snapshot.recorded_at" in team


def test_fresh_hosted_connect_defers_intelligence_until_team_identity_exists() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]

    assert "active_runtime = runtime_store.get(user_id)" in connect
    assert "active_runtime.selected_team_id is not None" in connect
    assert "deferred intelligence until managed-team selection" in connect


def test_explicit_team_selection_hands_off_to_intelligence_without_silent_team_restore() -> None:
    app = open("src/fsffl/product/static/app.js", encoding="utf-8").read()
    refresh = open(
        "src/fsffl/product/static/forecast_refresh.js",
        encoding="utf-8",
    ).read()
    mobile = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    select = app.split("async function selectTeam(teamId)", 1)[1].split(
        "function wireConnectButton", 1
    )[0]
    assert "api('/api/select-team'" in select
    assert "applyContext()" in select
    assert "window.fsfflEnsureIntelligenceAfterTeamSelection?.()" in select
    assert "window.fsfflEnsureIntelligenceAfterTeamSelection=()=>{" in refresh
    assert "fsfflSettledStateId=null" in refresh
    assert "maybeStartIntelligenceJob({manual:false})" in refresh

    interactive = mobile.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]
    assert "localStorage.removeItem(TEAM_KEY)" in interactive
    assert "restoreSelectedTeam(" not in interactive
