from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from fsffl.forecast.future_contract import (
    ForecastUncertaintyKind,
    FutureForecastContract,
    FutureForecastScenario,
    FuturePlayerHorizonForecast,
)
from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import ForecastObservation
from fsffl.state.models import LeagueState

from .i1_player_scoring import (
    FUTURE_I1_PLAYER_SCORING_VERSION,
    build_future_i1_player_scoring_multipliers,
    derive_future_i1_standard_year_one,
    translate_future_i1_result_for_player,
)
from .p0_forecast_runtime import (
    P0_CONNECTED_LEAGUE_Y1_BOARD_SHA256,
    P0_CURRENT_SOURCE_CSV_SHA256,
    P0_FINAL_ROUTE_AUTHORITY_SHA256,
    P0_FINAL_ROUTE_AUTHORITY_VERSION,
    P0_FORECAST_VERSION,
    P0_PACKAGE_SHA256,
    P0_SOURCE_SEASON,
    P0_STANDARD_Y1_BOARD_SHA256,
    build_p0_standard_future_materialization,
)


P0_FUTURE_FORECAST_SOURCE = "fsffl:p0_redeveloped_future_forecast"
P0_FUTURE_SCORING_COORDINATE = "connected_league_fantasy_points"


@dataclass(frozen=True)
class P0FutureForecastContractMaterialization:
    """Current P0 authority adapted to the stable future Forecast boundary."""

    contract: FutureForecastContract
    scoring_multipliers: Mapping[str, float]


def _multiplier_digest(scoring_multipliers: Mapping[str, float]) -> str:
    encoded = json.dumps(
        {
            player_id: float(multiplier)
            for player_id, multiplier in sorted(scoring_multipliers.items())
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_p0_future_forecast_contract(
    *,
    league_state: LeagueState,
    raw_forecasts: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
) -> P0FutureForecastContractMaterialization:
    """Materialize current P0 Y2/Y3 authority behind a model-agnostic contract.

    This adapter performs no fitting or route selection. It calls the frozen P0
    implementation unchanged, applies the already-promoted player-specific scoring
    translation once, and exposes the resulting governed distribution without
    requiring downstream product code to know D0/D1 internals.
    """

    standard_year_one = derive_future_i1_standard_year_one(
        raw_forecasts=raw_forecasts,
        rules=league_state.league.rules,
    )
    scoring_multipliers = build_future_i1_player_scoring_multipliers(
        raw_forecasts=raw_forecasts,
        league_year_one=league_year_one,
        rules=league_state.league.rules,
    )
    p0 = build_p0_standard_future_materialization(
        league_state=league_state,
        standard_year_one=standard_year_one,
    )

    if set(p0.players) != set(scoring_multipliers):
        missing_scoring = sorted(set(p0.players) - set(scoring_multipliers))
        extra_scoring = sorted(set(scoring_multipliers) - set(p0.players))
        raise ValueError(
            "P0 future Forecast/scoring coverage mismatch; "
            f"missing_scoring={missing_scoring}; extra_scoring={extra_scoring}"
        )

    rows: list[FuturePlayerHorizonForecast] = []
    for player_id in sorted(p0.players):
        player_forecast = p0.players[player_id]
        for year_index in (2, 3):
            result = translate_future_i1_result_for_player(
                player_id,
                player_forecast.result_for(year_index),
                multipliers=scoring_multipliers,
            )
            rows.append(
                FuturePlayerHorizonForecast(
                    player_id=player_id,
                    position=player_forecast.source.position,
                    evaluation_season=P0_SOURCE_SEASON,
                    year_index=year_index,
                    target_season=P0_SOURCE_SEASON + year_index - 1,
                    central_expectation=max(0.0, float(result.anticipated_points)),
                    scoring_coordinate=P0_FUTURE_SCORING_COORDINATE,
                    model_version=result.model_version,
                    source=P0_FUTURE_FORECAST_SOURCE,
                    uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                    scenarios=tuple(
                        FutureForecastScenario(
                            scenario_id=state,
                            probability=max(0.0, float(result.probabilities[state])),
                            fantasy_points=max(0.0, float(result.state_means[state])),
                        )
                        for state in STATE_NAMES
                    ),
                    evidence_path=result.evidence_path,
                )
            )

    provenance: dict[str, bool | float | int | str | None] = {
        "provider_neutral_contract": True,
        "future_forecast_authority": "P0_D0_D1_redevelopment_final_routes_v1",
        "p0_package_sha256": P0_PACKAGE_SHA256,
        "p0_final_route_authority_sha256": P0_FINAL_ROUTE_AUTHORITY_SHA256,
        "p0_final_route_authority_version": P0_FINAL_ROUTE_AUTHORITY_VERSION,
        "p0_current_source_sha256": P0_CURRENT_SOURCE_CSV_SHA256,
        "p0_standard_y1_board_sha256": P0_STANDARD_Y1_BOARD_SHA256,
        "p0_connected_league_y1_control_sha256": P0_CONNECTED_LEAGUE_Y1_BOARD_SHA256,
        "p0_internal_scoring_coordinate": "standard_non_ppr",
        "p0_future_source_season": P0_SOURCE_SEASON,
        "future_i1_scoring_version": FUTURE_I1_PLAYER_SCORING_VERSION,
        "future_i1_scoring_method": "player_specific_year1_league_standard_ratio",
        "future_i1_scoring_player_count": len(scoring_multipliers),
        "future_i1_scoring_multiplier_sha256": _multiplier_digest(scoring_multipliers),
    }
    contract = FutureForecastContract(
        evaluation_season=P0_SOURCE_SEASON,
        scoring_coordinate=P0_FUTURE_SCORING_COORDINATE,
        forecast_model_version=P0_FORECAST_VERSION,
        forecast_source=P0_FUTURE_FORECAST_SOURCE,
        forecasts=tuple(rows),
        provenance=provenance,
    )
    return P0FutureForecastContractMaterialization(
        contract=contract,
        scoring_multipliers=dict(scoring_multipliers),
    )
