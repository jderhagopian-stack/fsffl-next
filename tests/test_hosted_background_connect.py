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


def test_mobile_connect_has_one_poll_owner_and_requires_terminal_connect_success() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "let activeConnectPromise=null" in source
    assert "let activeLeagueId=null" in source
    assert "activeConnectPromise&&activeLeagueId===leagueId" in source
    assert "activeOperation" not in source
    assert "const existing=await recoverCurrentJob(leagueId,operation)" in source
    assert "['queued','running'].includes(existing.status)" in source
    assert "current.status==='completed'&&current.operation===operation" in source
    assert "const recovered=await recoverCurrentJob(leagueId,operation)" in source
    perform = source.split("async function performBackgroundImport", 1)[1].split(
        "function waitForBackgroundImport", 1
    )[0]
    assert "nextContextProbeAt" not in perform
    assert "operation==='connect'&&Date.now()" not in perform
    assert "job?.status==='completed'" in perform
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
    assert "runtime_store.set_league_state" in refresh
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
    assert "self._checkpoint_executor.submit" in source
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


def test_mobile_connect_commits_saved_league_only_after_identity_match() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    previous_index = interactive.index("const previousLeagueId=localStorage.getItem(LEAGUE_KEY)")
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    verify_index = interactive.index("if(!contextMatchesLeague(context,normalized)||!context?.state_id)")
    save_index = interactive.index("localStorage.setItem(LEAGUE_KEY,normalized)")
    apply_index = interactive.index("applyConnectedContext(context)")
    assert previous_index < wait_index < verify_index < save_index < apply_index
    assert "localStorage.setItem(LEAGUE_KEY,normalized);" not in interactive[:wait_index]
    assert "if(previousLeagueId===null)localStorage.removeItem(LEAGUE_KEY)" in interactive
    assert "else localStorage.setItem(LEAGUE_KEY,previousLeagueId)" in interactive


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


def test_current_static_release_busts_pre_identity_safe_mobile_cache() -> None:
    source = open("src/fsffl/product/static/index.html", encoding="utf-8").read()
    assert "20260925-market-discovery1" in source
    assert "mobile_safari_recovery.js?v=20260925-market-discovery1" in source


def test_hosted_connect_waits_for_serialized_persistence_before_completion() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]
    set_index = connect.index("runtime_store.set_league_state(user_id, league_state)")
    wait_index = connect.index('getattr(runtime_store, "wait_for_checkpoint", None)')
    verify_index = connect.index("active_state = runtime_store.get(user_id).league_state")
    behavioral_index = connect.index("behavioral_coordinator.start")
    assert set_index < wait_index < verify_index < behavioral_index
    assert 'raise RuntimeError("Sleeper league activation could not be durably checkpointed")' in connect
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
    write_index = refresh.index("runtime_store.set_league_state(user_id, league_state)")
    assert capture_index < guard_index < write_index
    assert capture_index < active_index < write_index
    assert "FSFFL Sleeper refresh superseded before activation" in refresh


def test_manual_connect_cannot_report_same_active_league_as_switch_success() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    active_index = interactive.index("const activeBefore=")
    canonical_index = interactive.index("canonicalBefore=await resilientApi('/api/product-context'")
    same_index = interactive.index("if(contextMatchesLeague(canonicalBefore,normalized))")
    start_index = interactive.index("interactiveConnectInFlight=true")
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    assert active_index < canonical_index < same_index < start_index < wait_index
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
