from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"
STATIC = PRODUCT / "static"


def test_franchise_consumer_uses_canonical_shapley_intrinsic() -> None:
    source = (STATIC / "intrinsic_value_experience.js").read_text(encoding="utf-8")
    assert "api('/api/value/intrinsic-shapley-v1')" in source
    assert "api('/api/value/intrinsic-v1')" not in source
    assert "FSFFL Intrinsic · Shapley" in source
    assert "raw_intrinsic_value" in source
    assert "replacement-surplus endpoint remains compatibility-only" in source


def test_legacy_replacement_surplus_route_is_deprecated_compatibility_only() -> None:
    source = (PRODUCT / "intrinsic_value_routes.py").read_text(encoding="utf-8")
    assert '@app.get("/api/value/intrinsic-v1", deprecated=True)' in source
    assert '"authority_status": "legacy_replacement_surplus_compatibility_only"' in source
    assert '"canonical_intrinsic_endpoint": "/api/value/intrinsic-shapley-v1"' in source
    assert '"product_consumer_status": "no_current_product_consumer"' in source


def test_league_value_lens_names_shapley_as_canonical_intrinsic_without_team_value() -> None:
    source = (PRODUCT / "league_value_lenses.py").read_text(encoding="utf-8")
    assert '"canonical_fsffl_intrinsic_authority": "shapley_intrinsic"' in source
    assert '"authority_family": "canonical_shapley_intrinsic"' in source
    assert '"team_value_total_created": False' in source
    assert '"team_value_rank_created": False' in source
    assert '"league_market_value_available": False' in source
    assert '"team_utility_included": False' in source


def test_franchise_shapley_migration_preserves_approved_value_hierarchy() -> None:
    source = (STATIC / "intrinsic_value_experience.js").read_text(encoding="utf-8")
    assert "Broad Market Value" in source
    assert "FSFFL Intrinsic · Shapley" in source
    assert "League Market Value" in source
    assert "Team Utility" in source
    assert "Broad Market and Shapley Intrinsic use different raw units" in source
    assert "same versioned 0-10,000 Value Index for presentation" in source
    assert "Raw Market and raw Shapley quantities are never subtracted" in source
    assert "FSFFL Cardinal Value" not in source
