from __future__ import annotations

import pytest
from pydantic import ValidationError

from fsffl.forecast.future_contract import (
    FUTURE_FORECAST_CONTRACT_VERSION,
    ForecastUncertaintyKind,
    FutureForecastContract,
    FutureForecastScenario,
    FuturePlayerHorizonForecast,
)
from fsffl.state.models import Position


def _row(
    *,
    year_index: int = 2,
    scenarios: tuple[FutureForecastScenario, ...] | None = None,
) -> FuturePlayerHorizonForecast:
    support = scenarios or (
        FutureForecastScenario(scenario_id="out", probability=0.25, fantasy_points=0.0),
        FutureForecastScenario(scenario_id="active", probability=0.75, fantasy_points=160.0),
    )
    return FuturePlayerHorizonForecast(
        player_id="p1",
        position=Position.WR,
        evaluation_season=2026,
        year_index=year_index,
        target_season=2026 + year_index - 1,
        central_expectation=120.0,
        scoring_coordinate="league_points",
        model_version="forecast-fixture-v1",
        source="fixture",
        uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
        scenarios=support,
        evidence_path="full",
    )


def test_future_forecast_contract_is_model_agnostic_and_reconciles_scenarios() -> None:
    contract = FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate="league_points",
        forecast_model_version="forecast-fixture-v1",
        forecast_source="fixture",
        forecasts=(_row(year_index=2), _row(year_index=3)),
        provenance={"provider_neutral_contract": True},
    )

    assert contract.contract_version == FUTURE_FORECAST_CONTRACT_VERSION
    assert contract.player_ids == ("p1",)
    assert [row.year_index for row in contract.rows_for_player("p1")] == [2, 3]
    assert all(
        row.uncertainty_kind == ForecastUncertaintyKind.DISCRETE_SCENARIOS
        for row in contract.forecasts
    )


def test_discrete_scenarios_must_reconcile_to_central_expectation() -> None:
    with pytest.raises(ValidationError, match="central expectation"):
        FuturePlayerHorizonForecast(
            player_id="p1",
            position=Position.WR,
            evaluation_season=2026,
            year_index=2,
            target_season=2027,
            central_expectation=100.0,
            scoring_coordinate="league_points",
            model_version="forecast-fixture-v1",
            source="fixture",
            uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
            scenarios=(
                FutureForecastScenario(
                    scenario_id="out",
                    probability=0.5,
                    fantasy_points=0.0,
                ),
                FutureForecastScenario(
                    scenario_id="active",
                    probability=0.5,
                    fantasy_points=150.0,
                ),
            ),
        )


def test_contract_does_not_require_discrete_scenarios_for_future_versions() -> None:
    row = FuturePlayerHorizonForecast(
        player_id="p1",
        position=Position.RB,
        evaluation_season=2026,
        year_index=2,
        target_season=2027,
        central_expectation=145.0,
        scoring_coordinate="league_points",
        model_version="hierarchical-fixture-v1",
        source="fixture",
        uncertainty_kind=ForecastUncertaintyKind.QUANTILES,
        p10=70.0,
        p25=100.0,
        p50=140.0,
        p75=190.0,
        p90=230.0,
    )
    contract = FutureForecastContract(
        evaluation_season=2026,
        scoring_coordinate="league_points",
        forecast_model_version="hierarchical-fixture-v1",
        forecast_source="fixture",
        forecasts=(row,),
    )
    assert contract.forecasts[0].scenarios == ()



def test_future_forecast_iqr_quantiles_must_remain_ordered() -> None:
    with pytest.raises(ValidationError, match="p10 <= p25 <= p50 <= p75 <= p90"):
        FuturePlayerHorizonForecast(
            player_id="p1",
            position=Position.WR,
            evaluation_season=2026,
            year_index=2,
            target_season=2027,
            central_expectation=120.0,
            scoring_coordinate="league_points",
            model_version="forecast-fixture-v2",
            source="fixture",
            uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
            p10=40.0,
            p25=100.0,
            p50=90.0,
            p75=160.0,
            p90=220.0,
            scenarios=(
                FutureForecastScenario(
                    scenario_id="out",
                    probability=0.25,
                    fantasy_points=0.0,
                ),
                FutureForecastScenario(
                    scenario_id="active",
                    probability=0.75,
                    fantasy_points=160.0,
                ),
            ),
        )
