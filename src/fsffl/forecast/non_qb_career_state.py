from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from fsffl.forecast.career import CareerTransitionEvidence, MultiYearForecastPoint, build_multi_year_forecast
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Position


NON_QB_CAREER_MODEL_VERSION = "non-qb-career-age-band-v1"
NON_QB_CAREER_EVIDENCE_THROUGH_SEASON = 2022


@dataclass(frozen=True)
class _TransitionCell:
    sample_size: int
    survival_probability: float
    conditional_multiplier: float
    conditional_multiplier_stddev: float


# Forecast-owned football transition evidence. These age-band summaries are a
# bounded production materialization of the point-in-time career-transition
# evidence validated in PR #131. They are intentionally independent of dynasty
# market price, roster fit, replacement level, and owner behavior.
_TRANSITION_CELLS: dict[tuple[Position, str], _TransitionCell] = {
    (Position.RB, "<=23"): _TransitionCell(373, 0.758878, 1.005261, 0.529426),
    (Position.RB, "24-26"): _TransitionCell(1818, 0.759378, 1.060324, 0.532199),
    (Position.RB, "27-29"): _TransitionCell(1358, 0.760239, 0.850089, 0.524681),
    (Position.RB, "30-32"): _TransitionCell(532, 0.758617, 0.827984, 0.522974),
    (Position.RB, "33+"): _TransitionCell(161, 0.762262, 0.826446, 0.523018),
    (Position.WR, "<=23"): _TransitionCell(449, 0.764392, 1.038043, 0.506705),
    (Position.WR, "24-26"): _TransitionCell(2097, 0.766690, 0.889113, 0.505333),
    (Position.WR, "27-29"): _TransitionCell(1502, 0.767246, 0.840720, 0.504052),
    (Position.WR, "30-32"): _TransitionCell(645, 0.767616, 0.840778, 0.503831),
    (Position.WR, "33+"): _TransitionCell(335, 0.769146, 0.837775, 0.503282),
    (Position.TE, "<=23"): _TransitionCell(142, 0.769305, 1.237942, 0.531908),
    (Position.TE, "24-26"): _TransitionCell(1082, 0.770193, 0.959695, 0.529650),
    (Position.TE, "27-29"): _TransitionCell(934, 0.769912, 0.913367, 0.526298),
    (Position.TE, "30-32"): _TransitionCell(466, 0.769075, 0.803435, 0.525177),
    (Position.TE, "33+"): _TransitionCell(190, 0.768939, 0.848586, 0.525945),
}


def _age_band(age: float) -> str:
    if age <= 23:
        return "<=23"
    if age <= 26:
        return "24-26"
    if age <= 29:
        return "27-29"
    if age <= 32:
        return "30-32"
    return "33+"


def _transition(position: Position, age: float) -> CareerTransitionEvidence:
    band = _age_band(age)
    cell = _TRANSITION_CELLS[(position, band)]
    survivors = max(1, round(cell.sample_size * cell.survival_probability))
    multiplier_se = cell.conditional_multiplier_stddev / sqrt(survivors)
    survival_se = sqrt(
        cell.survival_probability * (1.0 - cell.survival_probability) / cell.sample_size
    )
    return CareerTransitionEvidence(
        position=position,
        horizon=ForecastHorizon.SEASON,
        cohort_name=f"{position.value}:age:{band}",
        age_years=age,
        sample_size=cell.sample_size,
        survivor_sample_size=survivors,
        conditional_production_multiplier=cell.conditional_multiplier,
        survival_probability=cell.survival_probability,
        conditional_multiplier_stddev=cell.conditional_multiplier_stddev,
        conditional_multiplier_standard_error=multiplier_se,
        survival_standard_error=survival_se,
        model_version=NON_QB_CAREER_MODEL_VERSION,
        evidence_through_season=NON_QB_CAREER_EVIDENCE_THROUGH_SEASON,
    )


def _season_forecasts(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    selected: dict[str, ForecastObservation] = {}
    for observation in observations:
        if observation.horizon != ForecastHorizon.SEASON or observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        prior = selected.get(observation.player_id)
        if prior is None or observation.as_of > prior.as_of:
            selected[observation.player_id] = observation
    return selected


def build_non_qb_bounded_paths(
    league_state: LeagueState,
    *,
    season_forecasts: tuple[ForecastObservation, ...],
) -> dict[str, tuple[MultiYearForecastPoint, ...]]:
    """Materialize the governed non-QB Year-2/Year-3 football path.

    Forecast owns age, survival, transition dispersion, and trajectory. Value may
    consume this output but must not recreate or reweight those football effects.
    Players lacking a current age fail closed to the existing Forecast fallback.
    """

    by_player = _season_forecasts(season_forecasts)
    players = {player.player_id: player for player in league_state.players}
    states = {state.player_id: state for state in league_state.player_states}
    output: dict[str, tuple[MultiYearForecastPoint, ...]] = {}
    for player_id, observation in by_player.items():
        player = players.get(player_id)
        state = states.get(player_id)
        if player is None or state is None or state.age_years is None:
            continue
        if player.position not in {Position.RB, Position.WR, Position.TE}:
            continue
        if observation.as_of > league_state.as_of:
            raise ValueError("career-transition Forecast evidence cannot postdate canonical league state")
        transitions = (
            _transition(player.position, state.age_years),
            _transition(player.position, state.age_years + 1.0),
        )
        output[player_id] = build_multi_year_forecast(observation.distribution, transitions)
    return output
