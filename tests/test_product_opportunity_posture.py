from pathlib import Path

from fsffl.product.opportunity_posture import (
    apply_search_posture,
    default_posture_for_state,
    resolve_search_posture,
)
from fsffl.team_utility.utility import CalculatedCompetitiveState, OwnerStrategicPosture


ROOT = Path(__file__).resolve().parents[1]


def _row(*, gap: float, value: float, strength: float, age: float) -> dict[str, object]:
    return {
        "market_gap_ratio": gap,
        "target_fsffl_value": value,
        "focal_position_strength_index": strength,
        "counterparty_receive_position_strength_index": 100.0,
        "send": [{"asset_ref": f"send:{gap}"}],
        "receive": [{"asset_ref": f"recv:{gap}", "age_years": age}],
    }


def test_default_posture_tracks_calculated_state_without_mutating_it() -> None:
    assert default_posture_for_state(CalculatedCompetitiveState.CONTENDER) is OwnerStrategicPosture.WIN_NOW
    assert default_posture_for_state(CalculatedCompetitiveState.COMPETITIVE) is OwnerStrategicPosture.BALANCED
    assert default_posture_for_state(CalculatedCompetitiveState.DEVELOPING) is OwnerStrategicPosture.RETOOL
    assert default_posture_for_state(CalculatedCompetitiveState.REBUILDING) is OwnerStrategicPosture.REBUILD
    assert (
        resolve_search_posture(
            OwnerStrategicPosture.DEFAULT_CALCULATED,
            CalculatedCompetitiveState.REBUILDING,
        )
        is OwnerStrategicPosture.REBUILD
    )


def test_win_now_posture_admits_roster_need_early_but_preserves_closest_market_match() -> None:
    closest = _row(gap=0.01, value=60.0, strength=100.0, age=25.0)
    need = _row(gap=0.25, value=75.0, strength=55.0, age=26.0)
    other = _row(gap=0.05, value=65.0, strength=90.0, age=24.0)
    ordered = apply_search_posture([closest, other, need], OwnerStrategicPosture.WIN_NOW)
    assert ordered[0] is closest
    assert ordered[1] is need


def test_rebuild_posture_admits_youth_early_but_preserves_market_spotlight() -> None:
    closest = _row(gap=0.01, value=60.0, strength=100.0, age=29.0)
    veteran = _row(gap=0.04, value=80.0, strength=80.0, age=28.0)
    youth = _row(gap=0.20, value=65.0, strength=95.0, age=21.0)
    ordered = apply_search_posture([closest, veteran, youth], OwnerStrategicPosture.REBUILD)
    assert ordered[0] is closest
    assert ordered[1] is youth


def test_explicit_posture_overrides_default_search_lens_only() -> None:
    assert (
        resolve_search_posture(
            OwnerStrategicPosture.WIN_NOW,
            CalculatedCompetitiveState.REBUILDING,
        )
        is OwnerStrategicPosture.WIN_NOW
    )


def test_posture_ui_selects_only_server_owned_views() -> None:
    script = (ROOT / "src/fsffl/product/static/opportunity_posture_ui.js").read_text()
    index = (ROOT / "src/fsffl/product/static/index.html").read_text()
    workspace = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text()

    assert "trade_discovery.posture_views" not in script
    assert "const views=discovery&&discovery.posture_views" in script
    assert "fsffl.tradeFinderPosture" in script
    assert "This changes Trade Finder discovery order only" in script
    assert "opportunity_posture_ui.js?v=20260908-tradefinder5" in index
    assert '"posture_views": posture_views' in workspace
    assert '"owner_strategic_posture_is_search_lens_only": True' in workspace
    assert '"browser_selects_server_owned_posture_views_only": True' in workspace
