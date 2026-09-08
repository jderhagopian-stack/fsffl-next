from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_my_team_adds_position_and_league_context_without_new_score() -> None:
    source = (ROOT / "src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "api('/api/league/team-views')" in source
    assert "myTeamPositionRank" in source
    assert "myTeamLeagueOutcomeRank" in source
    assert "Position rank" in source
    assert "League rank #" in source
    assert "Championship odds" in source
    assert "separate from owner posture" in source
    assert "not a new FSFFL score" in source
    assert "*10000" not in source.replace(" ", "")


def test_league_comparison_adds_state_title_and_read_only_ranks() -> None:
    source = (ROOT / "src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "championship_probability" in source
    assert "api('/api/league/team-views')" in source
    assert "competitive_state" in source
    assert "lcRank" in source
    assert "Title odds" in source
    assert "separate from owner strategic posture" in source
    assert "does not calculate new scores or rankings" in source
    assert "does not create a new master score" in source


def test_contextual_information_keeps_action_surfaces_available() -> None:
    source = (ROOT / "src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    for destination in ("trade_center", "opportunities", "league_comparison", "analytics", "what_if"):
        assert f'data-my-team-route="{destination}"' in source
