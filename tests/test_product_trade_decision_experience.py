from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIENCE = ROOT / "src/fsffl/product/static/trade_decision_experience.js"
INDEX = ROOT / "src/fsffl/product/static/index.html"


def test_trade_center_elevates_backend_disposition_after_simulation() -> None:
    source = EXPERIENCE.read_text(encoding="utf-8")
    assert "result?.disposition" in source
    assert "authoritative NEXT-5 disposition" in source
    assert "changed roster ran through NEXT-4 Simulation" in source
    assert "scenario_simulation_count" in source
    assert "elevateFinalDecision(result)" in source
    assert "window.renderTradeSimulationResult" in source


def test_fast_trade_analysis_remains_preliminary_until_changed_state_simulation() -> None:
    source = EXPERIENCE.read_text(encoding="utf-8")
    assert "Preliminary read" in source
    assert "Run the changed-roster simulation to finish the recommendation" in source
    assert "not the final action disposition" in source
    assert "installPreliminaryRead(result)" in source


def test_frontier_interpretation_stays_diagnostic_and_does_not_invent_acceptance() -> None:
    source = EXPERIENCE.read_text(encoding="utf-8")
    assert "Closest mutual-gain package candidate" in source
    assert "Best path to investigate" in source
    assert "diagnostic price discovery" in source
    assert "not an acceptance forecast or action recommendation" in source
    assert "unknown materiality or acceptance evidence still fails closed" in source
    assert "acceptance_probability" not in source
    assert "best counter" not in source.lower()


def test_trade_decision_experience_only_translates_existing_authority() -> None:
    source = EXPERIENCE.read_text(encoding="utf-8")
    assert "dispositionAction(result)" in source
    assert "feasibility_shape==='mutual_gain_candidate'" in source
    assert "search_distance" in source
    assert "FSFFL Value remains market context" in source
    assert "no acceptance probability is invented" in source
    assert "*10000" not in source.replace(" ", "")
    assert "composite_score" not in source.lower()
    assert "master_score" not in source.lower()


def test_trade_decision_experience_loads_after_trade_center() -> None:
    html = INDEX.read_text(encoding="utf-8")
    assert "/static/trade_decision_experience.js?v=" in html
    assert html.index("trade_center.js") < html.index("trade_decision_experience.js")
