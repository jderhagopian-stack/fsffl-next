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


def test_player_trajectory_matches_expected_median_iqr_mockup_semantics() -> None:
    source = _text("player_intelligence.js")
    css = _text("player_intelligence.css")
    assert "Actual → Forecast" in source
    assert "pi-boundary" in source
    assert "FORECAST" in source
    assert "Expected forecast" in source
    assert "Median (P50)" in source
    assert "IQR (P25–P75)" in source
    assert "P10–P90" in source
    assert "pi-expected-line" in source
    assert "pi-median-line" in source
    assert "pi-iqr-band" in source
    assert ".pi-actual-line" in css
    assert ".pi-expected-line" in css
    assert ".pi-median-line" in css
    assert ".pi-iqr-band" in css
    assert ".pi-outer-band" in css
    assert "pi-bar-wrap" not in source


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
    assert "height:100dvh" in css
    assert "env(safe-area-inset-top)" in css
    assert "env(safe-area-inset-bottom)" in css
    assert ".pi-sheet" in css and "overflow-x:hidden" in css
    assert ".pi-tabs" in css and "overflow-x:auto" in css
    assert "position:sticky" in css
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
    assert "void loadOverview(g,id);void loadHistory(g,id)" in source
    overview_loader = source.split("async function loadOverview(g,id){", 1)[1].split(
        "async function loadHistory(g,id){", 1
    )[0]
    assert "loadHistory(g,id)" not in overview_loader


def test_live_corrective_rejects_invalid_player_ids_before_fetch() -> None:
    source = _text("player_intelligence.js")
    assert "normalizedPlayerId" in source
    assert "['null','undefined','none']" in source
    assert "const id=normalizedPlayerId(trigger.dataset.playerIntelligenceId);if(!id)return" in source
    assert "encodeURIComponent(id)" in source
    assert "encodeURIComponent(activeId)" not in source


def test_live_corrective_cleans_ppg_unavailable_reason_without_inventing_games() -> None:
    source = _text("player_intelligence.js")
    assert "replace(/^unavailable:\\s*/i,'')" in source
    assert "PPG unavailable unavailable" not in source
    assert "17-game display rate" not in source


def test_live_corrective_busts_mobile_player_intelligence_cache() -> None:
    index = _text("index.html")
    assert "player_intelligence.js?pi=20260922-player-intelligence-north-star1&v=20260913-phase3-latency1" in index
    assert "player_intelligence.css?pi=20260922-player-intelligence-north-star1&v=20260913-phase3-latency1" in index
    assert "product_shell.js?v=20260913-phase3-latency1" in index


def test_full_career_mobile_history_keeps_summary_and_expansion_state() -> None:
    source = _text("player_intelligence.js")
    css = _text("player_intelligence.css")
    assert "expandedSeasons" in source
    assert "sheetScrollTop" in source
    assert "data-pi-season" in source
    assert "restoreViewState" in source
    assert "Fantasy points" in source
    assert "Fantasy PPG" in source
    assert "games_played_basis" in source
    assert "More stats" in source
    assert "summary span:nth-child(n+3){display:none}" not in css


def test_full_career_mobile_trajectory_is_horizontally_bounded_not_microscopic() -> None:
    css = _text("player_intelligence.css")
    assert "overflow-x:auto" in css
    assert ".pi-trajectory-scroll" in css
    assert ".pi-trajectory-svg{height:240px;width:auto}" in css
    assert "overscroll-behavior-x:contain" in css


def test_historical_standard_stat_labels_cover_qb_rb_wr_te_box_score_fields() -> None:
    source = _text("player_intelligence.js")
    for token in (
        "pass_att:'Pass att'",
        "pass_cmp:'Completions'",
        "pass_yd:'Pass yds'",
        "pass_td:'Pass TD'",
        "pass_int:'INT'",
        "rush_att:'Rush att'",
        "rush_yd:'Rush yds'",
        "rush_td:'Rush TD'",
        "rec_tgt:'Targets'",
        "rec:'Receptions'",
        "rec_yd:'Rec yds'",
        "rec_td:'Rec TD'",
        "fum:'Fumbles'",
        "fum_lost:'Fumbles lost'",
    ):
        assert token in source



def test_intrinsic_never_falls_through_to_a_silent_dash() -> None:
    source = _text("player_intelligence.js")
    franchise = _text("my_team_dashboard.js")
    assert "function intrinsicReason(v)" in source
    assert "return'Unavailable'" in source
    assert "intrinsic_error" in source
    assert "intrinsic_status_reason" in source
    assert "franchise-intrinsic-unavailable" in franchise
    assert "Governed FSFFL Intrinsic is unavailable for the current league state." in franchise


def test_forecast_detail_keeps_expected_as_centerline_and_does_not_relabel_it_p50() -> None:
    source = _text("player_intelligence.js")
    assert "Expected · governed economic centerline" in source
    assert "<small>Median (P50)</small>" in source
    assert "<small>IQR (P25–P75)</small>" in source
    assert "<small>P10–P90</small>" in source



def test_north_star_visual_rebuild_matches_approved_information_hierarchy() -> None:
    source = _text("player_intelligence.js")
    css = _text("player_intelligence.css")
    for token in (
        "pi-summary-grid",
        "pi-value-gauge",
        "pi-compare-card",
        "pi-trajectory-frame",
        "pi-drill-button",
        "Governed future distribution",
        "Year-by-year production",
    ):
        assert token in source or token in css
    assert "Actual → Forecast" in source
    assert "Expected" in source
    assert "Median (P50)" in source
    assert "IQR (P25–P75)" in source
    assert "P10–P90" in source
    assert "background:radial-gradient" in css
    assert ".pi-tabs button.active:after" in css


def test_north_star_history_is_compact_segmented_table_not_tall_default_cards() -> None:
    source = _text("player_intelligence.js")
    css = _text("player_intelligence.css")
    for label in ("Passing", "Rushing", "Receiving", "Fantasy"):
        assert label in source
    assert "pi-history-segments" in source
    assert "pi-history-table" in source
    assert "Historical fantasy scoring uses current league rules" in source
    assert ".pi-history-table-wrap" in css
    assert ".pi-history-segments button.active" in css


def test_north_star_overview_keeps_decision_relevant_content_in_first_screenful() -> None:
    source = _text("player_intelligence.js")
    assert "Season Projection" in source
    assert "Broad Market" in source
    assert "FSFFL Intrinsic" in source
    assert "valueComparison()" in source
    assert "Open detail" in source
    assert "Career trajectory" in source


def test_north_star_value_comparison_only_presents_descriptive_governed_lenses() -> None:
    source = _text("player_intelligence.js")
    assert "shared 0–10,000 presentation ruler" in source
    assert "separate governed lenses" in source
    assert "This is not a buy/sell command." in source
    assert "Value comparison unavailable" in source
