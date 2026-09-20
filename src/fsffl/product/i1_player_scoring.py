from __future__ import annotations

import math
from typing import Mapping

from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueRules, Position

from .i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING


FUTURE_I1_PLAYER_SCORING_VERSION = "i1-future-league-scoring-v2:player-ratio"
_SUPPORTED_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def _season_fantasy_points(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    output: dict[str, ForecastObservation] = {}
    for observation in observations:
        if (
            observation.metric != ForecastMetric.FANTASY_POINTS
            or observation.horizon != ForecastHorizon.SEASON
            or observation.position not in _SUPPORTED_POSITIONS
        ):
            continue
        if observation.player_id in output:
            raise ValueError(
                "player-specific future-I1 scoring received multiple full-season "
                f"fantasy-point observations for {observation.player_id}"
            )
        output[observation.player_id] = observation
    return output


def player_scoring_multipliers(
    *,
    standard_year_one: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
) -> dict[str, float]:
    """Return one deterministic league/standard Year-1 ratio per player.

    This is the promoted future-scoring representation. It preserves the player's
    governed Year-1 scoring mix instead of replacing it with a position-average
    conversion. The ratio is a downstream unit translation only; it does not fit
    or modify I1.
    """

    standard = _season_fantasy_points(standard_year_one)
    league = _season_fantasy_points(league_year_one)
    if not league:
        raise ValueError(
            "player-specific future-I1 scoring requires governed league Year-1 forecasts"
        )

    missing = sorted(set(league) - set(standard))
    if missing:
        raise ValueError(
            "player-specific future-I1 scoring cannot reproduce the frozen standard "
            f"coordinate for required players: {missing}"
        )

    multipliers: dict[str, float] = {}
    for player_id, league_observation in league.items():
        standard_observation = standard[player_id]
        if standard_observation.position != league_observation.position:
            raise ValueError(
                "player-specific future-I1 scoring position mismatch for "
                f"{player_id}: standard={standard_observation.position.value} "
                f"league={league_observation.position.value}"
            )
        denominator = max(0.0, float(standard_observation.distribution.mean))
        numerator = max(0.0, float(league_observation.distribution.mean))
        if denominator <= 0.0:
            if numerator <= 0.0:
                multipliers[player_id] = 1.0
                continue
            raise ValueError(
                "player-specific future-I1 scoring has nonzero league points but "
                f"zero frozen standard points for {player_id}"
            )
        multiplier = numerator / denominator
        if not math.isfinite(multiplier) or multiplier <= 0.0:
            raise ValueError(
                "player-specific future-I1 scoring produced invalid multiplier for "
                f"{player_id}"
            )
        multipliers[player_id] = multiplier
    return multipliers


def derive_future_i1_standard_year_one(
    *,
    raw_forecasts: tuple[ForecastObservation, ...],
    rules: LeagueRules,
) -> tuple[ForecastObservation, ...]:
    """Direct-score the frozen raw stat vector on the governed standard/non-PPR coordinate."""

    standard_rules = rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING})
    return derive_league_fantasy_point_forecasts(
        raw_forecasts,
        rules=standard_rules,
        source="fsffl:p0_frozen_standard_scoring:player_specific",
        model_version=FUTURE_I1_PLAYER_SCORING_VERSION,
    )


def build_future_i1_player_scoring_multipliers(
    *,
    raw_forecasts: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
    rules: LeagueRules,
) -> dict[str, float]:
    """Build player-specific translation from the governed frozen Year-1 stat vector."""

    standard_year_one = derive_future_i1_standard_year_one(
        raw_forecasts=raw_forecasts,
        rules=rules,
    )
    return player_scoring_multipliers(
        standard_year_one=standard_year_one,
        league_year_one=league_year_one,
    )


def translate_future_i1_result(
    result: I1ForecastResult,
    *,
    multiplier: float,
) -> I1ForecastResult:
    """Translate frozen I1 point outputs without changing P0 probabilities or persistence."""

    multiplier = float(multiplier)
    if not math.isfinite(multiplier) or multiplier <= 0.0:
        raise ValueError("player-specific future-I1 scoring multiplier must be finite and positive")

    state_means = {
        state: max(0.0, float(result.state_means[state]) * multiplier)
        for state in STATE_NAMES
    }
    anticipated_points = max(
        0.0,
        sum(
            float(result.probabilities[state]) * state_means[state]
            for state in STATE_NAMES
        ),
    )
    model_version = result.model_version
    if FUTURE_I1_PLAYER_SCORING_VERSION not in model_version:
        model_version = f"{model_version}:{FUTURE_I1_PLAYER_SCORING_VERSION}"
    return I1ForecastResult(
        probabilities=result.probabilities,
        persistence_probability=result.persistence_probability,
        anticipated_points=anticipated_points,
        state_means=state_means,
        evidence_path=result.evidence_path,
        model_version=model_version,
    )


def translate_future_i1_result_for_player(
    player_id: str,
    result: I1ForecastResult,
    *,
    multipliers: Mapping[str, float],
) -> I1ForecastResult:
    """Identity-aware authoritative adapter for a caller that already owns player identity."""

    try:
        multiplier = multipliers[player_id]
    except KeyError as exc:
        raise ValueError(
            "player-specific future-I1 scoring lacks a governed multiplier for "
            f"{player_id}"
        ) from exc
    return translate_future_i1_result(result, multiplier=float(multiplier))
