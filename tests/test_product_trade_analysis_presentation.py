from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRADE_UI = ROOT / "src" / "fsffl" / "product" / "static" / "trade_center.js"
TRADE_RUNTIME = ROOT / "src" / "fsffl" / "product" / "trade_analysis_runtime.py"
WEBAPP = ROOT / "src" / "fsffl" / "product" / "webapp.py"


def test_trade_analysis_runtime_uses_authoritative_upstream_contracts() -> None:
    source = TRADE_RUNTIME.read_text()
    assert "apply_bilateral_trade" in source
    assert "assemble_team_utility_vector" in source
    assert "evaluate_bilateral_trade_deltas" in source
    assert "classify_bilateral_trade_decision" in source
    assert "summarize_bilateral_trade_economics" in source
    assert "provisional_fsffl_values" not in source
    assert '"provisional_fsffl_value_used_for_decision": False' in source


def test_trade_analysis_does_not_fake_simulation_or_acceptance() -> None:
    source = TRADE_RUNTIME.read_text()
    assert '"competitive_outcomes": False' in source
    assert '"acceptance_probability": False' in source
    assert "until the post-trade state is run through Simulation authority" in source
    assert "Acceptance probability is not estimated" in source


def test_hosted_webapp_has_a_default_governed_trade_analysis_path() -> None:
    source = WEBAPP.read_text()
    assert "build_private_beta_trade_analysis" in source
    assert "Trade analysis runtime is not configured yet" not in source
    assert "if trade_evaluator is not None" in source


def test_trade_center_renders_bilateral_analysis_instead_of_raw_json() -> None:
    source = TRADE_UI.read_text()
    assert "function renderTradeAnalysis(result)" in source
    assert "Bilateral consequence view" in source
    assert "Competitive impact" in source
    assert "Acceptance probability" in source
    assert "Provisional FSFFL Value shown in the builder is not used in this analysis." in source
    assert "JSON.stringify(result,null,2)" not in source
