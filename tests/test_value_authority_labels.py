from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "fsffl" / "product" / "static"


def test_market_cardinal_numbers_are_labeled_as_cardinal_market_value() -> None:
    opportunities = (STATIC / "opportunities.js").read_text(encoding="utf-8")
    assert "authoritative_cardinal_value:'FSFFL Cardinal Market Value'" in opportunities
    assert "<span>FSFFL Cardinal Market Value</span>" in opportunities
    assert "<th>FSFFL Cardinal Market Value</th>" in opportunities
    assert "authoritative_cardinal_value:'FSFFL Value'" not in opportunities
    assert "<span>FSFFL Value</span>" not in opportunities
    assert "<th>FSFFL Value</th>" not in opportunities


def test_trade_center_cardinal_context_is_not_presented_as_generic_fsffl_value() -> None:
    trade = (STATIC / "trade_center.js").read_text(encoding="utf-8")
    decision = (STATIC / "trade_decision_experience.js").read_text(encoding="utf-8")
    polish = (STATIC / "product_polish.js").read_text(encoding="utf-8")

    assert "FSFFL Cardinal Market Values shown above" in trade
    assert "FSFFL Cardinal Market Value is market context only" in trade
    assert "Authoritative FSFFL Cardinal Market Value is market context" in trade
    assert "FSFFL Cardinal Market Value remains market context" in decision
    assert "FSFFL Cardinal —" in trade
    assert "FSFFL Cardinal —" in polish


def test_trade_backend_names_missing_cut_value_as_cardinal_market_value() -> None:
    source = (
        ROOT / "src" / "fsffl" / "product" / "trade_analysis_runtime.py"
    ).read_text(encoding="utf-8")
    assert "lacks authoritative FSFFL Cardinal Market Value" in source
    assert "is not added to FSFFL Cardinal Market Value" in source


def test_franchise_and_simulator_copy_do_not_hide_value_coordinate() -> None:
    franchise = (STATIC / "my_team_dashboard.js").read_text(encoding="utf-8")
    simulator = (STATIC / "simulator.js").read_text(encoding="utf-8")
    assert "Your three highest current FSFFL Cardinal Market Values are" in franchise
    assert "Ownership and existing Value evidence remain unchanged." in simulator
