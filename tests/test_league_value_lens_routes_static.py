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


def test_cardinal_is_not_rebranded_as_generic_franchise_value() -> None:
    html = (PRODUCT / "static" / "index.html").read_text(encoding="utf-8")
    corrections = (PRODUCT / "static" / "beta_product_corrections.js").read_text(encoding="utf-8")
    league = (PRODUCT / "static" / "league_comparison.js").read_text(encoding="utf-8")
    assert 'value="total_cardinal_value">FSFFL Cardinal Value' in html
    assert "cardinalOption.textContent='FSFFL Cardinal Value'" in corrections
    assert "cardinalOption.textContent='Franchise value'" not in corrections
    assert "Total FSFFL Cardinal Value" in league
