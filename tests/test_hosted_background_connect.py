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


def test_mobile_connect_is_single_flight_and_recovers_existing_job_before_starting() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()

    assert "let activeConnectPromise=null" in source
    assert "let activeLeagueId=null" in source
    assert "let activeOperation=null" in source
    assert "activeConnectPromise&&" in source
    assert "activeLeagueId===leagueId" in source
    assert "activeOperation===operation" in source
    assert "const existing=await recoverCurrentJob(leagueId,operation)" in source
    assert "['queued','running'].includes(existing.status)" in source


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
