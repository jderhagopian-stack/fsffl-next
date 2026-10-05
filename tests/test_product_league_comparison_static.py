import hashlib
import re
from pathlib import Path


def test_league_comparison_consumes_authoritative_atlas_analytics_and_value_contracts() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for evidence in (
        "calculated_competitive_state",
        "expected_wins",
        "position_strengths",
        "strength_index",
        "league_rank",
        "playoff_probability",
        "preseason_expectation",
        "pick_map",
    ):
        assert evidence in source
    assert "api('/api/league/atlas')" in source
    assert "api('/api/league/team-views')" in source
    assert "function laAtlasPayloadsAligned(atlasPayload,teamViewsPayload,requestedStateId,expectedGeneration=null)" in source
    assert "League State changed while the Atlas and roster views were loading" in source
    assert "api('/api/league/value-lenses')" in source
    assert "api('/api/values')" not in source
    assert "team_cardinal_portfolios" not in source
    assert "No team Market total, team Intrinsic total" in source


def test_position_map_keeps_current_rank_and_uses_governed_dynasty_room_authority() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "Current ranks optimized-starter production for winning now" in source
    assert "Career-forward room rank; roster counts are breadth only." in source
    assert "data-position-view=\"current\"" in source
    assert "data-position-view=\"dynasty\"" in source
    assert "dynasty?laDynastyRoom(view.team_id,position):laStrength(view,position)" in source
    assert "api('/api/league/dynasty-position-rooms')" in source
    assert "raw holistic career-forward reference" in source
    assert "rostered · breadth" in source
    assert "depthBucket=player=>player.roster_slot==='IR'?'IR':player.roster_slot==='TAXI'?'TAXI':player.projected_starter?'STARTER':'BENCH'" in source
    assert "peerRooms.filter(item=>item.room_raw===row.room_raw).length" in source
    assert "api('/api/value/long-term-intrinsic-shadow-v1')" in source
    assert "Array.isArray(longTerm?.uncertainty?.long_horizon_y4_y7)" in source
    assert "longTerm?.raw_career_forward_reference" in source
    assert "Y4–Y7 marginal Shapley" in source
    assert "payload?.league_state_id!==requestedStateId" in source
    assert "longTermState==='ready'?'not reported':longTermState==='idle'?'not loaded':longTermState==='stale'" in source
    assert "longTermState==='stale'?'not loaded for this last-good state'" in source
    assert "longTermStatus==='stale'?'Long-Term Intrinsic is not loaded for this last-good State.'" in source
    assert "longTermStatus==='unavailable'?'Long-Term Intrinsic request is temporarily unavailable; reopen this detail to retry." in source
    assert "!['idle','building','unavailable'].includes(fsfflLeagueStructureState.longTermStatus)" in source
    assert source.count("fsfflLeagueStructureState.atlas?.intelligence_freshness?.stale") == 2
    assert "Current Intrinsic · " in source
    assert "Market · " in source


def test_dynasty_room_metric_is_owned_by_analytics_and_exact_state_route() -> None:
    analytics = Path("src/fsffl/analytics/dynasty_position_room.py").read_text(encoding="utf-8")
    routes = Path("src/fsffl/product/foundation4_shadow_routes.py").read_text(encoding="utf-8")
    assert "estimate.raw_career_forward_reference" in analytics
    assert "career_forward=record.contract" in routes
    assert "evidence_state_id=record.league_state_id" in routes
    assert 'payload["league_state_id"] = record.league_state_id' in routes
    assert "record.league_state_id != state.state_id" in routes
    assert "authoritative_for_product_ranking" not in analytics


def test_value_api_exposes_server_owned_team_value_portfolios_without_atlas_consuming_them() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    atlas = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert '"team_market_value_portfolios"' in source
    assert '"team_cardinal_portfolios"' in source
    assert "team_cardinal_portfolios" not in atlas


def test_league_comparison_is_wired_as_a_real_product_surface() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "league_comparison.js" in shell
    assert "renderFsfflLeagueComparison" in shell
    assert "route==='league_comparison'" in shell


def test_league_comparison_has_mobile_first_hierarchy() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    css = Path("src/fsffl/product/static/league_atlas.css").read_text(encoding="utf-8")
    assert ".league-edge-row" in source
    assert "@media(max-width:720px)" in css
    assert ".league-atlas-tabs" in css
    assert ".atlas-race-list{overflow-x:auto}" in css
    assert ".atlas-pick-table{overflow-x:auto}" in css
    assert ".atlas-outlook-list{overflow-x:auto}" in css



