from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import RLock
from typing import Callable

from fsffl.forecast.current_runtime import LiveForecastRuntimeResult, build_current_live_forecasts
from fsffl.forecast.models import ForecastObservation
from fsffl.providers.acquisition import ProviderBackedStateService
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.state.models import LeagueState


LiveStateLoader = Callable[[str], LeagueState]
_logger = logging.getLogger("fsffl.product.forecast")


@dataclass(frozen=True)
class LiveForecastEvidence:
    """Product-runtime handle to authoritative NEXT-2 current forecast output."""

    raw_forecasts: tuple[ForecastObservation, ...]
    league_scored_forecasts: tuple[ForecastObservation, ...]
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    uncertainty_ready: bool
    runtime_result: LiveForecastRuntimeResult
    model_version: str = "next8-live-forecast-evidence-v2"


LiveForecastLoader = Callable[[LeagueState], LiveForecastEvidence]


def default_sleeper_state_loader(league_external_id: str) -> LeagueState:
    """Materialize current canonical state through the governed provider path."""

    service = ProviderBackedStateService(
        source=SleeperLiveSource(),
        normalizer=SleeperSnapshotNormalizer(),
    )
    return service.materialize_live(league_external_id=league_external_id)


def default_live_forecast_loader(league_state: LeagueState) -> LiveForecastEvidence:
    """Run the governed multi-provider NEXT-2 current forecast runtime.

    No single provider output is promoted as an FSFFL forecast. The returned raw
    forecasts are the authoritative equal-weight ensemble after per-player source
    coverage gates. League-scored forecasts are derived only after that ensemble.
    """

    result = build_current_live_forecasts(league_state)
    _logger.info(
        "FSFFL live forecast sources successful=%s failures=%s raw_groups=%s scored_players=%s",
        list(result.successful_source_ids),
        list(result.failed_sources),
        len(result.raw_ensemble),
        len(result.fantasy_point_forecasts),
    )
    uncertainty_ready = bool(result.fantasy_point_forecasts) and all(
        observation.distribution.stddev > 0
        for observation in result.fantasy_point_forecasts
    )
    return LiveForecastEvidence(
        raw_forecasts=result.raw_ensemble,
        league_scored_forecasts=result.fantasy_point_forecasts,
        successful_source_ids=result.successful_source_ids,
        failed_sources=result.failed_sources,
        uncertainty_ready=uncertainty_ready,
        runtime_result=result,
    )


@dataclass(frozen=True)
class UserRuntimeContext:
    user_id: str
    league_state: LeagueState | None = None
    selected_team_id: str | None = None
    forecast_evidence: LiveForecastEvidence | None = None


class PrivateBetaRuntimeStore:
    """Small in-memory runtime store for the single-user/private beta.

    Canonical league state and model evidence live in process memory only. They
    are not written to the repository. A durable multi-user store can replace this
    interface later without changing model or presentation authority.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._contexts: dict[str, UserRuntimeContext] = {}

    def get(self, user_id: str) -> UserRuntimeContext:
        with self._lock:
            return self._contexts.get(user_id, UserRuntimeContext(user_id=user_id))

    def set_league_state(self, user_id: str, league_state: LeagueState) -> UserRuntimeContext:
        if not user_id.strip():
            raise ValueError("user_id cannot be blank")
        with self._lock:
            context = UserRuntimeContext(user_id=user_id, league_state=league_state)
            self._contexts[user_id] = context
            return context

    def set_forecast_evidence(
        self,
        user_id: str,
        evidence: LiveForecastEvidence,
        *,
        refreshed_league_state: LeagueState | None = None,
    ) -> UserRuntimeContext:
        """Attach NEXT-2 evidence, optionally advancing state past evidence cutoff."""

        with self._lock:
            current = self.get(user_id)
            league_state = refreshed_league_state or current.league_state
            if league_state is None:
                raise ValueError("cannot attach forecasts before a league is loaded")
            forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
            if any(item.as_of > league_state.as_of for item in forecasts):
                raise ValueError("forecast evidence cannot postdate canonical league state")
            selected = current.selected_team_id
            valid_team_ids = {team.team_id for team in league_state.teams}
            if selected not in valid_team_ids:
                selected = None
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected,
                forecast_evidence=evidence,
            )
            self._contexts[user_id] = updated
            return updated

    def select_team(self, user_id: str, team_id: str) -> UserRuntimeContext:
        if not team_id.strip():
            raise ValueError("team_id cannot be blank")
        with self._lock:
            current = self.get(user_id)
            if current.league_state is None:
                raise ValueError("cannot select team before a league is loaded")
            valid_team_ids = {team.team_id for team in current.league_state.teams}
            if team_id not in valid_team_ids:
                raise ValueError("selected team does not belong to loaded league")
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=current.league_state,
                selected_team_id=team_id,
                forecast_evidence=current.forecast_evidence,
            )
            self._contexts[user_id] = updated
            return updated

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._contexts.pop(user_id, None)
