from datetime import UTC, datetime

import pytest

from fsffl.team_utility import (
    CalculatedCompetitiveState,
    FranchiseAssetPortfolio,
    RosterResilience,
    TeamCompetitiveOutcome,
    TeamUtilityVector,
    compare_team_utility_vectors,
)
from fsffl.value.models import ValueDistribution, ValueScale


AS_OF = datetime(2026, 9, 5, 16, 0, tzinfo=UTC)
SCALE = ValueScale(scale_id="dynasty", version="v1", unit_label="points")


def vector(
    *,
    wins: float,
    playoff: float,
    first: float,
    drop: float,
    bench: int,
    mean_value: float,
    scale: ValueScale = SCALE,
    state: CalculatedCompetitiveState = CalculatedCompetitiveState.COMPETITIVE,
) -> TeamUtilityVector:
    return TeamUtilityVector(
        team_id="team:1",
        as_of=AS_OF,
        competitive_outcome=TeamCompetitiveOutcome(
            team_id="team:1",
            expected_wins=wins,
            wins_stddev=1.0,
            playoff_probability=playoff,
            first_place_probability=first,
            simulation_count=50_000,
            simulation_model_version="sim-v1",
        ),
        calculated_competitive_state=state,
        asset_portfolio=FranchiseAssetPortfolio(
            team_id="team:1",
            distribution=ValueDistribution(mean=mean_value, stddev=25.0),
            scale=scale,
            value_concept="market_price",
            value_model_versions=("value-v1",),
        ),
        roster_resilience=RosterResilience(
            team_id="team:1",
            starter_count=9,
            bench_forecasted_count=bench,
            unavailable_count=1,
            missing_forecast_count=0,
            largest_single_player_lineup_drop=drop,
            model_version="resilience-v1",
        ),
        model_version="utility-v1",
    )


def test_scenario_delta_keeps_channels_separate() -> None:
    baseline = vector(wins=7.0, playoff=0.45, first=0.10, drop=8.0, bench=4, mean_value=5000.0)
    scenario = vector(
        wins=8.2,
        playoff=0.62,
        first=0.18,
        drop=6.5,
        bench=5,
        mean_value=5250.0,
        state=CalculatedCompetitiveState.CONTENDER,
    )

    result = compare_team_utility_vectors(baseline, scenario)

    assert result.competitive is not None
    assert result.competitive.expected_wins == pytest.approx(1.2)
    assert result.competitive.playoff_probability == pytest.approx(0.17)
    assert result.resilience is not None
    assert result.resilience.largest_single_player_lineup_drop == pytest.approx(-1.5)
    assert result.resilience.bench_forecasted_count == 1
    assert result.asset_portfolio is not None
    assert result.asset_portfolio.mean_value == 250.0
    assert result.calculated_state_before == "competitive"
    assert result.calculated_state_after == "contender"


def test_scenario_delta_rejects_incompatible_value_scales() -> None:
    baseline = vector(wins=7.0, playoff=0.45, first=0.10, drop=8.0, bench=4, mean_value=5000.0)
    scenario = vector(
        wins=7.0,
        playoff=0.45,
        first=0.10,
        drop=8.0,
        bench=4,
        mean_value=5000.0,
        scale=ValueScale(scale_id="dynasty", version="v2", unit_label="points"),
    )

    with pytest.raises(ValueError, match="same value scale"):
        compare_team_utility_vectors(baseline, scenario)


def test_scenario_delta_rejects_cross_team_comparison() -> None:
    baseline = vector(wins=7.0, playoff=0.45, first=0.10, drop=8.0, bench=4, mean_value=5000.0)
    scenario = baseline.model_copy(update={"team_id": "team:2"})

    with pytest.raises(ValueError, match="same team"):
        compare_team_utility_vectors(baseline, scenario)
