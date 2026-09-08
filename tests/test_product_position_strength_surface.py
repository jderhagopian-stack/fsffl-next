from pathlib import Path


def test_my_team_consumes_authoritative_league_relative_position_strength() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")

    assert "view.position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "league_average_expected_points" in source
    assert "100 equals league-average optimized starter production" in source
    assert "current competitive lineup strength only" in source
    assert "does not mix in future dynasty asset value" in source


def test_position_strength_surface_does_not_create_browser_model_truth() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")

    assert "myTeamPositionStrengthCard" in source
    assert "row?.strength_index" in source
    assert "row?.expected_points" in source
    assert "row?.league_average_expected_points" in source
    assert "build_league_relative_position_strengths" not in source
