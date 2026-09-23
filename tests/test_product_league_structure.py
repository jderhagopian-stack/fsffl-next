from pathlib import Path


def test_league_structure_surface_uses_governed_race_position_value_pick_and_forward_evidence() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for label in (
        "League Race",
        "Frozen preseason expectation",
        "Competitive shape",
        "Depth / fragility",
        "Pick Map",
        "Outlook",
    ):
        assert label in source
    assert "calculated_competitive_state" in source
    assert "position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "100 = league-average optimized starter production" in source


def test_league_structure_visualization_does_not_create_model_authority() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    contract = Path("src/fsffl/product/league_atlas.py").read_text(encoding="utf-8")

    assert "no arbitrary pick-value master score" in source
    assert "not trade recommendations" in source
    assert "does not invent a position fragility score" in source
    assert '"presentation_creates_model_truth": False' in contract
    assert '"team_intrinsic_total_created": False' in contract
    assert '"summed_market_percentiles_created": False' in contract
    assert '"league_market_value_available": False' in contract
    assert '"power_score_created": False' in contract
    assert '"recommendation_strength_created": False' in contract
    assert '"acceptance_probability_created": False' in contract


def test_final_atlas_has_no_standalone_outlook_or_duplicate_position_grid() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "laTabButton('outlook'" not in source
    assert "laOutlookTab" not in source
    assert "league-edge-exact" not in source
    assert "View all " not in source
