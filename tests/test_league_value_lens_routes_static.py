from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"


def test_persistent_webapp_installs_distinct_league_value_lens_route() -> None:
    webapp = (PRODUCT / "persistent_webapp.py").read_text(encoding="utf-8")
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    assert "install_league_value_lens_routes" in webapp
    assert '"/api/league/value-lenses"' in routes
    assert "build_league_value_lenses" in routes
    assert "Broad Market remains independently usable" in routes


def test_atlas_lens_contract_cannot_create_team_value_or_team_utility() -> None:
    source = (PRODUCT / "league_value_lenses.py").read_text(encoding="utf-8")
    assert '"team_value_total_created": False' in source
    assert '"team_value_rank_created": False' in source
    assert '"league_market_value_available": False' in source
    assert '"team_utility_included": False' in source
    assert '"fsffl_cardinal_value_included": False' in source
    assert '"raw_value_subtraction_used": False' in source
    assert '"recommendation_authority": False' in source
    assert '"acceptance_probability": None' in source


def test_primary_league_presentation_uses_approved_value_hierarchy() -> None:
    html = (PRODUCT / "static" / "index.html").read_text(encoding="utf-8")
    corrections = (PRODUCT / "static" / "beta_product_corrections.js").read_text(encoding="utf-8")
    league = (PRODUCT / "static" / "league_comparison.js").read_text(encoding="utf-8")
    assert 'value="total_cardinal_value"' not in html
    assert 'option[value="total_cardinal_value"]' in corrections
    assert "remove()" in corrections
    assert "Broad Market + FSFFL Intrinsic" in league
    assert "Total FSFFL Cardinal Value" not in league


def test_player_board_intrinsic_build_is_optional_not_route_blocking() -> None:
    routes = (PRODUCT / "league_value_lens_routes.py").read_text(encoding="utf-8")
    assert '"status": "building_optional"' in routes
    assert '"Broad Market remains independently usable."' in routes
    assert "JSONResponse(status_code=202" not in routes
    assert 'payload["fsffl_intrinsic"]' in routes
