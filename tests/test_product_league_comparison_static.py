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
    assert source.count("fsfflLeagueStructureState.atlas?.intelligence_freshness?.stale") == 4
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
    assert "const publicationMatches=contextGeneration===atlasGeneration" in atlas
    assert "if(!force&&publicationMatches&&fsfflLeagueStructureState.atlas" in atlas
    assert "laAtlasPayloadsAligned(results[0],results[1],stateId,expectedGeneration)" in atlas
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
        const sandbox={};
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
        const sandbox={};
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
    assert "20261004-publication-handoff378" in Path(
        "src/fsffl/product/static/product_shell.js"
    ).read_text(encoding="utf-8")
    assert "20261004-publication-handoff378" in source


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
