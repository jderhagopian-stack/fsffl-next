from __future__ import annotations

import subprocess
import textwrap
from datetime import UTC, datetime, timedelta
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.hosted_connect import (
    LeagueConnectCoordinator,
    LeagueConnectStatus,
    install_hosted_connect_routes,
)
from fsffl.product.persistent_webapp import app
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.persistence import SyncCursorRecord
from fsffl.providers.sleeper_live import SleeperSyncProbe
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


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
    assert "current.status==='failed'&&current.operation===operation" in source
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


def test_true_clean_browser_connect_uses_state_without_silent_team_selection() -> None:
    script = textwrap.dedent(
        r"""
        const fs=require('fs');
        const vm=require('vm');
        const assert=require('assert');

        const storage=new Map();
        global.localStorage={
          getItem(key){return storage.has(key)?storage.get(key):null},
          setItem(key,value){storage.set(key,String(value))},
          removeItem(key){storage.delete(key)},
        };

        function selectNode(){
          const node={children:[],disabled:true};
          Object.defineProperty(node,'innerHTML',{
            get(){return ''},
            set(_value){node.children=[]},
          });
          node.appendChild=child=>node.children.push(child);
          return node;
        }

        const sync=[];
        const button={disabled:false,textContent:'Connect Sleeper League'};
        const leagueSelect=selectNode();
        const teamSelect=selectNode();
        let clickHandler=null;
        global.document={
          visibilityState:'visible',
          querySelector(selector){
            if(selector==='#connect-button')return button;
            if(selector==='#league-select')return leagueSelect;
            if(selector==='#team-select')return teamSelect;
            if(selector.startsWith('script[data-fsffl-'))return {};
            return null;
          },
          createElement(tag){
            if(tag==='option')return {value:'',textContent:''};
            throw new Error('unexpected element '+tag);
          },
          head:{appendChild(){}},
          addEventListener(type,handler,options){
            if(type==='click'){
              clickHandler=handler;
              assert.strictEqual(options,true,'manual Connect must own capture phase');
            }
          },
        };
        global.CustomEvent=class{constructor(type,init){this.type=type;this.detail=init?.detail}};
        global.window={
          performance:{now:()=>1},
          prompt:()=> '123',
          alert(message){throw new Error('unexpected alert: '+message)},
          dispatchEvent(event){if(event.type==='fsffl:sync-state')sync.push(event.detail)},
          addEventListener(){},
          fsfflSyncState:{set(state,message){sync.push({state,message})}},
        };
        global.fetch=()=>Promise.resolve({ok:true});
        global.state={
          context:{
            league_id:'sleeper:123',
            league_name:'Clean League',
            state_id:'state-known-but-not-rendered',
            teams:[],
            team_id:null,
          },
          teamView:null,valueCatalog:null,intelligence:null,route:'league',
        };
        global.applyContext=()=>{
          const context=state.context;
          leagueSelect.innerHTML='';
          const leagueOption=document.createElement('option');
          leagueOption.value=context?.league_id||'';
          leagueOption.textContent=context?.league_id
            ?(context.league_name||context.league_id)
            :'Connect league';
          leagueSelect.appendChild(leagueOption);
          teamSelect.innerHTML='';
          const empty=document.createElement('option');
          empty.value='';
          empty.textContent='Select team';
          teamSelect.appendChild(empty);
          for(const team of context?.teams||[]){
            const option=document.createElement('option');
            option.value=team.team_id;
            option.textContent=team.display_name;
            teamSelect.appendChild(option);
          }
          teamSelect.disabled=!context?.league_id;
        };
        // Intentionally do not apply the already-known context. This reproduces
        // a Safari shell whose JS identity is current while the visible controls are stale.

        const calls=[];
        let backgroundPosted=false;
        global.api=async(path,options={})=>{
          calls.push([path,options.method||'GET']);
          if(path==='/api/connect/sleeper/background/current')return {};
          if(path==='/api/connect/sleeper/background'&&options.method==='POST'){
            backgroundPosted=true;
            return {status:'running',league_external_id:'123',operation:'connect'};
          }
          if(path==='/api/product-context'){
            assert(backgroundPosted,'visible context must be recognized after background submission');
            return {
              league_id:'sleeper:123',
              league_name:'Clean League',
              state_id:'state-clean',
              teams:[
                {team_id:'team:a',display_name:'A'},
                {team_id:'team:b',display_name:'B'},
              ],
              team_id:null,
            };
          }
          throw new Error('unexpected api '+path);
        };

        vm.runInThisContext(
          fs.readFileSync('src/fsffl/product/static/mobile_safari_recovery.js','utf8')
        );
        assert(clickHandler,'connect click handler must install');

        let prevented=false;
        let stopped=false;
        clickHandler({
          target:{closest(selector){return selector==='#connect-button'?button:null}},
          preventDefault(){prevented=true},
          stopImmediatePropagation(){stopped=true},
        });

        setTimeout(()=>{
          try{
            assert.strictEqual(prevented,true);
            assert.strictEqual(stopped,true);
            const postIndex=calls.findIndex(([path,method])=>
              path==='/api/connect/sleeper/background'&&method==='POST'
            );
            const contextIndex=calls.findIndex(([path])=>path==='/api/product-context');
            assert(postIndex>=0,'physical tap must submit the background Connect request');
            assert(contextIndex>postIndex,'manual Connect must not context-preflight before submission');
            assert.strictEqual(
              calls.some(([path])=>path==='/api/connect/sleeper'),
              false,
              'capture-phase mobile handler must suppress the synchronous base Connect route'
            );
            assert.strictEqual(state.context.league_id,'sleeper:123');
            assert.strictEqual(state.context.state_id,'state-clean');
            assert.strictEqual(state.context.team_id,null);
            assert.strictEqual(localStorage.getItem('fsffl:last-sleeper-league'),'123');
            assert.strictEqual(localStorage.getItem('fsffl:last-team'),null);
            assert.strictEqual(leagueSelect.children[0].value,'sleeper:123');
            assert.strictEqual(leagueSelect.children[0].textContent,'Clean League');
            assert.strictEqual(teamSelect.disabled,false);
            assert.deepStrictEqual(
              teamSelect.children.map(item=>item.textContent),
              ['Select team','A','B'],
              'canonical State must become visible in the team-selection UI'
            );
            assert(
              sync.some(item=>item.state==='checking'&&item.message==='Starting import…'),
              'tap must produce immediate visible feedback'
            );
            assert(
              sync.some(item=>item.state==='current'&&String(item.message||'').includes('Select the franchise')),
              'State-ready UI must ask for explicit team choice'
            );
            process.exit(0);
          }catch(error){
            console.error(error);
            process.exit(1);
          }
        },25);
        """
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert completed.returncode == 0, completed.stderr

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


def test_hosted_refresh_uses_material_change_as_the_state_activation_boundary() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    refresh = source.split(
        '@application.post("/api/connect/sleeper/background/refresh")', 1
    )[1].split('@application.get("/api/connect/sleeper/background/current")', 1)[0]

    # Capture-time churn is verification only. Material football changes still
    # activate a new canonical State and restart State-owned downstream execution.
    assert "league_material_fingerprint" in refresh
    assert "changed =" in refresh
    assert "if not changed:" in refresh
    assert "verified no material State change" in refresh
    assert "runtime_store.set_league_state_if_generation" in refresh
    assert "state_identity_changed =" in refresh
    assert "if state_identity_changed:" in refresh
    assert "behavioral_coordinator.start" in refresh


def test_hosted_refresh_retains_published_state_on_capture_only_change(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    league_id = "sleeper:123"

    def state_at(minute: int) -> LeagueState:
        return LeagueState(
            league=League(
                league_id=league_id,
                name="League 123",
                season=2026,
                rules=LeagueRules(
                    team_count=2,
                    roster_size=1,
                    lineup=(),
                    scoring=(),
                ),
            ),
            as_of=datetime(2026, 10, 1, 15, minute, tzinfo=UTC),
            teams=(
                Team(
                    team_id=f"{league_id}:team:1",
                    league_id=league_id,
                    display_name="Alpha",
                ),
                Team(
                    team_id=f"{league_id}:team:2",
                    league_id=league_id,
                    display_name="Beta",
                ),
            ),
            team_states=(
                TeamState(team_id=f"{league_id}:team:1", roster=()),
                TeamState(team_id=f"{league_id}:team:2", roster=()),
            ),
            players=(),
            player_states=(),
        )

    published = state_at(0)
    recaptured = state_at(1)
    assert published.state_id != recaptured.state_id

    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", published)
    store.select_team("local-beta-user", f"{league_id}:team:1")
    events: list[str] = []

    class Behavioral:
        def start(self, **_kwargs):
            events.append("behavior")

    application = FastAPI()
    coordinator = install_hosted_connect_routes(
        application,
        runtime_store=store,
        state_loader=lambda _external_id: recaptured,
        behavioral_coordinator=Behavioral(),  # type: ignore[arg-type]
        intelligence_reconciler=lambda _user_id: events.append("intelligence"),
    )
    client = TestClient(application)
    response = client.post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "123"},
    )
    assert response.status_code == 200

    deadline = monotonic() + 2.0
    current = None
    while monotonic() < deadline:
        current = coordinator.current("local-beta-user")
        if current is not None and current.status in {
            LeagueConnectStatus.COMPLETED,
            LeagueConnectStatus.FAILED,
        }:
            break
        sleep(0.01)
    assert current is not None and current.status == LeagueConnectStatus.COMPLETED
    retained = store.get("local-beta-user")
    assert retained.league_state is published
    assert retained.league_state.state_id == published.state_id
    assert events == ["intelligence"]


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
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    verify_index = interactive.index("if(!contextMatchesLeague(context,normalized)||!context?.state_id)")
    save_index = interactive.index("localStorage.setItem(LEAGUE_KEY,normalized)")
    clear_team_index = interactive.index("localStorage.removeItem(TEAM_KEY)", save_index)
    apply_index = interactive.index("applyConnectedContext(context)")
    assert previous_index < feedback_index < wait_index < verify_index < save_index < clear_team_index < apply_index
    assert "canonicalBefore" not in interactive
    assert "if(activeBefore===normalized)" not in interactive
    assert "restoreSelectedTeam(" not in interactive
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


