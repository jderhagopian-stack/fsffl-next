from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "fsffl" / "product" / "static"


def test_primary_market_copy_keeps_cardinal_internal() -> None:
    opportunities = (STATIC / "opportunities.js").read_text(encoding="utf-8")
    assert "Internal Value compatibility" in opportunities
    assert "Broad Market / Intrinsic" in opportunities
    assert "Broad Market and FSFFL Intrinsic remain separate user-facing evidence lenses" in opportunities
    assert "FSFFL Cardinal Market Value" not in opportunities
    assert "through Cardinal Value" not in opportunities


def test_trade_center_foregrounds_broad_market_and_decision_not_cardinal() -> None:
    trade = (STATIC / "trade_center.js").read_text(encoding="utf-8")
    polish = (STATIC / "product_polish.js").read_text(encoding="utf-8")

    assert "Broad Market percentiles shown above are market context only" in trade
    assert "Decision owns bilateral package economics and consequences" in trade
    assert "Broad Market and FSFFL Intrinsic are evidence lenses" in trade
    assert "Broad Market —" in trade
    assert "Broad Market —" in polish
    assert "FSFFL Cardinal Market Values shown above" not in trade



def test_trade_backend_names_missing_cut_value_as_cardinal_market_value() -> None:
    source = (
        ROOT / "src" / "fsffl" / "product" / "trade_analysis_runtime.py"
    ).read_text(encoding="utf-8")
    assert "lacks authoritative FSFFL Cardinal Market Value" in source
    assert "is not added to FSFFL Cardinal Market Value" in source


def test_franchise_foregrounds_market_intrinsic_and_preserves_simulator_boundaries() -> None:
    franchise = (STATIC / "my_team_dashboard.js").read_text(encoding="utf-8")
    simulator = (STATIC / "simulator.js").read_text(encoding="utf-8")
    assert "FSFFL Intrinsic" in franchise
    assert "Broad Market" in franchise
    assert "fsffl_cardinal_values" not in franchise
    assert "Ownership and governed Value coordinates remain unchanged." in simulator
