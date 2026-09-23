from pathlib import Path


LEAGUE = Path("src/fsffl/product/static/league_comparison.js")
ATLAS_CSS = Path("src/fsffl/product/static/league_atlas.css")
INDEX = Path("src/fsffl/product/static/index.html")
POSITION_MAP = Path("src/fsffl/product/static/league_position_map.js")
POSITION_STRENGTH = Path("src/fsffl/product/static/league_position_strength.js")
PRODUCT_SHELL = Path("src/fsffl/product/static/product_shell.js")
MOBILE_TOUCH = Path("src/fsffl/product/static/mobile_touch_fix.css")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_league_atlas_uses_final_acceptance_information_architecture() -> None:
    source = _source(LEAGUE)

    for label in ("Overview", "Position & Depth", "Value Map", "Pick Map"):
        assert label in source
    assert "laOverview()" in source
    assert "laPositionsTab()" in source
    assert "laValueTab()" in source
    assert "laPickTab()" in source
    assert "laOutlookTab()" not in source
    assert "data-atlas-tab=\"outlook\"" not in source
    assert "data-atlas-tab" in source
    assert "Current Season + Outlook from Today" in source


def test_league_atlas_composes_governed_contracts_without_team_value_fabrication() -> None:
    source = _source(LEAGUE)

    assert "api('/api/league/atlas')" in source
    assert "api('/api/league/team-views')" in source
    assert "api('/api/league/value-lenses')" in source
    assert "api('/api/values')" not in source
    assert "team_cardinal_portfolios" not in source
    assert "no arbitrary pick-value master score" in source
    assert "does not invent a position fragility score" in source
    assert "acceptance_probability" not in source


def test_league_atlas_progressively_loads_value_without_blocking_structure() -> None:
    source = _source(LEAGUE)

    assert "Promise.all([api('/api/league/atlas'),api('/api/league/team-views')])" in source
    assert "void loadLeagueValueLenses()" in source
    assert "Governed value lenses are loading" in source
    assert "Other Atlas surfaces remain independently usable" in source


def test_position_and_pick_drilldowns_and_player_handoff_are_present() -> None:
    source = _source(LEAGUE)
    player = Path("src/fsffl/product/static/player_intelligence.js").read_text(encoding="utf-8")

    assert "data-room-team" in source
    assert "data-room-position" in source
    assert "data-pick-team" in source
    assert "data-player-intelligence-id" in source
    assert "document.addEventListener('click',event=>{const trigger=event.target.closest('[data-player-intelligence-id]')" in player


def test_league_pressure_point_is_investigative_not_a_trade_recommendation() -> None:
    source = _source(LEAGUE)

    assert "not trade recommendations" in source
    assert "Investigate in Market" in source
    assert "setRoute('opportunities')" in source


def test_league_atlas_mobile_css_is_deliberate_and_safe_area_aware() -> None:
    css = _source(ATLAS_CSS)

    assert "@media(max-width:720px)" in css
    mobile = _source(MOBILE_TOUCH)
    assert "env(safe-area-inset-top)" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "padding-top:calc(10px + env(safe-area-inset-top,0px))!important" in mobile
    assert "padding-bottom:calc(70px + env(safe-area-inset-bottom,0px))" in mobile
    assert "overflow-x:auto" in css
    assert "-webkit-overflow-scrolling:touch" in css
    assert ".atlas-drawer{inset:0" in css
    assert "min-height:44px" in css


def test_league_atlas_lazy_assets_have_release_specific_cache_bust() -> None:
    league = _source(LEAGUE)
    shell = _source(PRODUCT_SHELL)

    assert "/static/league_atlas.css?v=20260923-league-atlas-finaliphone3" in league
    assert "const leagueAtlasStaticVersion='20260923-league-atlas-finaliphone3';" in shell
    assert "league_comparison.js?v=${leagueAtlasStaticVersion}" in shell
    assert "const mobileTouchStaticVersion=\'20260923-mobile-safearea2\';" in shell


def test_legacy_league_position_modules_remain_non_rendering_shims() -> None:
    assert _source(POSITION_MAP).strip().startswith("// Phase 3 League now owns")
    assert _source(POSITION_STRENGTH).strip().startswith("// Phase 3 League now owns")


def test_phase3_league_preserves_hosted_recovery_scripts() -> None:
    source = _source(INDEX)

    assert "/static/session_recovery.js?v=" in source
    assert "/static/mobile_safari_recovery.js?v=" in source
    assert "/static/product_shell.js?v=" in source


def test_generic_surface_clears_league_only_panel_class() -> None:
    source = _source(PRODUCT_SHELL)

    assert "if(route!=='league_comparison')panel?.classList.remove('league-structure-panel')" in source