def test_physical_connect_busts_hosted_release_cache_coherently() -> None:
    source = open("src/fsffl/product/static/index.html", encoding="utf-8").read()
    release = "20260929-physical-connect1"
    for asset in ("app.js", "mobile_safari_recovery.js", "forecast_refresh.js"):
        assert f"/static/{asset}?v={release}" in source
    versions = {
        token.split("?v=")[1].split('"')[0].split("&")[0]
        for token in source.split()
        if "?v=" in token
    }
    assert versions == {release}


def test_hosted_connect_completes_from_in_memory_state_without_checkpoint_wait() -> None:
    source = open(
        "src/fsffl/product/hosted_connect.py",
        encoding="utf-8",
    ).read()
    connect = source.split(
        '@application.post("/api/connect/sleeper/background")', 1
    )[1].split('@application.post("/api/connect/sleeper/background/refresh")', 1)[0]

    lifecycle_index = connect.index("with runtime_store.lifecycle_operation(user_id):")
    activate_index = connect.index('"activate_league_state_for_connect"')
    active_runtime_index = connect.index("active_runtime = runtime_store.get(user_id)")
    state_verify_index = connect.index("active_state.state_id != league_state.state_id")
    behavioral_index = connect.index("behavioral_coordinator.start")
    ownership_verify_index = connect.index(
        "active_runtime.league_state.state_id != league_state.state_id",
        behavioral_index,
    )
    reconcile_index = connect.index("intelligence_reconciler(user_id)", ownership_verify_index)

    assert (
        lifecycle_index
        < activate_index
        < active_runtime_index
        < state_verify_index
        < behavioral_index
        < ownership_verify_index
        < reconcile_index
    )
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


