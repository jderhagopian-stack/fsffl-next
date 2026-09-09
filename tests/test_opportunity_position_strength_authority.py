from pathlib import Path


def test_opportunity_search_consumes_published_position_strength_rows() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert "for view in simulation.team_views" in source
    assert "for row in view.position_strengths" in source
    assert "build_league_relative_position_strengths" not in source
    assert "Consume already-published league-relative position strength evidence" in source


def test_opportunity_search_keeps_position_strength_as_search_context_only() -> None:
    source = Path("src/fsffl/product/opportunity_search.py").read_text(encoding="utf-8")

    assert '"action_authority": "diagnostic_only"' in source
    assert '"bilateral_decision_evaluated": False' in source
    assert "Cardinal Value is one market-plausibility coordinate" in source
    assert "not the definition of the best opportunity" in source
    assert "acceptance evidence remain incomplete" in source
    assert "No metrics are blended into a score" in source
