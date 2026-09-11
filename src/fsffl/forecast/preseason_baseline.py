from __future__ import annotations

from datetime import datetime

from fsffl.state.models import FrozenModel, LeagueState

from .current_runtime import LiveForecastRuntimeResult
from .league_scoring import derive_league_fantasy_point_forecasts
from .live_ensemble import LiveEnsembleCoverage
from .models import ForecastHorizon, ForecastObservation
from .regular_season import derive_fantasy_regular_season_forecasts
from .season_uncertainty import apply_empirical_season_fantasy_point_uncertainty


PRESEASON_BASELINE_MODEL_VERSION = "next2-preseason-baseline-v1"
PRESEASON_FALLBACK_RUNTIME_VERSION = "next2-current-runtime-v5:preseason-baseline-fallback"


class PreseasonForecastBaseline(FrozenModel):
    """Immutable point-in-time full-season forecast evidence captured before games begin.

    The baseline stores the authoritative multi-source raw ensemble, not downstream
    Simulation/Value/Decision output. Current league scoring and uncertainty logic are
    re-applied when the baseline is used so Forecast remains the only calculation authority.
    """

    league_id: str
    season: int
    raw_ensemble: tuple[ForecastObservation, ...]
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    evaluation_as_of: datetime
    source_runtime_model_version: str
    model_version: str = PRESEASON_BASELINE_MODEL_VERSION
    source_artifact_id: str | None = None


def preseason_scope_id(league_state: LeagueState) -> str:
    return f"{league_state.league.league_id}:{league_state.league.season}"


def state_is_preseason_capture_eligible(league_state: LeagueState) -> bool:
    """Allow automatic capture only before canonical State contains completed scoring.

    This is deliberately conservative. Once any matchup has recorded a score, the
    league-season baseline must already exist and cannot be created from current pages.
    """

    return not any(
        matchup.team_a_points is not None or matchup.team_b_points is not None
        for matchup in league_state.matchups
    )


def baseline_from_runtime(
    league_state: LeagueState,
    result: LiveForecastRuntimeResult,
    *,
    source_artifact_id: str | None = None,
) -> PreseasonForecastBaseline:
    if len(set(result.successful_source_ids)) < 2:
        raise ValueError("preseason baseline requires at least 2 independent sources")
    if not result.raw_ensemble:
        raise ValueError("preseason baseline requires a non-empty raw ensemble")
    if any(observation.horizon != ForecastHorizon.SEASON for observation in result.raw_ensemble):
        raise ValueError("preseason baseline may contain only full-season forecast observations")
    return PreseasonForecastBaseline(
        league_id=league_state.league.league_id,
        season=league_state.league.season,
        raw_ensemble=result.raw_ensemble,
        coverage=result.coverage,
        successful_source_ids=tuple(sorted(set(result.successful_source_ids))),
        evaluation_as_of=result.evaluation_as_of,
        source_runtime_model_version=result.model_version,
        source_artifact_id=source_artifact_id,
    )


def build_runtime_from_preseason_baseline(
    league_state: LeagueState,
    baseline: PreseasonForecastBaseline,
) -> LiveForecastRuntimeResult:
    if baseline.model_version != PRESEASON_BASELINE_MODEL_VERSION:
        raise ValueError("preseason baseline model version is stale")
    if baseline.league_id != league_state.league.league_id:
        raise ValueError("preseason baseline belongs to a different league")
    if baseline.season != league_state.league.season:
        raise ValueError("preseason baseline belongs to a different season")
    if len(set(baseline.successful_source_ids)) < 2:
        raise ValueError("preseason baseline does not satisfy independent-source authority")

    league_scored = derive_league_fantasy_point_forecasts(
        baseline.raw_ensemble,
        rules=league_state.league.rules,
        source="fsffl:preseason_baseline_league_scored",
        model_version=PRESEASON_FALLBACK_RUNTIME_VERSION,
    )
    fantasy_points = apply_empirical_season_fantasy_point_uncertainty(league_scored)
    fantasy_regular_season = (
        derive_fantasy_regular_season_forecasts(league_state, fantasy_points)
        if league_state.matchups
        else ()
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=baseline.raw_ensemble,
        fantasy_point_forecasts=fantasy_points,
        fantasy_regular_season_forecasts=fantasy_regular_season,
        coverage=baseline.coverage,
        successful_source_ids=baseline.successful_source_ids,
        failed_sources=("live_full_season_sources_unavailable; using immutable preseason baseline",),
        evaluation_as_of=baseline.evaluation_as_of,
        model_version=PRESEASON_FALLBACK_RUNTIME_VERSION,
    )