def test_manual_connect_always_runs_idempotent_background_handoff() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js",
        encoding="utf-8",
    ).read()
    interactive = source.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]

    active_index = interactive.index("const activeBefore=")
    feedback_index = interactive.index("button.textContent='Starting import…'")
    wait_index = interactive.index("await waitForBackgroundImport(normalized")
    assert active_index < feedback_index < wait_index
    assert "publishSyncState('checking','Starting import…')" in interactive
    assert "canonicalBefore" not in interactive
    assert "if(activeBefore===normalized)" not in interactive
    assert "same_visible_active" not in interactive
    assert "contextMatchesLeague(canonicalBefore,normalized)" not in interactive
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

    lifecycle_index = connect.index("with runtime_store.lifecycle_operation(user_id):")
    state_index = connect.index('"activate_league_state_for_connect"')
    verify_index = connect.index("active_state.state_id != league_state.state_id")
    behavior_index = connect.index("behavioral_coordinator.start")
    reconcile_index = connect.index("intelligence_reconciler(user_id)", behavior_index)

    assert lifecycle_index < state_index < verify_index < behavior_index < reconcile_index
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
    assert "maintainFsfflIntelligence()" in refresh
    assert "maybeStartIntelligenceJob({manual:false})" not in refresh.split(
        "window.fsfflEnsureIntelligenceAfterTeamSelection=()=>{", 1
    )[1].split("window.addEventListener('load'", 1)[0]

    webapp = open("src/fsffl/product/webapp.py", encoding="utf-8").read()
    select_route = webapp.split('@application.post("/api/select-team")', 1)[1].split(
        "def _start_intelligence_reconciliation", 1
    )[0]
    assert "_start_intelligence_reconciliation(" in select_route
    assert "sync_state=False" in select_route

    interactive = mobile.split("async function interactiveConnect()", 1)[1].split(
        "window.fsfflRestoreSession=restoreSavedSession", 1
    )[0]
    assert "localStorage.removeItem(TEAM_KEY)" in interactive
    assert "restoreSelectedTeam(" not in interactive



