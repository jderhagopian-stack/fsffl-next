from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.state.models import LeagueState, Player, PlayerState, Position

from .qb_career_state import (
    QB_CAREER_STATE_EVIDENCE_VERSION,
    QB_CAREER_STATE_MODEL_VERSION,
    QBCareerStateEvidence,
    QBCareerStateForecast,
    _evidence_payload,
    _probability,
    forecast_qb_career_state,
    rank_percentiles,
)


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().replace(".", "").replace("'", "").split())


@lru_cache(maxsize=1)
def _name_index() -> dict[str, tuple[tuple[str, dict], ...]]:
    grouped: defaultdict[str, list[tuple[str, dict]]] = defaultdict(list)
    for gsis_id, row in _evidence_payload().get("players", {}).items():
        name = _normalize_name(str(row.get("display_name") or ""))
        if name:
            grouped[name].append((gsis_id, row))
    return {key: tuple(value) for key, value in grouped.items()}


def _name_evidence(
    *,
    player: Player,
    player_state: PlayerState | None,
    evaluation_season: int,
) -> QBCareerStateEvidence | None:
    """Resolve current Sleeper identity when canonical GSIS is not present.

    This compatibility bridge is deterministic and fail-closed: it accepts only one
    exact normalized-name match in the versioned football-evidence artifact. It does
    not use market, team, or future information. Canonical GSIS provider refs remain
    the preferred identity path in ``forecast_qb_career_state``.
    """

    if player_state is None or player_state.age_years is None:
        return None
    payload = _evidence_payload()
    if payload.get("evaluation_season") != evaluation_season:
        return None
    matches = _name_index().get(_normalize_name(player.full_name), ())
    if len(matches) != 1:
        return None
    gsis_id, row = matches[0]
    cutoff = int(payload["feature_cutoff_season"])
    if int(row.get("feature_cutoff_season", -1)) != cutoff:
        return None
    return QBCareerStateEvidence(
        gsis_id=gsis_id,
        evaluation_season=evaluation_season,
        feature_cutoff_season=cutoff,
        experience=float(row["experience"]),
        draft_pick_pct=float(row["draft_pick_pct"]),
        games_pct=float(row["games_pct"]),
        opportunity_pct=float(row["opportunity_pct"]),
        role_mean_2=float(row["role_mean_2"]),
        role_vol_2=float(row["role_vol_2"]),
        established_starter_seasons=float(row["qb_established_starter_seasons"]),
    )


def forecast_qb_career_state_runtime(
    *,
    player: Player,
    player_state: PlayerState | None,
    evaluation_season: int,
    production_percentile: float,
) -> QBCareerStateForecast | None:
    direct = forecast_qb_career_state(
        player=player,
        player_state=player_state,
        evaluation_season=evaluation_season,
        production_percentile=production_percentile,
    )
    if direct is not None:
        return direct
    evidence = _name_evidence(
        player=player,
        player_state=player_state,
        evaluation_season=evaluation_season,
    )
    if evidence is None or player_state is None or player_state.age_years is None:
        return None
    p2 = _probability(
        age=float(player_state.age_years),
        evidence=evidence,
        production_percentile=production_percentile,
        horizon=1,
    )
    p3 = _probability(
        age=float(player_state.age_years),
        evidence=evidence,
        production_percentile=production_percentile,
        horizon=2,
    )
    return QBCareerStateForecast(
        model_version=QB_CAREER_STATE_MODEL_VERSION,
        evidence_version=QB_CAREER_STATE_EVIDENCE_VERSION,
        evaluation_season=evaluation_season,
        feature_cutoff_season=evidence.feature_cutoff_season,
        production_percentile=production_percentile,
        year2_probability=p2,
        year3_probability=p3,
    )


def build_qb_career_state_forecasts(
    league_state: LeagueState,
    *,
    season_forecasts: tuple[ForecastObservation, ...],
) -> dict[str, QBCareerStateForecast]:
    """Publish Forecast-owned Y2/Y3 QB meaningful-starter expectations.

    Only authoritative full-season fantasy-point Forecast observations contribute to
    the live production percentile. Missing, stale, ambiguous, or incomplete player
    evidence is omitted so Intrinsic v1 can fail closed to its conservative prior QB
    treatment rather than fabricating a state probability.
    """

    selected: dict[str, ForecastObservation] = {}
    for observation in season_forecasts:
        if observation.horizon != ForecastHorizon.SEASON:
            continue
        if observation.metric != ForecastMetric.FANTASY_POINTS:
            continue
        prior = selected.get(observation.player_id)
        if prior is None or observation.as_of > prior.as_of:
            selected[observation.player_id] = observation

    player_by_id = {player.player_id: player for player in league_state.players}
    state_by_id = {state.player_id: state for state in league_state.player_states}
    qb_means = {
        player_id: observation.distribution.mean
        for player_id, observation in selected.items()
        if (player := player_by_id.get(player_id)) is not None and player.position == Position.QB
    }
    percentiles = rank_percentiles(qb_means)

    output: dict[str, QBCareerStateForecast] = {}
    for player_id, production_percentile in percentiles.items():
        player = player_by_id[player_id]
        forecast = forecast_qb_career_state_runtime(
            player=player,
            player_state=state_by_id.get(player_id),
            evaluation_season=league_state.league.season,
            production_percentile=production_percentile,
        )
        if forecast is not None:
            output[player_id] = forecast
    return output
