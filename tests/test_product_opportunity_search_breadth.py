from pathlib import Path
from types import SimpleNamespace

from fsffl.product.opportunity_search import (
    _family_first_search_order,
    _multi_lane_search_order,
    _posture_target_admission,
)
from fsffl.product.trade_center_view import TradeAssetOption
from fsffl.state.models import Position
from fsffl.team_utility.utility import OwnerStrategicPosture


ROOT = Path(__file__).resolve().parents[1]


def _row(name: str, *, gap: float, target_value: float, focal: float, counterparty: float, send_count: int) -> dict[str, object]:
    return {
        "name": name,
        "market_gap_ratio": gap,
        "search_distance": gap * 100.0,
        "target_fsffl_value": target_value,
        "focal_position_strength_index": focal,
        "counterparty_receive_position_strength_index": counterparty,
        "send": [{"asset_ref": f"player:{name}:{index}"} for index in range(send_count)],
    }


def test_multi_lane_search_keeps_closest_market_match_first_but_admits_premium_target_early() -> None:
    rows = [
        _row("closest", gap=0.01, target_value=45.0, focal=95.0, counterparty=95.0, send_count=1),
        _row("market-two", gap=0.02, target_value=50.0, focal=90.0, counterparty=90.0, send_count=1),
        _row("premium", gap=0.30, target_value=99.0, focal=75.0, counterparty=80.0, send_count=3),
        _row("focal-need", gap=0.15, target_value=65.0, focal=40.0, counterparty=85.0, send_count=2),
        _row("counterparty-fit", gap=0.18, target_value=60.0, focal=80.0, counterparty=35.0, send_count=2),
    ]

    ordered = _multi_lane_search_order(rows)

    assert ordered[0]["name"] == "closest"
    assert [row["name"] for row in ordered[:5]].index("premium") < 4
    assert {row["name"] for row in ordered} == {row["name"] for row in rows}


def test_trade_search_supports_three_asset_premium_target_structures_without_consolidation_score() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()

    assert "_MAX_DISCOVERY_PACKAGE_SIZE = 3" in source
    assert '3: "three_for_one"' in source
    assert "for size in range(max(1, minimum_size), max_size + 1)" in source
    assert "the best single asset to veto all package complexity" in source
    assert "consolidation coefficient" in source
    assert "composite_score" not in source
    assert "opportunity_score" not in source


def test_both_trade_finder_spotlights_can_seed_nearby_package_frontier() -> None:
    ui = (ROOT / "src/fsffl/product/static/opportunity_spotlights.js").read_text()

    assert "opp-explore-market" in ui
    assert "opp-explore-promising" in ui
    assert "runSpotlightFrontier('market')" in ui
    assert "runSpotlightFrontier('decision')" in ui
    assert "spotlightFrontierKind" in ui
    assert "oppSpotlightSeedKey(kind)===requestKey" in ui


def test_family_first_search_order_admits_distinct_targets_before_package_repeats() -> None:
    rows = []
    for target, gap in (("gibbs", 0.01), ("bijan", 0.02), ("breece", 0.03)):
        for variant in range(1, 4):
            row = _row(
                f"{target}-{variant}",
                gap=gap + variant / 1000,
                target_value=95.0 - variant,
                focal=70.0,
                counterparty=75.0,
                send_count=variant,
            )
            row["counterparty_team_id"] = f"owner-{target}"
            row["receive"] = [{"asset_ref": f"player:{target}"}]
            rows.append(row)

    ordered = _family_first_search_order(rows)

    first_three = {
        (
            row["counterparty_team_id"],
            row["receive"][0]["asset_ref"],
        )
        for row in ordered[:3]
    }
    assert len(first_three) == 3
    assert {
        row["receive"][0]["asset_ref"]
        for row in ordered[:3]
    } == {"player:gibbs", "player:bijan", "player:breece"}
    assert len(ordered) == len(rows)



def test_competitive_posture_can_change_early_target_admission_without_composite_score() -> None:
    state = SimpleNamespace(
        players=(
            SimpleNamespace(player_id="young", position=Position.WR),
            SimpleNamespace(player_id="veteran", position=Position.WR),
        )
    )
    young = TradeAssetOption(
        asset_ref="player:young",
        asset_kind="player",
        label="Young WR",
        player_id="young",
        age_years=22.0,
    )
    veteran = TradeAssetOption(
        asset_ref="player:veteran",
        asset_kind="player",
        label="Veteran WR",
        player_id="veteran",
        age_years=29.0,
    )
    age_medians = {Position.WR: 25.0}
    forecast_medians = {Position.WR: 180.0}
    forecasts = {"young": 150.0, "veteran": 220.0}

    young_win, young_win_reason = _posture_target_admission(
        league_state=state,
        target=young,
        posture=OwnerStrategicPosture.WIN_NOW,
        age_medians=age_medians,
        forecast_medians=forecast_medians,
        forecasts=forecasts,
    )
    veteran_win, _ = _posture_target_admission(
        league_state=state,
        target=veteran,
        posture=OwnerStrategicPosture.WIN_NOW,
        age_medians=age_medians,
        forecast_medians=forecast_medians,
        forecasts=forecasts,
    )
    young_rebuild, young_rebuild_reason = _posture_target_admission(
        league_state=state,
        target=young,
        posture=OwnerStrategicPosture.REBUILD,
        age_medians=age_medians,
        forecast_medians=forecast_medians,
        forecasts=forecasts,
    )
    veteran_rebuild, _ = _posture_target_admission(
        league_state=state,
        target=veteran,
        posture=OwnerStrategicPosture.REBUILD,
        age_medians=age_medians,
        forecast_medians=forecast_medians,
        forecasts=forecasts,
    )

    assert (young_win, veteran_win) == (False, True)
    assert (young_rebuild, veteran_rebuild) == (True, False)
    assert "season Forecast" in young_win_reason
    assert "governed age" in young_rebuild_reason


def test_competitive_posture_missing_evidence_does_not_fabricate_exclusion() -> None:
    state = SimpleNamespace(
        players=(SimpleNamespace(player_id="unknown", position=Position.RB),)
    )
    target = TradeAssetOption(
        asset_ref="player:unknown",
        asset_kind="player",
        label="Unknown RB",
        player_id="unknown",
    )

    admitted, reason = _posture_target_admission(
        league_state=state,
        target=target,
        posture=OwnerStrategicPosture.WIN_NOW,
        age_medians={},
        forecast_medians={},
        forecasts={},
    )

    assert admitted is True
    assert "did not exclude" in reason
