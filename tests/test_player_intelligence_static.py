from pathlib import Path
import shutil
import subprocess

import pytest


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


def _text(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def test_player_intelligence_exposes_required_information_architecture() -> None:
    source = _text("player_intelligence.js")
    for label in (
        "Overview",
        "Career & Forecast",
        "Value",
        "Methods / Evidence",
        "Broad Market",
        "FSFFL Intrinsic",
        "Historical actuals",
        "Forecast details",
    ):
        assert label in source
    assert "/api/player-intelligence/" in source
    assert "/history" in source


def test_player_trajectory_distinguishes_actual_forecast_and_uncertainty() -> None:
    source = _text("player_intelligence.js")
    css = _text("player_intelligence.css")
    assert "Actual → Forecast" in source
    assert "pi-forecast-boundary" in source
    assert "FORECAST" in source
    assert "Governed uncertainty / scenario range" in source
    assert "pi-range" in source
    assert ".pi-bar-wrap.pi-forecast-boundary" in css
    assert ".pi-phase-label" in css


def test_forecast_ppg_fails_closed_without_expected_games() -> None:
    source = _text("player_intelligence.js")
    assert "PPG unavailable" in source
    assert "ppg_basis" in source
    assert "17-game display rate" not in source


def test_player_intelligence_preserves_value_and_forecast_authority_boundaries() -> None:
    source = _text("player_intelligence.js")
    assert "Raw Market and raw Shapley quantities are never subtracted" in source
    assert "Future Y2/Y3 points come directly from Forecast authority" in source
    assert "they are not inferred from Intrinsic" in source
    assert "shared Value Index is presentation-only" in source
    assert "League Market Value:</strong> unavailable by design" in source


def test_player_intelligence_mobile_sheet_is_scrollable_and_tabs_accessible() -> None:
    css = _text("player_intelligence.css")
    source = _text("player_intelligence.js")
    assert "@media(max-width:620px)" in css
    assert ".pi-sheet{inset:0;border-radius:0;padding:16px;max-width:none}" in css
    assert ".pi-sheet" in css and "overflow:auto" in css
    assert ".pi-tabs" in css and "overflow-x:auto" in css
    assert "MAX_POLLS=80" in source
    assert "Escape" in source


def test_player_intelligence_browser_script_parses() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    result = subprocess.run(
        [node, "--check", str(STATIC / "player_intelligence.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_player_intelligence_is_reachable_from_core_player_surfaces() -> None:
    surfaces = {
        "my_team_dashboard.js": "data-player-intelligence-id",
        "explorer.js": "data-player-intelligence-id",
        "trade_center.js": "data-player-intelligence-id",
        "intrinsic_market_discovery.js": "data-player-intelligence-id",
        "intrinsic_value_experience.js": "data-player-intelligence-id",
        "player_stat_lines.js": "data-player-intelligence-id",
    }
    for filename, marker in surfaces.items():
        assert marker in _text(filename), filename


def test_live_corrective_preserves_selected_tab_during_intrinsic_polling() -> None:
    source = _text("player_intelligence.js")
    assert "let activeId=null,activeTab='overview'" in source
    assert "activeTab=button.dataset.piTab||'overview'" in source
    assert "tabClass('career')" in source
    assert "tabClass('value')" in source
    assert "tabClass('methods')" in source


def test_live_corrective_starts_history_independently_of_intrinsic() -> None:
    source = _text("player_intelligence.js")
    assert "void loadOverview(g);void loadHistory(g)" in source
    overview_loader = source.split("async function loadOverview(g){", 1)[1].split(
        "async function loadHistory(g){", 1
    )[0]
    assert "loadHistory(g)" not in overview_loader


def test_live_corrective_rejects_invalid_player_ids_before_fetch() -> None:
    source = _text("player_intelligence.js")
    assert "normalizedPlayerId" in source
    assert "['null','undefined','none']" in source
    assert "const id=normalizedPlayerId(trigger.dataset.playerIntelligenceId);if(!id)return" in source


def test_live_corrective_cleans_ppg_unavailable_reason_without_inventing_games() -> None:
    source = _text("player_intelligence.js")
    assert "replace(/^unavailable:\\s*/i,'')" in source
    assert "PPG unavailable unavailable" not in source
    assert "17-game display rate" not in source


def test_live_corrective_busts_mobile_player_intelligence_cache() -> None:
    index = _text("index.html")
    assert "player_intelligence.js?pi=20260921-player-intelligence-corrective1&v=20260913-phase3-latency1" in index
    assert "player_intelligence.css?pi=20260921-player-intelligence-corrective1&v=20260913-phase3-latency1" in index
