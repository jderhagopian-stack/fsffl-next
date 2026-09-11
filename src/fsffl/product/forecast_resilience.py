from __future__ import annotations

import logging
from typing import Callable

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
    live_failure: Exception,
) -> LiveForecastEvidence:
    result = build_runtime_from_preseason_baseline(league_state, baseline)
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
            f"live_full_season_refresh: {type(live_failure).__name__}: {live_failure}",
        ),
        uncertainty_ready=uncertainty_ready,
        runtime_result=result,
    )


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

        try:
            evidence = live_loader(league_state)
        except Exception as exc:
            if existing is None:
                raise
            baseline = decode_preseason_forecast_baseline(dict(existing.payload))
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