def test_league_atlas_explicitly_labels_stale_last_good_during_target_rebuild() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "intelligence_freshness||{}" in source
    assert "State current · last-good intelligence" in source
    assert "league-last-good-status" in source
    assert "Derived fields as of " in source
    assert "Replacement league intelligence is rebuilding." not in source


def test_current_publication_forces_one_state_safe_atlas_promotion_without_resetting_dynasty():
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    atlas = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "fsfflAtlasPromotionInFlight" in shell
    assert "fsfflAtlasPublicationPromotionTarget(state.route,context,atlas.league_state_id||null,atlas.publication_generation_id||null,fsfflAtlasPromotionGeneration)" in shell
    assert "readiness.overall_status!=='full'" in shell
    assert "publication.working_generation_active" in shell
    assert "window.renderFsfflLeagueComparison?.({force:true,expectedGeneration:generation})" in shell
    assert "One bounded retry covers a publication/read race without polling or loops." in shell
    assert "publication_generation_id:fsfflLeagueStructureState.atlas?.publication_generation_id||null" in atlas
    assert "fetchFsfflLeagueComparison({force,expectedGeneration})" in atlas
    assert "const publicationMatches=expectedGeneration===atlasGeneration" in atlas
    assert "if(!force&&publicationMatches&&fsfflLeagueStructureState.atlas" in atlas
    assert "laAtlasPayloadsAligned(results[0],results[1],stateId,expectedGeneration)" in atlas
    assert "laValueLensResponseMatches(requestId,fsfflLeagueValueLensRequestId" in atlas
    assert "laAtlasEvidenceRequestMatches(requestId,currentRequestId,requestedStateId,currentStateId,requestedGeneration,currentGeneration)" in atlas
    assert "fsfflLeagueDynastyRoomsRequestId+=1;fsfflLeagueLongTermRequestId+=1" in atlas
    assert "requestedGeneration=fsfflLeagueStructureState.atlas?.publication_generation_id||null" in atlas
    assert "laAtlasContextTarget(context,force=false,requestedGeneration=null)" in atlas
    assert "latestTarget.stateId!==stateId" in atlas
    assert "latestTarget.generationId!==expectedGeneration" in atlas
    assert "publicationMatches=expectedGeneration===atlasGeneration" in atlas
    assert "if(!stillCurrent(payload?.publication_generation_id||null))return" in atlas
    assert "fsfflLeagueStructureState.valueLenses=payload" in atlas
    assert "atlasPayload.publication_generation_id!==expectedGeneration" in atlas
    assert "positionLens:fsfflLeagueStructureState.positionLens" in atlas
    assert "fsfflLeagueStructureState.positionLens=retainedViewState?.positionLens||'current'" in atlas
    assert "if(fsfflLeagueStructureState.positionLens==='dynasty')void laLoadDynastyRooms()" in atlas


def test_atlas_publication_promotion_gate_is_generation_and_route_bound():
    import subprocess
    import textwrap

    script = textwrap.dedent(
        r"""
        const fs=require('fs'),vm=require('vm'),assert=require('assert');
        const source=fs.readFileSync('src/fsffl/product/static/product_shell.js','utf8');
        const start=source.indexOf('function fsfflAtlasPublicationPromotionTarget(');
        const end=source.indexOf('async function fsfflPromoteVisibleAtlas',start);
        assert(start>=0&&end>start,'production promotion gate must be present');
        const sandbox={window:{addEventListener:()=>{}}};
        vm.runInNewContext(source.slice(start,end)+`\nthis.pick=fsfflAtlasPublicationPromotionTarget;`,sandbox);
        const ready={state_id:'state-1',publication_generation_id:'g2',capability_readiness:{overall_status:'full',publication:{generation_id:'g2',working_generation_active:false}}};
        assert.strictEqual(sandbox.pick('league_comparison',ready,'state-1','g1',null),'g2');
        assert.strictEqual(sandbox.pick('league_comparison',ready,'state-1','g2',null),null);
        assert.strictEqual(sandbox.pick('league_comparison',ready,'state-1','g1','state-1|g2'),null);
        assert.strictEqual(sandbox.pick('league_comparison',ready,'state-2','g2',null),'g2');
        assert.strictEqual(sandbox.pick('league',ready,'state-1','g1',null),null);
        assert.strictEqual(sandbox.pick('league_comparison',{...ready,capability_readiness:{...ready.capability_readiness,overall_status:'rebuilding'}},'state-1','g1',null),null);
        assert.strictEqual(sandbox.pick('league_comparison',{...ready,capability_readiness:{overall_status:'full',publication:{generation_id:'g2',working_generation_active:true}}},'state-1','g1',null),null);
        """
    )
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr


