from pathlib import Path


HOME = Path("src/fsffl/product/static/home_dashboard.js").read_text(encoding="utf-8")


def test_home_is_priority_command_center_not_dashboard_duplicate() -> None:
    for label in (
        "Command Center",
        "Best next action",
        "Franchise pulse",
        "Three things worth knowing",
        "Choose the decision, not the dashboard",
    ):
        assert label in HOME
    assert "home-priority" in HOME
    assert "home-pulse-list" in HOME
    assert "home-workflows" in HOME
    assert "largest_single_player_lineup_drop" in HOME
    assert "position_strengths" in HOME
    assert ".metric-grid" in HOME
    assert ".dashboard-grid" in HOME
    assert ".roster-panel" in HOME
    assert "setAttribute('hidden','')" in HOME
    assert "home-attention-grid" not in HOME
    assert "home-investigate-actions" not in HOME


def test_home_reuses_loaded_governed_evidence_and_does_not_launch_deep_work() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "ensureHomeScript" in shell
    assert "installFsfflHomeExperience" in shell
    assert "renderFsfflHomeAttention" in HOME
    assert "originalRenderMyTeam" in HOME
    assert "homeLoadedOpportunityWorkspace" in HOME
    assert "api(" not in HOME
    assert "fetch(" not in HOME
    assert "/api/" not in HOME
    assert "acceptance_probability" not in HOME
    assert "does not calculate a combined score or launch deep Search" in HOME


def test_home_keeps_future_change_feed_evidence_gated() -> None:
    assert "Change-since-last-visit and activity alerts" in HOME
    assert "only after their governed history/evidence contracts exist" in HOME
    assert "what changed" not in HOME.lower()


def test_home_keeps_pipeline_status_progressively_disclosed_and_secondary() -> None:
    assert "Show technical status" in HOME
    assert "grid.hidden=true" in HOME
    assert "home-system-status" in HOME


def test_home_is_intentionally_mobile_first() -> None:
    assert "@media(max-width:760px)" in HOME
    assert ".home-priority{grid-template-columns:1fr" in HOME
    assert ".home-pulse-row>div{grid-template-columns:1fr" in HOME
    assert ".home-workflows{grid-template-columns:1fr" in HOME
