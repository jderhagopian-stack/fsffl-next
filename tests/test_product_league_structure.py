from pathlib import Path


def test_league_structure_surface_uses_governed_team_view_evidence() -> None:
    source = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")
    for label in (
        "League structure",
        "Competitive tiers",
        "Positional landscape",
        "Position-strength heat map",
        "How the franchises are meaningfully different",
    ):
        assert label in source
    assert "calculated_competitive_state" in source
    assert "position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "100 equals league-average optimized starter production" in source


def test_league_structure_visualization_does_not_create_model_authority() -> None:
    source = Path("src/fsffl/product/static/league_position_strength.js").read_text(encoding="utf-8")
    assert "presentation-only scaling" in source
    assert "not a new score, coefficient, tier, or valuation signal" in source
    assert "owner strategy" in source
    assert "acceptance_probability" not in source
    assert "market_value" not in source
    assert "@media(max-width:760px)" in source
    assert "@media(max-width:620px)" in source