def test_live_acceptance_corrective_mobile_composition_preserves_identity_and_progressive_evidence() -> None:
    source = _source(LEAGUE)
    css = _source(ATLAS_CSS)

    assert "View exact strength indices" not in source
    assert "league-edge-exact" not in source
    assert "largest_single_player_lineup_drop_player_ids" in source
    assert "driver unavailable" in source
    assert "total through" in source
    assert "Selected-year inventory is kept separate from all-horizon inventory." in source
    assert "league-value-detail-heading" in source
    assert "laActiveTab()+laEvidenceDetail()" in source
    assert "laActiveTab()+'</main>'+laEvidenceStrip()" not in source
    assert ".atlas-pick-table{overflow:visible!important" in css
    assert ".atlas-outlook-list{overflow:visible!important" in css
    assert ".league-edge-row>span:first-child{position:sticky" in css
    assert ".league-value-dot{\n  width:12px!important" in css



def test_final_acceptance_overview_is_full_league_sortable_table() -> None:
    source = _source(LEAGUE)
    css = _source(ATLAS_CSS)

    assert "standings.slice(0,6)" not in source
    assert "View all " not in source
    assert "laRaceSorted(standings)" in source
    assert 'class="atlas-race-table"' in source
    assert "Current Season" in source
    assert "Outlook from Today" in source
    assert "50,000 simulations using current standings, rosters and forecast evidence." in source
    for label in ("PF", "PA", "Max PF", "Projected Finish", "Playoffs", "Championship", "Projected Final Wins", "1st Place"):
        assert label in source
    assert "Forward details" not in source
    assert "rank vs exp finish" not in source
    assert "data-race-sort" in source
    assert "atlas-race-rank-sticky" in css
    assert "atlas-race-team-sticky" in css
    assert "overflow-x:auto" in css
    assert "Preseason expectation → now" in source
    assert "ppts + ppts_decimal" in source


def test_final_iphone_polish_uses_one_tappable_rank_strength_map_and_valid_value_dom() -> None:
    source = _source(LEAGUE)
    css = _source(ATLAS_CSS)

    assert source.count("league-edge-matrix league-edge-map") == 1
    assert source.count("See positional control at a glance") == 1
    assert "Where does each roster own an actual lineup edge?" not in source
    assert "league-edge-exact" not in source
    assert "positionLensMode:'rank'" in source
    assert 'data-position-lens="rank"' in source
    assert 'data-position-lens="strength"' in source
    assert "100 = league-average optimized starter production." in source
    assert "Team order does not change between lenses." in source
    assert "data-room-team" in source
    assert "data-room-position" in source
    assert "Tap any position to see the players and evidence behind its rank." in source
    assert "league-value-team-select" in source
    assert '<button type="button" class="league-value-row ' not in source
    assert '<div class="league-value-row ' in source
    assert "league-edge-map .league-edge-cell>b" in css
    assert "width:36px" in css
    assert "grid-template-columns:minmax(80px,1.25fr) repeat(4,minmax(0,1fr))!important" in css


def test_final_iphone_polish_race_has_real_two_tier_sticky_geometry() -> None:
    source = _source(LEAGUE)
    css = _source(ATLAS_CSS)

    assert 'class="atlas-race-group-row"' in source
    assert 'class="atlas-race-metric-row"' in source
    assert 'colspan="4">Current Season' in source
    assert 'colspan="5">Outlook from Today' in source
    assert 'rowspan="2"' in source
    assert "atlas-col-wins" in source
    assert "min-width:1120px" in css
    assert "--atlas-race-group-height:32px" in css
    assert "tr.atlas-race-group-row>th" in css
    assert "tr.atlas-race-metric-row>th" in css
    assert ".atlas-race-table thead th{\n    position:static!important" in css
    assert "top:auto!important" in css
    assert "width:108px!important" in css
    assert ".atlas-race-group-row>.atlas-race-team-sticky" in css


def test_physical_iphone_acceptance_hides_legacy_duplicate_map_and_fits_retained_map() -> None:
    source = _source(LEAGUE)
    css = _source(ATLAS_CSS)
    north_star = Path("src/fsffl/product/static/north_star_app.js").read_text(encoding="utf-8")

    assert source.count("league-edge-matrix league-edge-map") == 1
    assert "atlas.className='ns-league-atlas'" in north_star
    assert ".league-structure-panel .ns-league-atlas{display:none!important}" in css
    assert "height:31px!important" in css
    assert "width:27px!important" in css
    assert "grid-template-columns:minmax(78px,1.22fr) repeat(4,minmax(0,1fr))!important" in css


def test_physical_iphone_acceptance_race_identity_is_compact_and_header_does_not_cover_first_row() -> None:
    css = _source(ATLAS_CSS)

    assert ".atlas-race-team-sticky{\n  width:108px!important" in css
    assert ".atlas-race-group-row>.atlas-race-team-sticky" in css
    assert "text-align:left!important" in css
    assert ".atlas-race-table thead th{\n    position:static!important" in css
    assert ".atlas-race-table thead .atlas-race-rank-sticky" in css
    assert "top:auto!important" in css
