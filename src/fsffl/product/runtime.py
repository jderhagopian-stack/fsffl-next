from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Callable

from fsffl.forecast.adapters.razzball import ProjectionCoverageReport, normalize_razzball_snapshot
from fsffl.forecast.league_scoring import (
    ScoringCoverage,
    ScoringCoverageStatus,
    classify_scoring_coverage,
    derive_league_fantasy_point_forecasts,
)
from fsffl.forecast.models import ForecastObservation
from fsffl.providers.acquisition import ProviderBackedStateService
from fsffl.providers.razzball_live import RazzballLiveProjectionSource
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.state.models import LeagueState


LiveStateLoader = Callable[[str], LeagueState]


@dataclass(frozen=True)
class LiveForecastEvidence:
    raw_forecasts: tuple[ForecastObservation, ...]
    league_scored_forecasts: tuple[ForecastObservation, ...]
    provider_coverage: ProjectionCoverageReport
    scoring_coverage: ScoringCoverage
    uncertainty_ready: bool
    model_version: str = "next8-live-forecast-evidence-v1"


LiveForecastLoader = Callable[[LeagueState], LiveForecastEvidence]


def default_sleeper_state_loader(league_external_id: str) -> LeagueState:
    """Materialize current canonical state through the governed provider path."""

    service = ProviderBackedStateService(
        source=SleeperLiveSource(),
        normalizer=SleeperSnapshotNormalizer(),
    )
    return service.materialize_live(league_external_id=league_external_id)


def default_live_forecast_loader(league_state: LeagueState) -> LiveForecastEvidence:
    """Acquire and normalize current beta projection evidence for a loaded league.

    Razzball is a replaceable private-beta/personal-research provider. Its raw
    provider fantasy-point columns are not used. Raw stats are resolved against
    canonical player identities and scored from canonical league rules.
    """

    snapshot = RazzballLiveProjectionSource().fetch_latest()
    period_end = datetime(league_state.league.season + 1, 2, 15, tzinfo=UTC)
    raw_forecasts, provider_coverage = normalize_razzball_snapshot(
        snapshot,
        league_state=league_state,
        period_end=period_end,
    )
    scoring_coverage = classify_scoring_coverage(league_state.league.rules)
    scored: tuple[ForecastObservation, ...] = ()
    if scoring_coverage.status == ScoringCoverageStatus.COMPLETE:
        scored = derive_league_fantasy_point_forecasts(
            raw_forecasts,
            rules=league_state.league.rules,
        )

    # Current live provider rows are point estimates. A single provider therefore
    # does not yet establish simulation-grade marginal uncertainty. NEXT-4 remains
    # blocked until calibrated uncertainty or independent provider disagreement is
    # attached; projected means can still be displayed transparently.
    uncertainty_ready = bool(scored) and all(
        observation.distribution.stddev > 0 for observation in scored
    )
    return LiveForecastEvidence(
        raw_forecasts=raw_forecasts,
        league_scored_forecasts=scored,
        provider_coverage=provider_coverage,
        scoring_coverage=scoring_coverage,
        uncertainty_ready=uncertainty_ready,
    )


@dataclass(frozen=True)
class UserRuntimeContext:
    user_id: str
    league_state: LeagueState | None = None
    selected_team_id: str | None = None
    forecast_evidence: LiveForecastEvidence | None = None


class PrivateBetaRuntimeStore:
    """Small in-memory runtime store for the single-user/private beta.

    Canonical league state and projection evidence live in process memory only.
    They are not written to the repository. A durable multi-user store can replace
    this interface later.
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
    ) -> UserRuntimeContext:
        with self._lock:
            current = self.get(user_id)
            if current.league_state is None:
                raise ValueError("cannot attach forecasts before a league is loaded")
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=current.league_state,
                selected_team_id=current.selected_team_id,
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
