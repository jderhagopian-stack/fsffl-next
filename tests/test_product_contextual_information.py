from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_franchise_adds_position_and_league_context_without_new_score() -> None:
    source = (ROOT / "src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "api('/api/league/team-views')" in source
    assert "myTeamPositionRank" in source
    assert "myTeamLeagueOutcomeRank" in source
    assert "100 = league average" in source
    assert "in expected wins" in source
    assert "title" in source
    assert "calculated_competitive_state" in source
    assert "no presentation-layer dynasty score" in source
    assert "*10000" not in source.replace(" ", "")


def test_league_structure_adds_state_position_and_read_only_context() -> None:
    source = (ROOT / "src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "api('/api/league/team-views')" in source
    assert "calculated_competitive_state" in source
    assert "position_strengths" in source
    assert "league_rank" in source
    assert "strength_index" in source
    assert "Calculated state comes from Team Utility and Simulation" in source
    assert "owner strategic posture is separate" in source
    assert "does not create trade recommendations" in source
    assert "hidden power rating" in source


def test_franchise_keeps_primary_action_paths_available_without_dashboard_duplication() -> None:
    source = (ROOT / "src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    for destination in ("trade_center", "opportunities", "what_if"):
        assert f'data-franchise-route="{destination}"' in source
    assert "data-franchise-tab-open=\"roster\"" in source
    assert "data-franchise-tab-open=\"assets\"" in source
