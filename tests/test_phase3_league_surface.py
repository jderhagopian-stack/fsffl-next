from pathlib import Path


LEAGUE = Path("src/fsffl/product/static/league_comparison.js")
ATLAS_CSS = Path("src/fsffl/product/static/league_atlas.css")
INDEX = Path("src/fsffl/product/static/index.html")
POSITION_MAP = Path("src/fsffl/product/static/league_position_map.js")
POSITION_STRENGTH = Path("src/fsffl/product/static/league_position_strength.js")
PRODUCT_SHELL = Path("src/fsffl/product/static/product_shell.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_league_atlas_uses_final_north_star_information_architecture() -> None:
    source = _source(LEAGUE)

    for label in ("Overview", "Position & Depth", "Value Map", "Pick Map", "Outlook"):
        assert label in source
    assert "laOverview()" in source
    assert "laPositionsTab()" in source
    assert "laValueTab()" in source
    assert "laPickTab()" in source
    assert "laOutlookTab()" in source
    assert "data-atlas-tab" in source


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
    assert "env(safe-area-inset-top)" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "overflow-x:auto" in css
    assert "-webkit-overflow-scrolling:touch" in css
    assert ".atlas-drawer{inset:0" in css
    assert "min-height:44px" in css


def test_league_atlas_lazy_assets_have_release_specific_cache_bust() -> None:
    league = _source(LEAGUE)
    shell = _source(PRODUCT_SHELL)

    assert "/static/league_atlas.css?v=20260922-league-atlas-corrective1" in league
    assert "const leagueAtlasStaticVersion='20260922-league-atlas-corrective1';" in shell
    assert "league_comparison.js?v=${leagueAtlasStaticVersion}" in shell


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

    assert "View exact strength indices" in source
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
    assert ".league-value-dot{width:11px!important" in css

