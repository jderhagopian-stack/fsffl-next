from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_behavioral_intelligence_is_first_class_read_only_surface() -> None:
    shell = (STATIC / "product_shell.js").read_text()
    surface = (STATIC / "behavioral_intelligence.js").read_text()

    assert "behavioral_intelligence" in shell
    assert "Behavioral Intelligence" in shell
    assert "/static/behavioral_intelligence.js" in shell
    assert "/api/behavioral/profiles" in surface
    assert "Market Value" in surface
    assert "acceptance probability" in surface
    assert "does not infer" in surface
    assert "current_team_name" in surface
    assert "trade_count" in surface
    assert "acquired_pick_count" in surface
    assert "consolidation_trade_count" in surface
    assert "acquired_positions" in surface
    assert "seasons_observed" in surface


def test_behavioral_intelligence_does_not_create_league_specific_or_action_authority() -> None:
    surface = (STATIC / "behavioral_intelligence.js").read_text().lower()

    assert "12-team" not in surface
    assert "half ppr" not in surface
    assert "superflex" not in surface
    assert "hurts so good" not in surface
    assert "acceptance prediction" in surface
    assert "cannot change market value" in surface
    assert "trade decision disposition" in surface
    assert "search authority" in surface


def test_behavioral_intelligence_has_mobile_layout() -> None:
    surface = (STATIC / "behavioral_intelligence.js").read_text()

    assert "@media(max-width:900px)" in surface
    assert "@media(max-width:680px)" in surface
    assert "behavior-owner-grid" in surface
