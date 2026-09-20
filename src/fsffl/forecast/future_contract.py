from __future__ import annotations

import math
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position


FUTURE_FORECAST_CONTRACT_VERSION = "future-forecast-contract-v1"


class ForecastUncertaintyKind(StrEnum):
    NONE = "none"
    MOMENTS = "moments"
    QUANTILES = "quantiles"
    DISCRETE_SCENARIOS = "discrete_scenarios"


class FutureForecastScenario(FrozenModel):
    """One model-agnostic discrete outcome support point.

    Scenario identifiers are descriptive only. Consumers must not assume a fixed
    vocabulary such as P0/I1 state names unless their own adapter explicitly
    declares support for that vocabulary.
    """

    scenario_id: str
    probability: Annotated[float, Field(ge=0.0, le=1.0)]
    fantasy_points: Annotated[float, Field(ge=0.0)]

    @field_validator("scenario_id")
    @classmethod
    def require_scenario_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("future Forecast scenario_id cannot be empty")
        return value


class FuturePlayerHorizonForecast(FrozenModel):
    """Governed future player output independent of a specific Forecast model.

    A Forecast version may provide only a central expectation, moments/quantiles,
    discrete scenarios, or a combination. The current P0 adapter emits discrete
    scenarios; future versions are not required to use that representation.
    """

    player_id: str
    position: Position
    evaluation_season: Annotated[int, Field(ge=2000)]
    year_index: Annotated[int, Field(ge=2)]
    target_season: Annotated[int, Field(ge=2000)]
    central_expectation: Annotated[float, Field(ge=0.0)]
    scoring_coordinate: str
    model_version: str
    source: str
    uncertainty_kind: ForecastUncertaintyKind = ForecastUncertaintyKind.NONE
    stddev: Annotated[float | None, Field(ge=0.0)] = None
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    scenarios: tuple[FutureForecastScenario, ...] = ()
    evidence_path: str | None = None

    @field_validator("player_id", "scoring_coordinate", "model_version", "source")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("future Forecast identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_distribution(self) -> "FuturePlayerHorizonForecast":
        if self.target_season != self.evaluation_season + self.year_index - 1:
            raise ValueError("future Forecast target season must align with year_index")

        supplied_quantiles = [self.p10, self.p50, self.p90]
        concrete_quantiles = [value for value in supplied_quantiles if value is not None]
        if concrete_quantiles != sorted(concrete_quantiles):
            raise ValueError("future Forecast quantiles must be ordered p10 <= p50 <= p90")

        if self.uncertainty_kind == ForecastUncertaintyKind.DISCRETE_SCENARIOS:
            if not self.scenarios:
                raise ValueError("discrete-scenario Forecast must provide scenarios")
            ids = [scenario.scenario_id for scenario in self.scenarios]
            if len(ids) != len(set(ids)):
                raise ValueError("future Forecast scenario ids must be unique")
            probability_sum = sum(float(scenario.probability) for scenario in self.scenarios)
            if not math.isclose(probability_sum, 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("future Forecast scenario probabilities must sum to one")
            expected = sum(
                float(scenario.probability) * float(scenario.fantasy_points)
                for scenario in self.scenarios
            )
            if not math.isclose(
                expected,
                float(self.central_expectation),
                rel_tol=0.0,
                abs_tol=1e-8,
            ):
                raise ValueError(
                    "future Forecast central expectation must reconcile to scenarios"
                )
        elif self.scenarios:
            raise ValueError(
                "future Forecast scenarios require uncertainty_kind=discrete_scenarios"
            )

        if self.uncertainty_kind == ForecastUncertaintyKind.MOMENTS and self.stddev is None:
            raise ValueError("moment-based future Forecast requires stddev")
        if self.uncertainty_kind == ForecastUncertaintyKind.QUANTILES and not concrete_quantiles:
            raise ValueError("quantile-based future Forecast requires quantiles")
        return self


class FutureForecastContract(FrozenModel):
    """Versioned Forecast-owned boundary for downstream dynasty consumers."""

    contract_version: str = FUTURE_FORECAST_CONTRACT_VERSION
    evaluation_season: Annotated[int, Field(ge=2000)]
    scoring_coordinate: str
    forecast_model_version: str
    forecast_source: str
    forecasts: tuple[FuturePlayerHorizonForecast, ...]
    provenance: dict[str, bool | float | int | str | None] = Field(default_factory=dict)

    @field_validator(
        "contract_version",
        "scoring_coordinate",
        "forecast_model_version",
        "forecast_source",
    )
    @classmethod
    def require_contract_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("future Forecast contract identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_contract(self) -> "FutureForecastContract":
        if not self.forecasts:
            raise ValueError("future Forecast contract cannot be empty")
        keys: set[tuple[str, int]] = set()
        for item in self.forecasts:
            if item.evaluation_season != self.evaluation_season:
                raise ValueError("future Forecast rows must share evaluation season")
            if item.scoring_coordinate != self.scoring_coordinate:
                raise ValueError("future Forecast rows must share scoring coordinate")
            key = (item.player_id, item.year_index)
            if key in keys:
                raise ValueError(
                    f"duplicate future Forecast player/year row: {item.player_id} Y{item.year_index}"
                )
            keys.add(key)
        return self

    def rows_for_player(self, player_id: str) -> tuple[FuturePlayerHorizonForecast, ...]:
        return tuple(
            row
            for row in self.forecasts
            if row.player_id == player_id
        )

    @property
    def player_ids(self) -> tuple[str, ...]:
        return tuple(sorted({row.player_id for row in self.forecasts}))