def test_atlas_load_rejects_cross_generation_payload_pairs():
    import subprocess
    import textwrap

    script = textwrap.dedent(
        r"""
        const fs=require('fs'),vm=require('vm'),assert=require('assert');
        const source=fs.readFileSync('src/fsffl/product/static/league_comparison.js','utf8');
        const start=source.indexOf('function laAtlasPayloadsAligned(');
        const end=source.indexOf('async function loadFsfflLeagueComparison',start);
        assert(start>=0&&end>start,'production payload alignment guard must exist');
        const sandbox={window:{addEventListener:()=>{}}};
        vm.runInNewContext(source.slice(start,end)+`\nthis.aligned=laAtlasPayloadsAligned;`,sandbox);
        const atlas={league_state_id:'state-2',publication_generation_id:'g2'};
        const views={league_state_id:'state-2',publication_generation_id:'g2'};
        assert.strictEqual(sandbox.aligned(atlas,views,'state-2','g2'),true);
        assert.strictEqual(sandbox.aligned(atlas,{...views,publication_generation_id:'g1'},'state-2','g2'),false);
        assert.strictEqual(sandbox.aligned(atlas,{...views,publication_generation_id:null},'state-2','g2'),false);
        assert.strictEqual(sandbox.aligned(atlas,views,'state-1','g2'),false);
        assert.strictEqual(sandbox.aligned(atlas,{league_state_id:'state-2'},'state-2',null),false);
        assert.strictEqual(sandbox.aligned({league_state_id:'state-2'},{league_state_id:'state-2'},'state-2',null),true);
        """
    )
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr


def test_atlas_reentry_uses_verified_last_good_identity_during_rebuild_only():
    import subprocess
    import textwrap

    script = textwrap.dedent(
        r"""
        const fs=require('fs'),vm=require('vm'),assert=require('assert');
        const source=fs.readFileSync('src/fsffl/product/static/league_comparison.js','utf8');
        const start=source.indexOf('function laAtlasContextTarget(');
        const end=source.indexOf('let fsfflLeagueValueLensRequestId',start);
        assert(start>=0&&end>start,'production served-publication target helper must exist');
        const sandbox={window:{addEventListener:()=>{}}};
        vm.runInNewContext(source.slice(start,end)+`\nthis.target=laAtlasContextTarget;`,sandbox);
        const rebuilding={state_id:'target-state',publication_generation_id:'target-generation',capability_readiness:{overall_status:'rebuilding',publication:{generation_id:'target-generation'},served_last_good:{available:true,league_state_id:'served-state',publication_generation_id:'served-generation'}}};
        assert.deepStrictEqual(JSON.parse(JSON.stringify(sandbox.target(rebuilding))),{canonicalStateId:'target-state',stateId:'served-state',generationId:'served-generation'});
        assert.deepStrictEqual(JSON.parse(JSON.stringify(sandbox.target(rebuilding,true,'target-generation'))),{canonicalStateId:'target-state',stateId:'target-state',generationId:'target-generation'});
        const ready={...rebuilding,capability_readiness:{overall_status:'full',publication:{generation_id:'target-generation'},served_last_good:{available:false}}};
        assert.deepStrictEqual(JSON.parse(JSON.stringify(sandbox.target(ready))),{canonicalStateId:'target-state',stateId:'target-state',generationId:'target-generation'});
        const unverified={...rebuilding,capability_readiness:{...rebuilding.capability_readiness,served_last_good:{...rebuilding.capability_readiness.served_last_good,available:false}}};
        assert.deepStrictEqual(JSON.parse(JSON.stringify(sandbox.target(unverified))),{canonicalStateId:'target-state',stateId:'target-state',generationId:'target-generation'});
        """
    )
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr


