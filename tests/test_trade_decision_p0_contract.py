from pathlib import Path

from fsffl.trade_decision.disposition import _metric_sets
from fsffl.trade_decision.material_assessment import SideMaterialAssessment
from fsffl.trade_decision.materiality import MaterialityDirection


ROOT = Path("src/fsffl")
FAST_RUNTIME = ROOT / "product" / "trade_analysis_runtime.py"
SIM_RUNTIME = ROOT / "product" / "trade_simulation_runtime.py"


def _side(*, intrinsic: MaterialityDirection) -> SideMaterialAssessment:
    neutral = MaterialityDirection.NEUTRAL
    return SideMaterialAssessment(
        team_id="team-a",
        expected_wins=neutral,
        playoff_probability=neutral,
        first_place_probability=neutral,
        championship_probability=neutral,
        largest_single_player_lineup_drop=neutral,
        market_value=neutral,
        intrinsic_value=intrinsic,
    )


def test_intrinsic_franchise_value_is_action_facing_once_in_disposition_metric_sets() -> None:
    gains, losses, unavailable = _metric_sets(
        _side(intrinsic=MaterialityDirection.MATERIAL_LOSS)
    )
    assert gains == ()
    assert losses == ("intrinsic_value",)
    assert unavailable == ()

    gains, losses, unavailable = _metric_sets(
        _side(intrinsic=MaterialityDirection.MATERIAL_GAIN)
    )
    assert gains == ("intrinsic_value",)
    assert losses == ()
    assert unavailable == ()


def test_fast_trade_analysis_explicitly_declares_partial_pre_simulation_scope() -> None:
    source = FAST_RUNTIME.read_text(encoding="utf-8")
    for phrase in (
        '"status": "partial_pre_simulation"',
        '"simulation_backed": False',
        '"final_disposition_available": False',
        '"decision_scope": "bilateral_roster_consequence_classification"',
        '"final_trade_disposition": False',
    ):
        assert phrase in source


def test_simulation_backed_trade_response_explicitly_declares_complete_scope() -> None:
    source = SIM_RUNTIME.read_text(encoding="utf-8")
    for phrase in (
        '"status": "complete_simulation_backed"',
        '"simulation_backed": True',
        '"final_disposition_available": True',
        '"decision_scope": "complete_trade_disposition"',
        '"final_trade_disposition": True',
        "intrinsic-action-facing",
    ):
        assert phrase in source
