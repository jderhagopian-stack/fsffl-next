from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from fsffl.forecast.i1_config import FROZEN_I1_REGULARIZATION
from fsffl.forecast.i1_current_facts import CurrentI1MappingResult
from fsffl.forecast.integrated_i1 import I1ForecastInput, I1ForecastResult, STATE_NAMES
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueRules, Position

from .shapley_intrinsic import (
    FROZEN_INTRINSIC_DISCOUNT,
    FROZEN_SHAPLEY_PERMUTATIONS,
    FROZEN_SHAPLEY_SEED,
    FutureStateForecast,
    IntrinsicShapleyEstimate,
    PlayerIntrinsicForecast,
    build_intrinsic_shapley_estimates,
)

LIVE_INTRINSIC_CALENDAR_VERSION = "live-intrinsic-calendar-v1:year1-live-h2-h3-direct"


class I1Predictor(Protocol):
    def predict(
        self,
        item: I1ForecastInput,
        *,
        fallback_probabilities: Mapping[str, float] | None = None,
    ) -> I1ForecastResult: ...


FutureI1ResultTranslator = Callable[[str, I1ForecastResult], I1ForecastResult]


@dataclass(frozen=True)
class LiveYearOneCoordinate:
    target_season: int
    anticipated_points: float
    stddev: float
    source: str
    model_version: str
    authority: str = "governed_live_current_season_forecast"


@dataclass(frozen=True)
class CompletedSourceI1Coordinate:
    source_season: int
    horizon: int
    target_season: int
    result: I1ForecastResult
    diagnostic_only: bool
    regularization_policy_version: str = FROZEN_I1_REGULARIZATION.version
    regularization_c: float = FROZEN_I1_REGULARIZATION.default_c

    @property
    def state_entropy(self) -> float:
        return -sum(
            float(probability) * math.log(max(1e-12, float(probability)))
            for probability in self.result.probabilities.values()
            if float(probability) > 0
        )


@dataclass(frozen=True)
class LiveThreeYearPlayerCoordinate:
    player_id: str
    position: Position
    evaluation_season: int
    year_1: LiveYearOneCoordinate
    diagnostic_h1: CompletedSourceI1Coordinate
    year_2: CompletedSourceI1Coordinate
    year_3: CompletedSourceI1Coordinate
    calendar_version: str = LIVE_INTRINSIC_CALENDAR_VERSION

    def __post_init__(self) -> None:
        if self.year_1.target_season != self.evaluation_season:
            raise ValueError("live Year 1 must target the evaluation season")
        if self.diagnostic_h1.target_season != self.evaluation_season or self.diagnostic_h1.horizon != 1:
            raise ValueError("completed-source h=1 must target the evaluation season and remain diagnostic")
        if not self.diagnostic_h1.diagnostic_only:
            raise ValueError("completed-source h=1 must be diagnostic only")
        if self.year_2.horizon != 2 or self.year_2.target_season != self.evaluation_season + 1:
            raise ValueError("live Year 2 must be completed-source direct h=2")
        if self.year_3.horizon != 3 or self.year_3.target_season != self.evaluation_season + 2:
            raise ValueError("live Year 3 must be completed-source direct h=3")
        if self.year_2.diagnostic_only or self.year_3.diagnostic_only:
            raise ValueError("live Year 2/3 coordinates cannot be diagnostic-only")

    def as_shapley_forecast(self) -> PlayerIntrinsicForecast:
        """Return the frozen Shapley consumer contract with h=1 hard-excluded.

        The diagnostic completed-source h=1 coordinate is intentionally not read
        here. Year 1 comes only from the governed live/current-season Forecast.
        """

        return PlayerIntrinsicForecast(
            player_id=self.player_id,
            position=self.position,
            current_points=max(0.0, self.year_1.anticipated_points),
            year_2=FutureStateForecast(
                probabilities=self.year_2.result.probabilities,
                state_means=self.year_2.result.state_means,
                anticipated_points=self.year_2.result.anticipated_points,
            ),
            year_3=FutureStateForecast(
                probabilities=self.year_3.result.probabilities,
                state_means=self.year_3.result.state_means,
                anticipated_points=self.year_3.result.anticipated_points,
            ),
        )


@dataclass(frozen=True)
class LiveIntrinsicCalendarResult:
    forecasts: tuple[LiveThreeYearPlayerCoordinate, ...]
    evaluation_season: int
    completed_source_season: int
    calendar_version: str = LIVE_INTRINSIC_CALENDAR_VERSION

    @property
    def player_count(self) -> int:
        return len(self.forecasts)


@dataclass(frozen=True)
class LiveCalendarShapleyResult:
    calendar: LiveIntrinsicCalendarResult
    estimates: tuple[IntrinsicShapleyEstimate, ...]
    discount: float = FROZEN_INTRINSIC_DISCOUNT
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS
    seed: int = FROZEN_SHAPLEY_SEED