def test_atlas_value_lens_response_cannot_overwrite_a_newer_publication():
    import subprocess
    import textwrap

    script = textwrap.dedent(
        r"""
        const fs=require('fs'),vm=require('vm'),assert=require('assert');
        const source=fs.readFileSync('src/fsffl/product/static/league_comparison.js','utf8');
        const start=source.indexOf('function laValueLensResponseMatches(');
        const end=source.indexOf('let fsfflLeagueValueLensRequestId',start);
        assert(start>=0&&end>start,'production value-lens generation fence must exist');
        const sandbox={window:{addEventListener:()=>{}}};
        vm.runInNewContext(source.slice(start,end)+`\nthis.matches=laValueLensResponseMatches;`,sandbox);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g2','g2','g2'),true);
        assert.strictEqual(sandbox.matches(1,2,'state-1','state-2','g1','g2','g1'),false);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g1','g2','g1'),false);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g2','g2','g1'),false);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2',null,null,null),true);
        """
    )
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr


def test_league_atlas_rollout_surfaces_simulation_futures_and_origin_aware_pick_intelligence() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "Season scenarios" in source
    assert "sim?.multiverse?.worlds" in source
    assert "row.projected_slot" in source
    assert "row.fsffl_intrinsic_pick_value" in source
    assert "Team-of-origin value" in source
    assert "Generic class fallback" in source
    assert "league-wide condition used to select each example" in source
    assert "Rarity is how often that condition or event appeared in this same run" in source
    assert "Neither is your team’s odds" in source
    assert "not a team-specific upside/downside or a separate probability" in source
    assert "world?.team_outcomes||[]" in source
    assert "outcome?.team_id===managed" in source
    assert "outcome.regular_season_rank" in source
    assert "outcome.champion" in source
    assert "managedWorlds.map(({world,outcome})=>" in source
    assert "managedWorlds.slice(0,4)" not in source
    assert "estimate?.distribution?.mean" in source
    assert "estimate.distribution.mean" in source
    assert "estimate.expected_value" not in source
    assert "world?.rarity?.label" in source
    assert "world.label" not in source
    assert "world.summary" not in source
    assert "world.description" not in source


def test_league_atlas_pick_drawer_groups_owned_assets_before_traded_history() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    drawer = source[source.index("function laPickDrawer()") : source.index("function laActiveTab()")]
    assert 'class="atlas-pick-group"><h4>Currently owned</h4>' in drawer
    assert 'class="atlas-pick-group atlas-traded-picks"><h4>Traded away</h4>' in drawer
    assert drawer.index('class="atlas-pick-group"><h4>Currently owned</h4>') < drawer.index(
        'class="atlas-pick-group atlas-traded-picks"><h4>Traded away</h4>'
    )
    assert "row.pick_id" not in drawer
    assert "row.projected_slot" in drawer
    assert "row.fsffl_intrinsic_pick_value" in drawer
    assert "row.owner_team_name" in drawer
    assert "row.original_team_name" in drawer
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    atlas_blob = Path("src/fsffl/product/static/league_comparison.js").read_bytes()
    atlas_git_sha = hashlib.sha1(
        b"blob " + str(len(atlas_blob)).encode() + bytes([0]) + atlas_blob
    ).hexdigest()[:12]
    assert f"const leagueAtlasStaticVersion='20261005-atlas-{atlas_git_sha}';" in shell


def test_position_lens_controls_and_dynasty_loading_are_mobile_readable() -> None:
    from pathlib import Path

    source = Path("src/fsffl/product/static/league_comparison.js").read_text(
        encoding="utf-8"
    )
    styles = Path("src/fsffl/product/static/league_atlas.css").read_text(
        encoding="utf-8"
    )

    assert "league-position-lens-row" in source
    assert 'class="league-position-lens-note" role="status" aria-live="polite"' in source
    assert "Loading Dynasty room values… roster counts are breadth only." in source
    assert "Long-Term evidence is building… roster counts are breadth only." in source
    assert ".league-position-lens-row{" in styles
    assert "grid-template-columns:minmax(0,1fr)!important" in styles
    assert "width:100%;" in styles
    assert "min-height:38px!important" in styles
    assert "justify-content:space-between!important;" not in styles.split(
        "/* #374: group both lens controls above one readable, full-width status line. */",
        1,
    )[1]


