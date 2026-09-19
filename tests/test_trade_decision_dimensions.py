from types import SimpleNamespace

from fsffl.product.trade_decision_dimensions import build_trade_decision_dimensions


class Dumpable(SimpleNamespace):
    def model_dump(self, *, mode: str = "python"):
        return dict(self.__dict__)


def _enum(value: str):
    return SimpleNamespace(value=value)


def _economic_net(*, intrinsic_delta: float, market_delta: float):
    scale = _enum("fsffl_cardinal_v1")
    return SimpleNamespace(
        side_a=SimpleNamespace(
            team_id="team-a",
            intrinsic=SimpleNamespace(
                status=_enum("complete"),
                mean_delta=intrinsic_delta,
                sent_mean=100.0,
                received_mean=100.0 + intrinsic_delta,
                scale=scale,
            ),
            market=SimpleNamespace(
                status=_enum("complete"),
                mean_delta=market_delta,
                sent_mean=100.0,
                received_mean=100.0 + market_delta,
                scale=scale,
            ),
        ),
        side_b=SimpleNamespace(team_id="team-b"),
    )


def _adjusted_market(delta: float):
    return SimpleNamespace(
        side_a=SimpleNamespace(
            team_id="team-a",
            status=_enum("complete"),
            roster_adjusted_market_delta=delta,
            raw_trade_market_delta=delta + 3.0,
            mandatory_cut_market_cost=3.0,
            required_cut_count=1,
        ),
        side_b=SimpleNamespace(team_id="team-b"),
    )


def _material_assessment():
    side_a = SimpleNamespace(
        team_id="team-a",
        expected_wins=_enum("material_gain"),
        playoff_probability=_enum("material_gain"),
        championship_probability=_enum("immaterial"),
        largest_single_player_lineup_drop=_enum("immaterial"),
        market_value=_enum("material_gain"),
        intrinsic_value=_enum("material_loss"),
    )
    return SimpleNamespace(side_a=side_a, side_b=SimpleNamespace(team_id="team-b"))


def _scenario_delta():
    return SimpleNamespace(
        competitive=SimpleNamespace(
            expected_wins=0.8,
            playoff_probability=0.06,
            first_place_probability=0.03,
            championship_probability=0.01,
        ),
        resilience=Dumpable(
            largest_single_player_lineup_drop=-1.2,
            bench_forecasted_count=1,
            unavailable_count=0,
            missing_forecast_count=0,
        ),
    )


def test_complete_contract_keeps_near_term_and_long_term_channels_separate() -> None:
    result = build_trade_decision_dimensions(
        focal_team_id="team-a",
        scenario_delta=_scenario_delta(),
        economic_net=_economic_net(intrinsic_delta=-18.0, market_delta=12.0),
        roster_adjusted_market_net=_adjusted_market(9.0),
        material_assessment=_material_assessment(),
        simulation_backed=True,
    )

    assert result["near_term_competitive"]["expected_wins_delta"] == 0.8
    assert result["near_term_competitive"]["materiality"]["expected_wins"] == "material_gain"
    assert result["long_term_franchise_value"]["net_delta"] == -18.0
    assert result["long_term_franchise_value"]["materiality"] == "material_loss"
    assert result["market_economics"]["net_delta"] == 9.0
    assert result["market_economics"]["mandatory_cut_cost"] == 3.0
    assert result["confidence"]["evidence_completeness"] == "complete"
    assert result["combined_master_score"] is None


def test_fast_contract_does_not_promote_competitive_delta_without_simulation_authority() -> None:
    result = build_trade_decision_dimensions(
        focal_team_id="team-a",
        scenario_delta=_scenario_delta(),
        economic_net=_economic_net(intrinsic_delta=5.0, market_delta=4.0),
        roster_adjusted_market_net=_adjusted_market(4.0),
        material_assessment=None,
        simulation_backed=False,
    )

    assert result["near_term_competitive"]["available"] is False
    assert result["near_term_competitive"]["expected_wins_delta"] is None
    assert result["long_term_franchise_value"]["available"] is True
    assert "near_term_competitive" in result["confidence"]["missing_dimensions"]
    assert result["combined_master_score"] is None
