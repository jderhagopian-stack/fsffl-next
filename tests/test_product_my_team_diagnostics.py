from pathlib import Path


def test_my_team_diagnostics_surface_franchise_drivers_without_new_authority() -> None:
    source = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text(encoding="utf-8")
    for label in (
        "Franchise drivers",
        "Position to investigate",
        "One-player exposure",
        "Current roster age shape",
        "Owned-pick trajectory",
    ):
        assert label in source
    assert "position_strengths" in source
    assert "largest_single_player_lineup_drop" in source
    assert "bench_forecasted_count" in source
    assert "draft_picks" in source
    assert "franchise-health score" in source
    assert "acceptance_probability" not in source
    assert "trade grade" not in source.lower()


def test_my_team_diagnostics_are_descriptive_and_mobile_first() -> None:
    source = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text(encoding="utf-8")
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assert "my_team_diagnostics.js" in html
    assert "originalRenderMyTeamCommandCenter" in source
    assert "api(" not in source
    assert "No youth/veteran label" in source
    assert "no new pick-value score" in source
    assert "@media(max-width:760px)" in source
