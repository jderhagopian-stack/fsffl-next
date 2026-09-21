from __future__ import annotations

import logging
from typing import Callable

from fsffl.forecast.current_runtime import LiveForecastSourceHealthFailure
from fsffl.forecast.preseason_baseline import (
    PRESEASON_BASELINE_MODEL_VERSION,
    baseline_from_runtime,
    build_runtime_from_preseason_baseline,
    preseason_scope_id,
    state_is_preseason_capture_eligible,
)
from fsffl.persistence.contracts import PersistenceStore
from fsffl.persistence.runtime_cache import (
    LEAGUE_SEASON_SCOPE_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    decode_preseason_forecast_baseline,
    preseason_forecast_baseline_artifact,
)
from fsffl.state.models import LeagueState

from .runtime import LiveForecastEvidence, default_live_forecast_loader


_logger = logging.getLogger("fsffl.product.forecast")
ForecastLoader = Callable[[LeagueState], LiveForecastEvidence]


def _evidence_from_baseline(
    league_state: LeagueState,
    *,
    baseline,
    live_failure: Exception | None = None,
) -> LiveForecastEvidence:
    result = build_runtime_from_preseason_baseline(league_state, baseline)
    if isinstance(live_failure, LiveForecastSourceHealthFailure):
        result = result.model_copy(
            update={"source_health_events": live_failure.health_events}
        )
    uncertainty_ready = bool(result.fantasy_point_forecasts) and all(
        observation.distribution.stddev > 0
        for observation in result.fantasy_point_forecasts
    )
    return LiveForecastEvidence(
        raw_forecasts=result.raw_ensemble,
        league_scored_forecasts=(
            result.fantasy_point_forecasts + result.fantasy_regular_season_forecasts
        ),
        successful_source_ids=result.successful_source_ids,
        failed_sources=(
            ()
            if live_failure is None
            else (
                f"live_full_season_refresh: {type(live_failure).__name__}: {live_failure}",
            )
        ),
        uncertainty_ready=uncertainty_ready,
        runtime_result=result,
        evidence_basis="preseason_baseline",
    )


def make_preseason_baseline_authority_loader(
    persistence_store: PersistenceStore | None,
) -> ForecastLoader:
    """Load the immutable preseason coordinate for consumers that require frozen Year 1.

    This loader never calls live providers. The ordinary resilient/live Forecast path
    remains separate so current-season/provider-health evidence can continue to refresh
    without silently replacing the frozen preseason coordinate.
    """

    def load(league_state: LeagueState) -> LiveForecastEvidence:
        if persistence_store is None:
            raise ValueError("preserved preseason Year-1 authority requires persistence")
        scope_id = preseason_scope_id(league_state)
        existing = persistence_store.get_latest_reusable_artifact(
            artifact_kind=PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
            scope_kind=LEAGUE_SEASON_SCOPE_KIND,
            scope_id=scope_id,
            model_version=PRESEASON_BASELINE_MODEL_VERSION,
        )
        if existing is None:
            raise ValueError(
                "valid preserved preseason Year-1 baseline is unavailable for "
                f"{scope_id}"
            )
        baseline = decode_preseason_forecast_baseline(dict(existing.payload))
        evidence = _evidence_from_baseline(
            league_state,
            baseline=baseline,
        )
        if evidence.evidence_basis != "preseason_baseline":
            raise ValueError("preserved Year-1 authority returned an unexpected evidence basis")
        return evidence

    return load


def make_resilient_forecast_loader(
    persistence_store: PersistenceStore | None,
    *,
    live_loader: ForecastLoader = default_live_forecast_loader,
) -> ForecastLoader:
    """Use live full-season evidence when valid and immutable preseason evidence otherwise.

    The fallback never lowers the two-independent-source requirement. It reuses a
    previously validated full-season ensemble captured before games began. Weekly or
    rest-of-season provider output is intentionally not relabeled as season evidence.
    """

    if persistence_store is None:
        return live_loader

    def load(league_state: LeagueState) -> LiveForecastEvidence:
        scope_id = preseason_scope_id(league_state)
        existing = persistence_store.get_latest_reusable_artifact(
            artifact_kind=PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
            scope_kind=LEAGUE_SEASON_SCOPE_KIND,
            scope_id=scope_id,
            model_version=PRESEASON_BASELINE_MODEL_VERSION,
        )

        baseline = (
            decode_preseason_forecast_baseline(dict(existing.payload))
            if existing is not None
            else None
        )

        try:
            if live_loader is default_live_forecast_loader:
                evidence = default_live_forecast_loader(
                    league_state,
                    reference_raw_forecasts=(
                        baseline.raw_ensemble if baseline is not None else None
                    ),
                )
            else:
                evidence = live_loader(league_state)
        except Exception as exc:
            if baseline is None:
                raise
            _logger.warning(
                "FSFFL live full-season forecast unavailable; using immutable preseason baseline league=%s season=%s baseline_as_of=%s sources=%s error=%s",
                league_state.league.league_id,
                league_state.league.season,
                baseline.evaluation_as_of.isoformat(),
                list(baseline.successful_source_ids),
                exc,
            )
            return _evidence_from_baseline(
                league_state,
                baseline=baseline,
                live_failure=exc,
            )

        if existing is None and state_is_preseason_capture_eligible(league_state):
            baseline = baseline_from_runtime(league_state, evidence.runtime_result)
            persistence_store.put_artifact(
                preseason_forecast_baseline_artifact(
                    league_season_scope_id=scope_id,
                    baseline=baseline,
                )
            )
            _logger.info(
                "FSFFL immutable preseason forecast baseline captured league=%s season=%s as_of=%s sources=%s",
                league_state.league.league_id,
                league_state.league.season,
                baseline.evaluation_as_of.isoformat(),
                list(baseline.successful_source_ids),
            )
        return evidence

    return load
