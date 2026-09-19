from pathlib import Path


def test_franchise_diagnosis_consumes_governed_backend_outputs() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "api('/api/my-team')" in source
    assert "api('/api/values')" in source
    assert "api('/api/league/team-views')" in source
    assert "competitive_outcome" in source
    assert "roster_resilience" in source
    assert "projected_starter" in source
    assert "fsffl_cardinal_values" in source
    assert "draft_picks" in source
    assert "calculated_competitive_state" in source


def test_franchise_diagnosis_does_not_create_parallel_authority() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "fsffl_cardinal_values" in source
    assert "acceptance_probability" not in source
    assert "trade grade" not in source.lower()
    assert "no presentation-layer dynasty score" in source
    assert "no new portfolio score" in source
    assert "strength_index" in source
    assert "calculated_competitive_state" in source


def test_franchise_is_a_real_diagnosis_surface_and_mobile_first() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "my_team:['Franchise','What is actually driving your team?'" in shell
    assert "ensureMyTeamScript" in shell
    assert "renderFsfflMyTeam" in shell
    assert "What is driving this team?" in source
    assert "Where the lineup wins — and where it bends" in source
    assert "Short term ↔ long term" in source
    for destination in ("trade_center", "opportunities", "what_if"):
        assert f'data-franchise-route="{destination}"' in source
    assert "@media(max-width:820px)" in source
    assert "@media(max-width:560px)" in source
