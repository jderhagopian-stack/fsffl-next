from __future__ import annotations

import hashlib
import json
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
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult, build_current_market_values

from .simulation_runtime import LiveSimulationAnalyticsResult


LiveStateLoader = Callable[[str], LeagueState]
_logger = logging.getLogger("fsffl.product.forecast")


def league_material_fingerprint(league_state: LeagueState) -> str:
    """Hash substantive league facts while ignoring snapshot/provenance timestamps.

    `LeagueState.state_id` intentionally changes whenever the canonical snapshot
    changes, including a fresh retrieval timestamp. That is correct for evidence
    provenance, but too strict for product cache reuse. This fingerprint is a
    performance-only compatibility key: any roster, rules, ownership, player
    status, matchup result, or NFL bye change invalidates it. Retrieval/effective
    timestamps and provenance metadata do not.
    """

    payload = {
        "schema_version": league_state.schema_version,
        "league": league_state.league.model_dump(mode="json"),
        "teams": [
            team.model_dump(mode="json")
            for team in sorted(league_state.teams, key=lambda item: item.team_id)
        ],
        "team_states": [
            state.model_dump(mode="json")
            for state in sorted(league_state.team_states, key=lambda item: item.team_id)
        ],
        "players": [
            player.model_dump(mode="json")
            for player in sorted(league_state.players, key=lambda item: item.player_id)
        ],
        "player_states": [
            {
                "player_id": state.player_id,
                "age_years": state.age_years,
                "nfl_team": state.nfl_team,
                "status": state.status.value,
            }
            for state in sorted(league_state.player_states, key=lambda item: item.player_id)
        ],
        "draft_picks": [
            pick.model_dump(mode="json")
            for pick in sorted(league_state.draft_picks, key=lambda item: item.pick_id)
        ],
        "pick_ownership": [
            ownership.model_dump(mode="json")
            for ownership in sorted(league_state.pick_ownership, key=lambda item: item.pick_id)
        ],
        "matchups": [
            {
                "week": matchup.week,
                "team_a_id": matchup.team_a_id,
                "team_b_id": matchup.team_b_id,
                "team_a_points": matchup.team_a_points,
                "team_b_points": matchup.team_b_points,
            }
            for matchup in sorted(
                league_state.matchups,
                key=lambda item: (item.week, item.team_a_id, item.team_b_id),
            )
        ],
        "nfl_team_byes": [
            {"season": bye.season, "nfl_team": bye.nfl_team, "week": bye.week}
            for bye in sorted(
                league_state.nfl_team_byes,
                key=lambda item: (item.season, item.nfl_team),
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def forecast_input_fingerprint(league_state: LeagueState) -> str:
    """Hash only canonical State inputs consumed by the current forecast runtime.

    Forecast acquisition/normalization depends on the season and canonical player
    identity/team mapping. League scoring and scoring-domain coverage depend on both
    scoring rules and active lineup requirements; the derived fantasy-regular-season
    horizon additionally depends on configured/scheduled fantasy weeks and NFL bye
    state. Roster ownership, draft-pick ownership, team labels, FAAB, matchup scores,
    age and player availability status are intentionally not forecast inputs; those
    facts remain free to invalidate Simulation, Value and downstream Decision outputs
    through the broader material fingerprint.
    """

    rules = league_state.league.rules
    payload = {
        "schema_version": league_state.schema_version,
        "season": league_state.league.season,
        "lineup": [
            requirement.model_dump(mode="json")
            for requirement in sorted(rules.lineup, key=lambda item: (item.slot.value, item.count))
        ],
        "scoring": [
            rule.model_dump(mode="json")
            for rule in sorted(rules.scoring, key=lambda item: (item.stat, item.points))
        ],
        "fantasy_regular_season_end_week": rules.fantasy_regular_season_end_week,
        "matchup_weeks": sorted({matchup.week for matchup in league_state.matchups}),
        "players": [
            {
                "player_id": player.player_id,
                "full_name": player.full_name,
                "position": player.position.value,
                "nfl_team": player.nfl_team,
            }
            for player in sorted(league_state.players, key=lambda item: item.player_id)
        ],
        "nfl_team_byes": [
            {"season": bye.season, "nfl_team": bye.nfl_team, "week": bye.week}
            for bye in sorted(
                league_state.nfl_team_byes,
                key=lambda item: (item.season, item.nfl_team),
            )
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LiveForecastEvidence:
    """Product-runtime handle to authoritative NEXT-2 current forecast output."""

    raw_forecasts: tuple[ForecastObservation, ...]
    league_scored_forecasts: tuple[ForecastObservation, ...]
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    uncertainty_ready: bool
    runtime_result: LiveForecastRuntimeResult
    evidence_basis: str = "live_full_season"
    model_version: str = "next8-live-forecast-evidence-v3"


LiveForecastLoader = Callable[[LeagueState], LiveForecastEvidence]
LiveValueLoader = Callable[[LeagueState], CurrentMarketValueRuntimeResult]


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
    coverage gates. League-scored forecasts include the preserved full NFL-season
    horizon plus the derived league-specific fantasy regular-season horizon.
    """

    result = build_current_live_forecasts(league_state)
    _logger.info(
        "FSFFL live forecast sources successful=%s failures=%s raw_groups=%s scored_players=%s regular_season_players=%s",
        list(result.successful_source_ids),
        list(result.failed_sources),
        len(result.raw_ensemble),
        len(result.fantasy_point_forecasts),
        len(result.fantasy_regular_season_forecasts),
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
        failed_sources=result.failed_sources,
        uncertainty_ready=uncertainty_ready,
        runtime_result=result,
        evidence_basis="live_full_season",
    )


def default_live_value_loader(league_state: LeagueState) -> CurrentMarketValueRuntimeResult:
    """Run the governed NEXT-3 current market-value runtime."""

    return build_current_market_values(league_state)


@dataclass(frozen=True)
class UserRuntimeContext:
    user_id: str
    league_state: LeagueState | None = None
    selected_team_id: str | None = None
    forecast_evidence: LiveForecastEvidence | None = None
    simulation_analytics: LiveSimulationAnalyticsResult | None = None
    value_evidence: CurrentMarketValueRuntimeResult | None = None
    intelligence_reused: bool = False


@dataclass(frozen=True)
class _PendingIntelligenceSnapshot:
    league_state: LeagueState
    forecast_evidence: LiveForecastEvidence
    simulation_analytics: LiveSimulationAnalyticsResult | None = None


class PrivateBetaRuntimeStore:
    """Small in-memory runtime store for the single-user/private beta.

    Canonical league state and model evidence live in process memory only. They
    are not written to the repository. A durable multi-user store can replace this
    interface later without changing model or presentation authority.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._contexts: dict[str, UserRuntimeContext] = {}
        self._pending_intelligence: dict[str, _PendingIntelligenceSnapshot] = {}

    def get(self, user_id: str) -> UserRuntimeContext:
        with self._lock:
            return self._contexts.get(user_id, UserRuntimeContext(user_id=user_id))

    def set_league_state(self, user_id: str, league_state: LeagueState) -> None:
        with self._lock:
            current = self.get(user_id)
            same_material_state = (
                current.league_state is not None
                and league_material_fingerprint(current.league_state)
                == league_material_fingerprint(league_state)
            )
            self._contexts[user_id] = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=(
                    current.selected_team_id
                    if current.selected_team_id in {team.team_id for team in league_state.teams}
                    else None
                ),
                forecast_evidence=current.forecast_evidence if same_material_state else None,
                simulation_analytics=current.simulation_analytics if same_material_state else None,
                value_evidence=current.value_evidence if same_material_state else None,
                intelligence_reused=same_material_state and current.forecast_evidence is not None,
            )
            if not same_material_state:
                self._pending_intelligence.pop(user_id, None)

    def select_team(self, user_id: str, team_id: str) -> None:
        with self._lock:
            current = self.get(user_id)
            if current.league_state is None:
                raise ValueError("load a league before selecting a team")
            if team_id not in {team.team_id for team in current.league_state.teams}:
                raise ValueError("selected team is not part of the loaded league")
            self._contexts[user_id] = UserRuntimeContext(
                user_id=current.user_id,
                league_state=current.league_state,
                selected_team_id=team_id,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=current.simulation_analytics,
                value_evidence=current.value_evidence,
                intelligence_reused=current.intelligence_reused,
            )

    def set_forecast_evidence(
        self,
        user_id: str,
        evidence: LiveForecastEvidence,
        *,
        refreshed_league_state: LeagueState | None = None,
    ) -> None:
        with self._lock:
            current = self.get(user_id)
            league_state = refreshed_league_state or current.league_state
            if league_state is None:
                raise ValueError("load a league before attaching forecast evidence")
            self._contexts[user_id] = UserRuntimeContext(
                user_id=current.user_id,
                league_state=league_state,
                selected_team_id=current.selected_team_id,
                forecast_evidence=evidence,
                simulation_analytics=None,
                value_evidence=current.value_evidence,
                intelligence_reused=False,
            )
            self._pending_intelligence[user_id] = _PendingIntelligenceSnapshot(
                league_state=league_state,
                forecast_evidence=evidence,
            )

    def set_simulation_analytics(self, user_id: str, simulation: LiveSimulationAnalyticsResult) -> None:
        with self._lock:
            current = self.get(user_id)
            self._contexts[user_id] = UserRuntimeContext(
                user_id=current.user_id,
                league_state=current.league_state,
                selected_team_id=current.selected_team_id,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=simulation,
                value_evidence=current.value_evidence,
                intelligence_reused=current.intelligence_reused,
            )
            pending = self._pending_intelligence.get(user_id)
            if pending is not None:
                self._pending_intelligence[user_id] = _PendingIntelligenceSnapshot(
                    league_state=pending.league_state,
                    forecast_evidence=pending.forecast_evidence,
                    simulation_analytics=simulation,
                )

    def set_value_evidence(self, user_id: str, values: CurrentMarketValueRuntimeResult) -> None:
        with self._lock:
            current = self.get(user_id)
            self._contexts[user_id] = UserRuntimeContext(
                user_id=current.user_id,
                league_state=current.league_state,
                selected_team_id=current.selected_team_id,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=current.simulation_analytics,
                value_evidence=values,
                intelligence_reused=current.intelligence_reused,
            )
            pending = self._pending_intelligence.pop(user_id, None)
            if pending is not None:
                self._persist_completed_intelligence_snapshot(user_id, pending, values)

    def _persist_completed_intelligence_snapshot(self, user_id: str, pending: _PendingIntelligenceSnapshot, values: CurrentMarketValueRuntimeResult) -> None:
        return None
