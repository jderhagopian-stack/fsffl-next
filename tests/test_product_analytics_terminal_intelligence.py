from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERMINAL = ROOT / "src/fsffl/product/static/analytics_terminal.js"


def test_analytics_terminal_exposes_deeper_read_only_views() -> None:
    source = TERMINAL.read_text(encoding="utf-8")
    assert "Team heatmap" in source
    assert "FSFFL vs market" in source
    assert "Trade partners" in source
    assert "Roster construction heatmap" in source
    assert "Where FSFFL and the market disagree" in source
    assert "Trade-partner intelligence" in source
    assert "championship_probability" in source
    assert "competitive_state" in source


def test_analytics_terminal_reconciles_canonical_team_identity() -> None:
    source = TERMINAL.read_text(encoding="utf-8")
    assert "idByName" in source
    assert "team_id" in source
    assert "drilldown_ref" in source
    assert "atNorm(point.label)" in source


def test_analytics_terminal_keeps_new_diagnostics_presentation_only() -> None:
    source = TERMINAL.read_text(encoding="utf-8")
    assert "not a new Value or utility score" in source
    assert "No new blended score is created" in source
    assert "not an acceptance forecast" in source
    assert "does not create forecasts, values, utility, probabilities, recommendations or hidden thresholds" in source
    assert "acceptance_probability" not in source
    assert "master score" in source


def test_analytics_terminal_player_projection_is_full_nfl_season_only() -> None:
    source = TERMINAL.read_text(encoding="utf-8")
    assert "season_fantasy_points_projection" in source
    assert "item.horizon==='season'" in source
    assert "fantasy_regular_season" not in source
    assert "NFL season projection" in source
