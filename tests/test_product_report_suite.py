from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "src/fsffl/product/static/reports.js"


def test_power_rankings_use_authoritative_expected_wins_without_master_score() -> None:
    source = REPORTS.read_text(encoding="utf-8")
    assert "FSFFL Power Rankings" in source
    assert "reportOutcome(b).expected_wins-reportOutcome(a).expected_wins" in source
    assert "Ranked by authoritative expected wins from NEXT-4 Simulation" in source
    assert "Power ranking order is expected wins only" in source
    assert "No report-only coefficient" in source
    assert "master_score" not in source
    assert "composite_score" not in source


def test_preseason_guide_keeps_forecast_value_and_simulation_separate() -> None:
    source = REPORTS.read_text(encoding="utf-8")
    assert "FSFFL Preseason Guide" in source
    assert "The league, team by team" in source
    assert "Projected lineup leaders" in source
    assert "Most valuable current assets" in source
    assert "Championship odds" in source
    assert "full NFL-season Forecast observations" in source
    assert "FSFFL Value remains the authoritative NEXT-3 market-cardinal score" in source
    assert "Starter age is descriptive presentation math" in source
    assert "report-only team grade" in source


def test_report_switcher_exposes_publication_suite() -> None:
    source = REPORTS.read_text(encoding="utf-8")
    assert "['power','Power Rankings']" in source
    assert "['preseason','Preseason Guide']" in source
    assert "loadPowerRankings" in source
    assert "loadPreseasonGuide" in source
    assert "kind==='power'" in source
    assert "kind==='preseason'" in source
