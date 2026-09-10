from pathlib import Path


def test_my_team_diagnostics_surface_carrier_and_asset_leverage_without_new_score() -> None:
    source = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text(encoding="utf-8")
    for label in (
        "Current lineup engine",
        "Highest-value roster asset",
        "Highest-value nonstarter",
    ):
        assert label in source
    assert "position_strengths" in source
    assert "myTeamValueNumber" in source
    assert "not a new franchise score" in source
    assert "acceptance_probability" not in source
    assert "api(" not in source


def test_my_team_optional_leverage_is_descriptive_not_aggregate_value() -> None:
    source = Path("src/fsffl/product/static/my_team_diagnostics.js").read_text(encoding="utf-8")
    assert "Highest authoritative FSFFL Value among players not currently projected to start" in source
    assert "descriptive only" in source
    assert "reduce(" not in source
    assert "sum(" not in source
