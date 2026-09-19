from pathlib import Path


LEAGUE = Path("src/fsffl/product/static/league_comparison.js")
INDEX = Path("src/fsffl/product/static/index.html")
POSITION_MAP = Path("src/fsffl/product/static/league_position_map.js")
POSITION_STRENGTH = Path("src/fsffl/product/static/league_position_strength.js")
PRODUCT_SHELL = Path("src/fsffl/product/static/product_shell.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_league_surface_leads_with_governed_structure_not_power_score() -> None:
    source = _source(LEAGUE)

    assert "lcPrimaryTakeaway()" in source
    assert "lcPositionMatrix()" in source
    assert "calculated_competitive_state" in source
    assert "league_rank" in source
    assert "strength_index" in source
    assert "one power score" in source
    assert "hidden power rating" in source


def test_league_surface_keeps_value_optional_to_canonical_team_analytics() -> None:
    source = _source(LEAGUE)

    assert "Promise.allSettled([api('/api/league/team-views'),api('/api/values')])" in source
    assert "if(teamResult.status!=='fulfilled')throw teamResult.reason" in source
    assert "valueResult.status==='fulfilled'?valueResult.value:null" in source


def test_league_pressure_point_is_investigative_not_a_trade_recommendation() -> None:
    source = _source(LEAGUE)

    assert "not trade recommendations" in source
    assert "Investigate in Market" in source
    assert "setRoute('opportunities')" in source


def test_league_surface_uses_visible_primary_structure_and_secondary_provenance() -> None:
    source = _source(LEAGUE)

    render = source.split("function renderLeagueComparison()", 1)[1].split(
        "async function loadFsfflLeagueComparison", 1
    )[0]
    assert render.index("lcPrimaryTakeaway()") < render.index("lcPositionMatrix()")
    assert render.index("lcPositionMatrix()") < render.index("lcCompetitiveMap()")
    assert "Evidence & definitions" in source
    assert "<details class=\"league-detail\"><summary>Evidence & definitions" in source


def test_legacy_league_position_modules_no_longer_render_competing_surfaces() -> None:
    assert _source(POSITION_MAP).strip().startswith("// Phase 3 League now owns")
    assert _source(POSITION_STRENGTH).strip().startswith("// Phase 3 League now owns")


def test_phase3_league_cache_generation_preserves_hosted_recovery_scripts() -> None:
    source = _source(INDEX)

    assert "/static/session_recovery.js?v=" in source
    assert "/static/mobile_safari_recovery.js?v=" in source
    assert "/static/product_shell.js?v=" in source
    versions = {
        token.split("?v=")[1].split('"')[0]
        for token in source.split()
        if "?v=" in token
    }
    assert len(versions) == 1


def test_league_asset_order_never_mixes_pick_count_with_cardinal_value() -> None:
    source = _source(LEAGUE)

    assert "b.picks-a.picks" in source
    assert "(b.pickValue??b.picks)" not in source
    assert "(a.pickValue??a.picks)" not in source


def test_age_profile_surfaces_starter_specific_evidence_on_mobile() -> None:
    source = _source(LEAGUE)

    assert "known_starter_age_count" in source
    assert "starter avg · ${view.known_starter_age_count||0} known" in source
    assert ".league-age-reading:nth-child(3){display:none}" not in source


def test_generic_surface_clears_league_only_panel_class() -> None:
    source = _source(PRODUCT_SHELL)

    assert "if(route!=='league_comparison')panel?.classList.remove('league-structure-panel')" in source
