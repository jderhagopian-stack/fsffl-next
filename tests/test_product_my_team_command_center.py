from pathlib import Path


def test_my_team_command_center_consumes_governed_backend_outputs() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "api('/api/my-team')" in source
    assert "api('/api/values')" in source
    assert "competitive_outcome" in source
    assert "projected_starter" in source
    assert "fsffl_cardinal_values" in source
    assert "draft_picks" in source
    assert "calculated_competitive_state" in source


def test_my_team_command_center_does_not_create_parallel_authority() -> None:
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "this screen only organizes them" in source
    assert "new team score" not in source.lower()
    assert "acceptance_probability" not in source
    assert "trade grade" not in source.lower()
    assert ".reduce(" not in source


def test_my_team_is_a_real_product_surface_and_mobile_first() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    source = Path("src/fsffl/product/static/my_team_dashboard.js").read_text(encoding="utf-8")
    assert "my_team:['My Team','Your franchise command center.'" in shell
    assert "ensureMyTeamScript" in shell
    assert "renderFsfflMyTeam" in shell
    for destination in ("trade_center", "league_comparison", "analytics", "what_if"):
        assert f'data-my-team-route="{destination}"' in source
    assert "@media(max-width:760px)" in source
    assert "@media(max-width:460px)" in source
