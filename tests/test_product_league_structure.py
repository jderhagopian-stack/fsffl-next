from pathlib import Path


def test_league_structure_surface_uses_governed_team_view_evidence() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for label in (
        "Competitive shape",
        "Positional edge map",
        "Age profile",
        "Asset construction",
        "Depth & fragility across the league",
    ):
        assert label in source
    assert "calculated_competitive_state" in source
    assert "position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "100 = league-average optimized starter production" in source


def test_league_structure_visualization_does_not_create_model_authority() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "This screen does not create a blended league score" in source
    assert "does not create trade recommendations" in source
    assert "owner strategic posture is separate" in source
    assert "acceptance_probability" not in source
    assert "@media(max-width:900px)" in source
    assert "@media(max-width:560px)" in source