def _year_one_index(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    by_player: dict[str, ForecastObservation] = {}
    for observation in observations:
        if observation.metric != ForecastMetric.FANTASY_POINTS or observation.horizon != ForecastHorizon.SEASON:
            continue
        prior = by_player.get(observation.player_id)
        if prior is not None:
            raise ValueError(f"multiple governed live Year-1 season forecasts for {observation.player_id}")
        by_player[observation.player_id] = observation
    return by_player


def compose_live_intrinsic_calendar(
    *,
    live_year_one_forecasts: tuple[ForecastObservation, ...],
    mapping: CurrentI1MappingResult,
    h1_h2_predictor: I1Predictor,
    h3_predictor: I1Predictor,
    future_i1_result_translator: FutureI1ResultTranslator | None = None,
) -> LiveIntrinsicCalendarResult:
    """Compose the management-authorized live three-year Forecast coordinate.

    Calendar ownership is explicit and non-overlapping:
      * Year 1 / E: governed live current-season Forecast;
      * Year 2 / E+1: completed-source direct I1 h=2;
      * Year 3 / E+2: completed-source direct I1 h=3.

    Completed-source h=1 is predicted only for diagnostics/parity and is never
    consumed as Year 1 or by the Shapley conversion.
    """

    if mapping.unmapped_player_ids or mapping.ambiguous_player_ids:
        raise ValueError(
            "authoritative live Intrinsic calendar requires fail-closed completed-source coverage; "
            f"unmapped={mapping.unmapped_player_ids}; ambiguous={mapping.ambiguous_player_ids}"
        )

    year_one = _year_one_index(live_year_one_forecasts)
    output: list[LiveThreeYearPlayerCoordinate] = []
    for player_id in sorted(mapping.inputs):
        live = year_one.get(player_id)
        if live is None:
            raise ValueError(f"missing governed live Year-1 Forecast for {player_id}")
        h1_input = mapping.input_for(player_id, 1)
        h2_input = mapping.input_for(player_id, 2)
        h3_input = mapping.input_for(player_id, 3)
        if not (
            h1_input.current_points == h2_input.current_points == h3_input.current_points
            and h1_input.prior_points == h2_input.prior_points == h3_input.prior_points
        ):
            raise ValueError("direct I1 horizons must share completed-source factual inputs")

        h1 = h1_h2_predictor.predict(h1_input)
        h2 = h1_h2_predictor.predict(h2_input)
        h3 = h3_predictor.predict(h3_input)
        if future_i1_result_translator is not None:
            h1 = future_i1_result_translator(player_id, h1)
            h2 = future_i1_result_translator(player_id, h2)
            h3 = future_i1_result_translator(player_id, h3)
        source_season = mapping.completed_source_season
        output.append(
            LiveThreeYearPlayerCoordinate(
                player_id=player_id,
                position=h1_input.position,
                evaluation_season=mapping.evaluation_season,
                year_1=LiveYearOneCoordinate(
                    target_season=mapping.evaluation_season,
                    anticipated_points=max(0.0, float(live.distribution.mean)),
                    stddev=max(0.0, float(live.distribution.stddev)),
                    source=live.source,
                    model_version=live.model_version,
                    authority=(
                        "preserved_preseason_year1_forecast"
                        if live.source.startswith("fsffl:preseason_baseline")
                        else "governed_live_current_season_forecast"
                    ),
                ),
                diagnostic_h1=CompletedSourceI1Coordinate(
                    source_season=source_season,
                    horizon=1,
                    target_season=mapping.target_season(1),
                    result=h1,
                    diagnostic_only=True,
                ),
                year_2=CompletedSourceI1Coordinate(
                    source_season=source_season,
                    horizon=2,
                    target_season=mapping.target_season(2),
                    result=h2,
                    diagnostic_only=False,
                ),
                year_3=CompletedSourceI1Coordinate(
                    source_season=source_season,
                    horizon=3,
                    target_season=mapping.target_season(3),
                    result=h3,
                    diagnostic_only=False,
                ),
            )
        )

    return LiveIntrinsicCalendarResult(
        forecasts=tuple(output),
        evaluation_season=mapping.evaluation_season,
        completed_source_season=mapping.completed_source_season,
    )


def build_live_calendar_shapley_estimates(
    calendar: LiveIntrinsicCalendarResult,
    *,
    rules: LeagueRules,
    permutations: int = FROZEN_SHAPLEY_PERMUTATIONS,
    seed: int = FROZEN_SHAPLEY_SEED,
) -> LiveCalendarShapleyResult:
    """Apply frozen Shapley only after the live calendar is explicitly aligned."""

    forecasts = tuple(item.as_shapley_forecast() for item in calendar.forecasts)
    estimates = build_intrinsic_shapley_estimates(
        forecasts,
        rules=rules,
        permutations=permutations,
        seed=seed,
    )
    return LiveCalendarShapleyResult(
        calendar=calendar,
        estimates=estimates,
        permutations=permutations,
        seed=seed,
    )
