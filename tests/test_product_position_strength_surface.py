from pathlib import Path


def test_franchise_consumes_authoritative_league_relative_position_strength() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")

    assert "position_strengths" in source
    assert "strength_index" in source
    assert "league_rank" in source
    assert "team_count" in source
    assert "100 = league average" in source
    assert "governed position-strength index" in source


def test_position_strength_visualization_does_not_create_browser_model_truth() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")

    assert "myTeamStrengthBar" in source
    assert "row.strength_index" in source
    assert "build_league_relative_position_strengths" not in source
    assert "new position score" not in source.lower()