def test_repeated_cross_league_connect_reclaims_before_next_heavy_handoff(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")

    def state(external_id: str) -> LeagueState:
        league_id = f"sleeper:{external_id}"
        return LeagueState(
            league=League(
                league_id=league_id,
                name=f"League {external_id}",
                season=2026,
                rules=LeagueRules(
                    team_count=2,
                    roster_size=1,
                    lineup=(),
                    scoring=(),
                ),
            ),
            as_of=datetime(2026, 9, 29, tzinfo=UTC),
            teams=(
                Team(
                    team_id=f"{league_id}:team:1",
                    league_id=league_id,
                    display_name=f"Team {external_id} A",
                ),
                Team(
                    team_id=f"{league_id}:team:2",
                    league_id=league_id,
                    display_name=f"Team {external_id} B",
                ),
            ),
            team_states=(
                TeamState(
                    team_id=f"{league_id}:team:1",
                    roster=(),
                ),
                TeamState(
                    team_id=f"{league_id}:team:2",
                    roster=(),
                ),
            ),
            players=(),
            player_states=(),
        )

    states = {external_id: state(external_id) for external_id in ("a", "b")}
    store = PrivateBetaRuntimeStore()
    events: list[tuple[str, str]] = []

    class Behavioral:
        def start(self, *, league_state, **_kwargs):
            events.append(("behavior", league_state.league.league_id))

    def reclaim(label: str):
        active = store.get("local-beta-user").league_state
        events.append(
            (
                "reclaim",
                f"{active.league.league_id if active is not None else 'none'}:{label}",
            )
        )
        return {"label": label, "cleared_execution_caches": {"workspace": 1}}

    application = FastAPI()
    coordinator = install_hosted_connect_routes(
        application,
        runtime_store=store,
        state_loader=lambda external_id: states[external_id],
        behavioral_coordinator=Behavioral(),  # type: ignore[arg-type]
        intelligence_reconciler=lambda _user_id: events.append(("intelligence", "start")),
        state_transition_reclaimer=reclaim,
    )
    client = TestClient(application)

    def connect(external_id: str) -> None:
        response = client.post(
            "/api/connect/sleeper/background",
            json={"league_external_id": external_id},
        )
        assert response.status_code == 200
        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            current = coordinator.current("local-beta-user")
            if current is not None and current.status in {
                LeagueConnectStatus.COMPLETED,
                LeagueConnectStatus.FAILED,
            }:
                assert current.status == LeagueConnectStatus.COMPLETED, current.error
                return
            sleep(0.01)
        raise AssertionError("background connect did not finish")

    connect("a")
    events.clear()
    connect("b")
    connect("a")

    reclaims = [event for event in events if event[0] == "reclaim"]
    assert len(reclaims) == 2
    assert reclaims[0][1].startswith("sleeper:b:")
    assert reclaims[1][1].startswith("sleeper:a:")

    # For each switch the old execution cache is reclaimed after new State activation
    # and before any new league behavioral/heavy handoff begins.
    first_reclaim = events.index(reclaims[0])
    first_behavior = next(
        index
        for index, event in enumerate(events)
        if event == ("behavior", "sleeper:b")
    )
    second_reclaim = events.index(reclaims[1])
    second_behavior = next(
        index
        for index, event in enumerate(events)
        if event == ("behavior", "sleeper:a")
    )
    assert first_reclaim < first_behavior
    assert second_reclaim < second_behavior


def test_session_restore_freshness_read_reuses_governed_cursor_before_refresh(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    league_id = "sleeper:restore-freshness"
    external_id = "restore-freshness"
    league_state = LeagueState(
        league=League(
            league_id=league_id,
            name="Freshness league",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=datetime(2026, 10, 4, tzinfo=UTC),
        teams=(
            Team(team_id=f"{league_id}:team:1", league_id=league_id, display_name="Alpha"),
            Team(team_id=f"{league_id}:team:2", league_id=league_id, display_name="Beta"),
        ),
        team_states=(
            TeamState(team_id=f"{league_id}:team:1", roster=()),
            TeamState(team_id=f"{league_id}:team:2", roster=()),
        ),
        players=(),
        player_states=(),
    )
    now = datetime.now(UTC)

    class Persistence:
        def __init__(self, cursor):
            self.cursor = cursor

        def get_sync_cursor(self, **_kwargs):
            return self.cursor

    def make_cursor(last_full_refresh_at, fingerprint="fingerprint-current"):
        return SyncCursorRecord(
            provider="sleeper",
            scope_kind="league_refresh",
            scope_id=external_id,
            cursor_payload={
                "probe_fingerprint": fingerprint,
                "season": 2026,
                "week": 5,
                "last_full_refresh_at": last_full_refresh_at.isoformat(),
            },
            synced_at=last_full_refresh_at,
        )

    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", league_state)
    store.select_team("local-beta-user", f"{league_id}:team:1")
    probe_calls = []

    def probe(_league):
        probe_calls.append(True)
        return SleeperSyncProbe(
            league_external_id=external_id,
            captured_at=now,
            season=2026,
            week=5,
            fingerprint="fingerprint-current",
        )

    def client_for(cursor, probe_loader=probe, coordinator=None):
        application = FastAPI()
        install_hosted_connect_routes(
            application,
            runtime_store=store,
            state_loader=lambda _league: league_state,
            behavioral_coordinator=SimpleNamespace(start=lambda **_kwargs: None),
            coordinator=coordinator,
            persistence_store=Persistence(cursor),  # type: ignore[arg-type]
            sync_probe_loader=probe_loader,
            full_refresh_seconds=3600,
        )
        return TestClient(application)

    current = client_for(make_cursor(now)).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert current.status_code == 200
    assert current.json() == {"refresh_due": False, "reason": "provider_current"}
    assert len(probe_calls) == 1

    in_progress = client_for(
        make_cursor(now),
        coordinator=SimpleNamespace(
            current=lambda _user: SimpleNamespace(
                league_external_id=external_id,
                operation="refresh",
                status=LeagueConnectStatus.RUNNING,
            )
        ),
    ).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert in_progress.status_code == 200
    assert in_progress.json() == {
        "refresh_due": False,
        "refresh_in_progress": True,
        "reason": "refresh_in_progress",
    }

    connect_in_progress = client_for(
        make_cursor(now),
        coordinator=SimpleNamespace(
            current=lambda _user: SimpleNamespace(
                league_external_id=external_id,
                operation="connect",
                status=LeagueConnectStatus.RUNNING,
            )
        ),
    ).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert connect_in_progress.status_code == 200
    assert connect_in_progress.json() == {
        "refresh_due": False,
        "reason": "provider_current",
    }
    assert len(probe_calls) == 2

    changed_probe = client_for(make_cursor(now), lambda _league: SleeperSyncProbe(
        league_external_id=external_id,
        captured_at=now,
        season=2026,
        week=5,
        fingerprint="provider-changed",
    )).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert changed_probe.json() == {"refresh_due": True, "reason": "provider_probe_changed"}
    # A cheap probe/cursor error is unknown, not a license to start the expensive path.
    unknown = client_for(make_cursor(now), lambda _league: (_ for _ in ()).throw(OSError("offline"))).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert unknown.json() == {"refresh_due": False, "reason": "freshness_unavailable"}

    due = client_for(make_cursor(now - timedelta(hours=2))).get(
        "/api/connect/sleeper/background/freshness",
        params={"league_external_id": external_id},
    )
    assert due.status_code == 200
    assert due.json() == {"refresh_due": True, "reason": "full_refresh_due"}


def test_saved_session_restore_is_read_first_and_keeps_missing_state_fallback() -> None:
    source = open(
        "src/fsffl/product/static/mobile_safari_recovery.js", encoding="utf-8"
    ).read()
    restore = source.split("async function restoreSavedSession()", 1)[1].split(
        "async function interactiveConnect()", 1
    )[0]
    assert "refreshStoredLeagueIfDue(leagueId,context.state_id)" in restore
    assert "waitForBackgroundImport(leagueId,null,'connect')" in restore
    assert "if(freshness?.refresh_in_progress===true)" in source
    assert "if(freshness?.refresh_due===true)void refreshStoredLeague(leagueId,latestStateId)" in source
    assert "waitForBackgroundImport(leagueId,null,'refresh')" in source
    assert "function refreshStoredLeagueIfDue" in source


def test_saved_session_restore_only_posts_provider_refresh_when_freshness_is_due() -> None:
    script = r"""
      const fs=require('fs'),vm=require('vm'),assert=require('assert');
      const condition=process.argv[1],due=condition==='due',inProgress=condition==='in-progress',completedBeforeCheck=condition==='completed-before-check',attachCompleted=condition==='attach-completed',attachFailed=condition==='attach-failed',storage=new Map([['fsffl:last-sleeper-league','123']]),calls=[];
      let currentReads=0,contextReads=0;const syncStates=[];
      global.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,String(value)),removeItem:key=>storage.delete(key)};
      global.document={visibilityState:'visible',querySelector:()=>null,createElement:tag=>({tagName:tag,dataset:{}}),head:{appendChild(){}},addEventListener(){}};
      global.CustomEvent=class{constructor(type,init){this.type=type;this.detail=init?.detail}};
      global.window={performance:{now:()=>1},addEventListener(){},dispatchEvent(){},fsfflEnsureIntelligenceAfterTeamSelection(){},fsfflSyncState:{set(status){syncStates.push(status)}}};
      global.state={context:null,teamView:null,valueCatalog:null,intelligence:null,route:'league'};
      global.applyContext=()=>{};global.fetch=()=>Promise.resolve({ok:true});
      global.api=async(path,options={})=>{
        calls.push([path,options.method||'GET']);
        if(path==='/api/product-context'){contextReads+=1;const advanced=completedBeforeCheck?contextReads>1:inProgress?contextReads>1:attachCompleted?contextReads>1:false;return{league_id:'sleeper:123',state_id:advanced?'state-2':'state-1',teams:[],team_id:null};}
        if(path.startsWith('/api/connect/sleeper/background/freshness?'))return{refresh_due:due,refresh_in_progress:inProgress||attachCompleted||attachFailed,reason:due?'full_refresh_due':(inProgress||attachCompleted||attachFailed)?'refresh_in_progress':'provider_current'};
        if(path==='/api/connect/sleeper/background/current')return inProgress?(++currentReads===1?{league_external_id:'123',status:'running',operation:'refresh'}:{league_external_id:'123',status:'completed',operation:'refresh'} ):attachCompleted?{league_external_id:'123',status:'completed',operation:'refresh'}:attachFailed?{league_external_id:'123',status:'failed',operation:'refresh',error:'provider refresh failed'}:{};
        if(path==='/api/connect/sleeper/background/refresh'&&options.method==='POST')return{status:'completed',operation:'refresh',league_external_id:'123'};
        throw new Error('unexpected API '+path);
      };
      vm.runInThisContext(fs.readFileSync('src/fsffl/product/static/mobile_safari_recovery.js','utf8'));
      (async()=>{
        assert.strictEqual(await window.fsfflRestoreSession(),true);
        await new Promise(resolve=>setTimeout(resolve,inProgress?900:20));
        const refreshPosts=calls.filter(([path,method])=>path==='/api/connect/sleeper/background/refresh'&&method==='POST');
        assert.strictEqual(refreshPosts.length,due?1:0,'only governed due freshness may launch a new provider POST');
        assert.strictEqual(calls.some(([path])=>path==='/api/connect/sleeper/background/freshness?league_external_id=123'),true);
        if(!attachFailed)assert.strictEqual(calls.filter(([path])=>path==='/api/product-context').length>=2,true,'a bounded post-freshness or job-completion context read reconciles State');
        if(inProgress||attachCompleted)assert.strictEqual(state.context.state_id,'state-2','restored session attaches to active or just-completed refresh and adopts the new context');
        if(completedBeforeCheck)assert.strictEqual(state.context.state_id,'state-2','restored session reconciles an already-completed refresh without reposting');
        if(attachFailed)assert.strictEqual(syncStates.includes('stale'),true,'failed attached refresh remains visible as stale');
      })().catch(error=>{console.error(error);process.exitCode=1});
    """
    for condition in ("current", "due", "in-progress", "completed-before-check", "attach-completed", "attach-failed"):
        completed = subprocess.run(
            ["node", "-e", script, condition],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert completed.returncode == 0, completed.stderr
