from pathlib import Path

from fsffl.product.scenario_cache import ScenarioComputationStage
from fsffl.product.webapp import AnalyzeTradeRequest, EvaluateWaiverRequest, PlayerUnavailableRequest


ROOT = Path(__file__).resolve().parents[1]
WEBAPP = ROOT / "src/fsffl/product/webapp.py"
TRADE_OPPORTUNITY = ROOT / "src/fsffl/product/trade_opportunity_runtime.py"
TRADE_SIMULATION = ROOT / "src/fsffl/product/trade_simulation_runtime.py"
WAIVER_ACTION = ROOT / "src/fsffl/product/waiver_action_runtime.py"


def test_simulation_dependency_fingerprints_do_not_import_persistence_layer() -> None:
    source = (ROOT / "src/fsffl/product/simulation_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "fsffl.persistence" not in source
    assert "_scenario_dependency_fingerprint" in source


def test_interactive_scenario_requests_default_to_authoritative_confirmation() -> None:
    trade = AnalyzeTradeRequest(
        counterparty_team_id="b",
        focal_asset_refs=(),
        counterparty_asset_refs=(),
    )
    waiver = EvaluateWaiverRequest(add_player_id="p1")
    what_if = PlayerUnavailableRequest(player_id="p1")

    assert trade.scenario_stage == ScenarioComputationStage.CONFIRMATION
    assert waiver.scenario_stage == ScenarioComputationStage.CONFIRMATION
    assert what_if.scenario_stage == ScenarioComputationStage.CONFIRMATION


def test_web_routes_forward_explicit_progressive_stage() -> None:
    source = WEBAPP.read_text(encoding="utf-8")
    assert source.count("scenario_stage=request.scenario_stage") >= 4
    assert "__fsffl_progressive_loader_factory__" in source
    assert "__fsffl_selective_runner__" in source
    assert "simulation_count=50_000" in source


def test_non_authoritative_trade_preview_cannot_create_decision_or_opportunity_authority() -> None:
    trade = TRADE_SIMULATION.read_text(encoding="utf-8")
    opportunity = TRADE_OPPORTUNITY.read_text(encoding="utf-8")

    assert "if computation.authoritative:" in trade
    assert '"non_authoritative_scenario_preview"' in trade
    assert '"final_trade_disposition": decision_complete and computation.authoritative' in trade
    assert "if not computation[\"authoritative\"]:" in opportunity
    assert '"candidate": None' in opportunity
    assert "ActionAuthority.DIAGNOSTIC_ONLY.value" in opportunity
    assert "withheld until authoritative confirmation" in opportunity


def test_non_authoritative_waiver_preview_cannot_create_action_authority() -> None:
    source = WAIVER_ACTION.read_text(encoding="utf-8")
    assert 'if not comparison["scenario_computation"]["authoritative"]:' in source
    assert '"candidate": None' in source
    assert "ActionAuthority.DIAGNOSTIC_ONLY.value" in source
    assert "withheld until authoritative 50,000-run confirmation" in source
