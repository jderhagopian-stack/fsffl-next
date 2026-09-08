from pathlib import Path


def test_opportunity_search_consumes_published_position_strength_rows() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert "for view in simulation.team_views" in source
    assert "for row in view.position_strengths" in source
    assert "build_league_relative_position_strengths" not in source
    assert "Search does not rebuild this derived truth" in source


def test_opportunity_search_keeps_position_strength_as_ordering_context_only() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert '"action_authority": "diagnostic_only"' in source
    assert '"bilateral_decision_evaluated": False' in source
    assert "Cardinal Value order Search only" in source
    assert "acceptance" in source
