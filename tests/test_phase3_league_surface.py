from pathlib import Path


LEAGUE = Path("src/fsffl/product/static/league_comparison.js")
INDEX = Path("src/fsffl/product/static/index.html")
POSITION_MAP = Path("src/fsffl/product/static/league_position_map.js")
POSITION_STRENGTH = Path("src/fsffl/product/static/league_position_strength.js")


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

    assert "session_recovery.js?v=20260910-phase3-league2" in source
    assert "mobile_safari_recovery.js?v=20260910-phase3-league2" in source
    assert "league_comparison.js?v=20260910-phase3-league2" not in source
    assert "product_shell.js?v=20260910-phase3-league2" in source
