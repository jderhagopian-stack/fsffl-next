from __future__ import annotations

import math
from typing import Mapping, Protocol

from fsffl.forecast.integrated_i1 import I1ForecastInput, I1ForecastResult, STATE_NAMES
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueRules, Position, ScoringRule

FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION = (
    "i1-future-league-scoring-bridge-v1:position-ratio"
)
_SUPPORTED_POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)

# The frozen I1 research coordinate is documented as standard/non-PPR fantasy
# points. This is an explicit unit bridge only; it does not alter I1 features,
# probabilities, regularization, career-state definitions, or fitted artifacts.
FROZEN_I1_STANDARD_SCORING = (
    ScoringRule(stat="pass_yd", points=0.04),
    ScoringRule(stat="pass_td", points=4.0),
    ScoringRule(stat="pass_int", points=-2.0),
    ScoringRule(stat="rush_yd", points=0.1),
    ScoringRule(stat="rush_td", points=6.0),
    ScoringRule(stat="rec_yd", points=0.1),
    ScoringRule(stat="rec_td", points=6.0),
    ScoringRule(stat="fum_lost", points=-2.0),
)


class I1Predictor(Protocol):
    def predict(
        self,
        item: I1ForecastInput,
        *,
        fallback_probabilities: Mapping[str, float] | None = None,
    ) -> I1ForecastResult: ...


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
                "future-I1 scoring bridge received multiple full-season fantasy-point "
                f"observations for {observation.player_id}"
            )
        output[observation.player_id] = observation
    return output


def position_scoring_multipliers(
    *,
    standard_year_one: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
) -> dict[Position, float]:
    """Convert the frozen standard I1 point unit to connected-league point units.

    I1 state means are position/state aggregate quantities, not player stat lines.
    The narrowest coherent bridge is therefore a deterministic position-level ratio
    computed from the same governed current Forecast universe on both scoring
    coordinates. No fitted coefficient, market data, or owner input is used.
    """

    standard = _season_fantasy_points(standard_year_one)
    league = _season_fantasy_points(league_year_one)
    if not league:
        raise ValueError("future-I1 scoring bridge requires governed league Year-1 forecasts")

    missing = sorted(set(league) - set(standard))
    if missing:
        raise ValueError(
            "future-I1 scoring bridge cannot reproduce the frozen standard coordinate "
            f"for required players: {missing}"
        )

    standard_totals = {position: 0.0 for position in _SUPPORTED_POSITIONS}
    league_totals = {position: 0.0 for position in _SUPPORTED_POSITIONS}
    counts = {position: 0 for position in _SUPPORTED_POSITIONS}
    for player_id, league_observation in league.items():
        standard_observation = standard[player_id]
        if standard_observation.position != league_observation.position:
            raise ValueError(
                "future-I1 scoring bridge position mismatch for "
                f"{player_id}: standard={standard_observation.position.value} "
                f"league={league_observation.position.value}"
            )
        position = league_observation.position
        standard_totals[position] += max(
            0.0, float(standard_observation.distribution.mean)
        )
        league_totals[position] += max(
            0.0, float(league_observation.distribution.mean)
        )
        counts[position] += 1

    multipliers: dict[Position, float] = {}
    for position in _SUPPORTED_POSITIONS:
        if counts[position] == 0:
            continue
        denominator = standard_totals[position]
        numerator = league_totals[position]
        if denominator <= 0.0:
            if numerator <= 0.0:
                multipliers[position] = 1.0
                continue
            raise ValueError(
                "future-I1 scoring bridge has nonzero league points but zero frozen "
                f"standard points for {position.value}"
            )
        multiplier = numerator / denominator
        if not math.isfinite(multiplier) or multiplier <= 0.0:
            raise ValueError(
                f"future-I1 scoring bridge produced invalid multiplier for {position.value}"
            )
        multipliers[position] = multiplier
    return multipliers


def build_future_i1_position_scoring_multipliers(
    *,
    raw_forecasts: tuple[ForecastObservation, ...],
    league_year_one: tuple[ForecastObservation, ...],
    rules: LeagueRules,
) -> dict[Position, float]:
    standard_rules = rules.model_copy(update={"scoring": FROZEN_I1_STANDARD_SCORING})
    standard_year_one = derive_league_fantasy_point_forecasts(
        raw_forecasts,
        rules=standard_rules,
        source="fsffl:i1_frozen_standard_scoring",
        model_version=FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION,
    )
    return position_scoring_multipliers(
        standard_year_one=standard_year_one,
        league_year_one=league_year_one,
    )


class LeagueScoringNormalizedI1Predictor:
    """Read a frozen I1 artifact in connected-league fantasy-point units.

    The underlying predictor is called unchanged. Only its output point quantities
    are converted; probabilities, persistence, evidence path, C, and direct horizon
    semantics remain untouched.
    """

    def __init__(
        self,
        predictor: I1Predictor,
        *,
        multipliers: Mapping[Position, float],
    ) -> None:
        self._predictor = predictor
        self._multipliers = dict(multipliers)

    def predict(
        self,
        item: I1ForecastInput,
        *,
        fallback_probabilities: Mapping[str, float] | None = None,
    ) -> I1ForecastResult:
        result = self._predictor.predict(
            item,
            fallback_probabilities=fallback_probabilities,
        )
        try:
            multiplier = float(self._multipliers[item.position])
        except KeyError as exc:
            raise ValueError(
                "future-I1 scoring bridge lacks a governed multiplier for "
                f"{item.position.value}"
            ) from exc
        if not math.isfinite(multiplier) or multiplier <= 0.0:
            raise ValueError(
                f"future-I1 scoring bridge has invalid multiplier for {item.position.value}"
            )

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
        return I1ForecastResult(
            probabilities=result.probabilities,
            persistence_probability=result.persistence_probability,
            anticipated_points=anticipated_points,
            state_means=state_means,
            evidence_path=result.evidence_path,
            model_version=(
                f"{result.model_version}:{FUTURE_I1_LEAGUE_SCORING_BRIDGE_VERSION}"
            ),
        )