def test_dynasty_evidence_response_fences_include_publication_generation():
    import subprocess
    import textwrap

    script = textwrap.dedent(
        r"""
        const fs=require('fs'),vm=require('vm'),assert=require('assert');
        const source=fs.readFileSync('src/fsffl/product/static/league_comparison.js','utf8');
        const start=source.indexOf('function laAtlasEvidenceRequestMatches(');
        const end=source.indexOf('async function loadFsfflLeagueComparison',start);
        assert(start>=0&&end>start,'production Dynasty request generation fence must exist');
        const sandbox={window:{addEventListener:()=>{}}};
        vm.runInNewContext(source.slice(start,end)+`\nthis.matches=laAtlasEvidenceRequestMatches;`,sandbox);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g2','g2'),true);
        assert.strictEqual(sandbox.matches(1,2,'state-1','state-2','g1','g2'),false);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g1','g2'),false);
        assert.strictEqual(sandbox.matches(2,2,'state-2','state-2','g2','g1'),false);
        """
    )
    completed = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=5)
    assert completed.returncode == 0, completed.stderr


def test_dynasty_loader_accepts_only_matching_persisted_publication_generation():
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    loader = source[source.index("async function laLoadDynastyRooms()"):source.index("async function laLoadLongTermEvidence()")]
    assert "if(fsfflLeagueStructureState.atlas?.intelligence_freshness?.stale)" not in loader
    assert "payload?.publication_generation_id!==requestedGeneration" in loader
    assert "payload?.status==='preparing'" in loader
    assert "payload?.dynasty_evidence_status==='last_good'" in loader


def test_open_atlas_reloads_when_publication_generation_advances() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "fsffl:intelligence-status-updated" in source
    assert "function laHandlePublishedIntelligence()" in source
    assert "target.generationId!==currentGeneration||target.stateId!==currentStateId" in source
    assert "loadFsfflLeagueComparison({force:true,expectedGeneration:target.generationId})" in source


def test_superseded_dynasty_request_resets_loading_and_restarts_for_new_generation() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    loader = source[source.index("async function laLoadDynastyRooms()"):source.index("async function laLoadLongTermEvidence()")]
    value_loader = source[source.index("async function loadLeagueValueLenses()"):source.index("async function laLoadDynastyRooms()")]
    long_term_loader = source[source.index("async function laLoadLongTermEvidence()"):source.index("function laAtlasPayloadsAligned(")]
    assert "const abandonSuperseded=()" in loader
    assert "fsfflLeagueDynastyRoomsLoadingRequestId!==requestId" in loader
    assert "fsfflLeagueDynastyRoomsLoadingRequestId=requestId" in loader
    assert "dynastyRoomStatus='idle'" in loader
    assert "atlasGeneration!==requestedGeneration" in loader
    assert "void laLoadDynastyRooms()" in loader
    assert "if(!stillCurrent()){abandonSuperseded();return;}" in loader
    assert "abandonSuperseded" not in value_loader
    assert "abandonSuperseded" not in long_term_loader


def test_league_atlas_modified_bundle_requires_new_inner_and_outer_cache_keys() -> None:
    atlas_path = Path("src/fsffl/product/static/league_comparison.js")
    shell_path = Path("src/fsffl/product/static/product_shell.js")
    index = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")

    atlas_blob = atlas_path.read_bytes()
    atlas_git_sha = hashlib.sha1(
        b"blob " + str(len(atlas_blob)).encode() + bytes([0]) + atlas_blob
    ).hexdigest()[:12]
    shell = shell_path.read_text(encoding="utf-8")
    match = re.search(r"const leagueAtlasStaticVersion='([^']+)';", shell)
    assert match is not None
    assert match.group(1) == f"20261005-atlas-{atlas_git_sha}"
    assert "20261005-dynasty-handoff383a" not in match.group(1)

    shell_blob = shell_path.read_bytes()
    shell_git_sha = hashlib.sha1(
        b"blob " + str(len(shell_blob)).encode() + bytes([0]) + shell_blob
    ).hexdigest()[:12]
    assert (
        f"/static/product_shell.js?v=20261004-safari-restore380&c=git-{shell_git_sha}"
        in index
    )
    assert (
        "/static/product_shell.js?v=20261004-safari-restore380"
        "&c=20261005-dynasty-handoff383a"
    ) not in index
