from pathlib import Path


def test_home_is_attention_surface_not_dashboard_duplicate() -> None:
    source = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
    for label in (
        "What should I care about right now?",
        "Competitive outlook",
        "Roster vulnerability",
        "Position to investigate",
        "From insight to action",
    ):
        assert label in source
    assert "largest_single_player_lineup_drop" in source
    assert "position_strengths" in source
    assert ".metric-grid" in source
    assert ".dashboard-grid" in source
    assert ".roster-panel" in source
    assert "setAttribute('hidden','')" in source
    assert "opaque combined score" in source


def test_home_reuses_loaded_governed_team_view_and_is_mobile_responsive() -> None:
    source = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "ensureHomeScript" in shell
    assert "installFsfflHomeExperience" in shell
    assert "renderFsfflHomeAttention" in source
    assert "originalRenderMyTeam" in source
    assert "api(" not in source
    assert "acceptance_probability" not in source
    assert "change-since-last-visit" in source
    assert "only after their governed history/evidence contracts exist" in source
    assert "@media(max-width:760px)" in source


def test_home_keeps_pipeline_status_progressively_disclosed() -> None:
    source = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")
    assert "Show technical status" in source
    assert "grid.hidden=true" in source
