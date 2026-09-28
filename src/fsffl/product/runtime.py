from __future__ import annotations

import hashlib
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass, replace
from threading import RLock, local
from typing import Callable

from fsffl.forecast.current_runtime import (
    LiveForecastRuntimeResult,
    build_current_live_forecasts,
    replay_governed_raw_ensemble_for_state,
)
from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
)
from fsffl.forecast.models import ForecastObservation
from fsffl.forecast.supplemental_coordinate import league_consumes_fumbles_lost
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
        "completed_through_week": league_state.completed_through_week,
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


def raw_forecast_input_fingerprint(league_state: LeagueState) -> str:
    """Hash only inputs that can invalidate governed raw provider Forecast truth.

    Provider acquisition/normalization is league-agnostic. It depends on season and
    canonical player identity/team mapping, not fantasy scoring, lineup structure,
    fantasy matchup weeks, roster ownership, or downstream NFL-bye/scoring
    derivations. Those downstream inputs must trigger re-scoring/rebinding rather
    than provider reacquisition.
    """

    payload = {
        "schema_version": league_state.schema_version,
        "season": league_state.league.season,
        "players": [
            {
                "player_id": player.player_id,
                "full_name": player.full_name,
                "position": player.position.value,
                "nfl_team": player.nfl_team,
            }
            for player in sorted(league_state.players, key=lambda item: item.player_id)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def raw_forecast_compatibility_reasons(
    prior_state: LeagueState,
    target_state: LeagueState,
) -> tuple[str, ...]:
    """Return exact raw-evidence incompatibilities; empty means replay-compatible."""

    reasons: list[str] = []
    if prior_state.schema_version != target_state.schema_version:
        reasons.append("canonical_schema_version_changed")
    if prior_state.league.season != target_state.league.season:
        reasons.append("nfl_season_changed")

    def player_identity(state: LeagueState) -> tuple[tuple[str, str, str, str | None], ...]:
        return tuple(
            (
                player.player_id,
                player.full_name,
                player.position.value,
                player.nfl_team,
            )
            for player in sorted(state.players, key=lambda item: item.player_id)
        )

    if player_identity(prior_state) != player_identity(target_state):
        reasons.append("canonical_player_identity_or_nfl_team_mapping_changed")
    return tuple(reasons)


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
    model_version: str = "next8-live-forecast-evidence-v6:partial-replay-contract"


LiveForecastLoader = Callable[[LeagueState], LiveForecastEvidence]
LiveValueLoader = Callable[[LeagueState], CurrentMarketValueRuntimeResult]


def default_sleeper_state_loader(league_external_id: str) -> LeagueState:
    """Materialize current canonical state through the governed provider path."""

    service = ProviderBackedStateService(
        source=SleeperLiveSource(),
        normalizer=SleeperSnapshotNormalizer(),
    )
    return service.materialize_live(league_external_id=league_external_id)


def default_live_forecast_loader(
    league_state: LeagueState,
    *,
    reference_raw_forecasts: tuple[ForecastObservation, ...] | None = None,
) -> LiveForecastEvidence:
    """Run the governed multi-provider NEXT-2 current forecast runtime.

    No single provider output is promoted as an FSFFL forecast. The returned raw
    forecasts are the authoritative equal-weight ensemble after per-player source
    coverage gates. League-scored forecasts include the preserved full NFL-season
    horizon plus the derived league-specific fantasy regular-season horizon.
    """

    result = build_current_live_forecasts(
        league_state,
        reference_raw_forecasts=reference_raw_forecasts,
    )
    _logger.info(
        "FSFFL live forecast sources successful=%s failures=%s raw_groups=%s scored_players=%s partial_players=%s regular_season_players=%s simulation_blockers=%s fumbles_lost_players=%s fumbles_lost_failure=%s",
        list(result.successful_source_ids),
        list(result.failed_sources),
        len(result.raw_ensemble),
        len(result.fantasy_point_forecasts),
        len(result.partial_fantasy_point_forecasts),
        len(result.fantasy_regular_season_forecasts),
        list(result.simulation_authority_blockers),
        result.fumbles_lost_supplement_player_count,
        result.fumbles_lost_supplement_failure,
    )
    uncertainty_ready = (
        bool(result.fantasy_point_forecasts)
        and not result.simulation_authority_blockers
        and all(
            observation.distribution.stddev > 0
            for observation in result.fantasy_point_forecasts
        )
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


def replay_live_forecast_evidence_for_state(
    league_state: LeagueState,
    evidence: LiveForecastEvidence,
) -> LiveForecastEvidence:
    """Re-score preserved governed raw evidence for a compatible exact State."""

    result = replay_governed_raw_ensemble_for_state(
        league_state,
        evidence.runtime_result,
    )
    uncertainty_ready = (
        bool(result.fantasy_point_forecasts)
        and not result.simulation_authority_blockers
        and all(
            observation.distribution.stddev > 0
            for observation in result.fantasy_point_forecasts
        )
    )
    return LiveForecastEvidence(
        raw_forecasts=result.raw_ensemble,
        league_scored_forecasts=(
            result.fantasy_point_forecasts
            + result.fantasy_regular_season_forecasts
        ),
        successful_source_ids=result.successful_source_ids,
        failed_sources=result.failed_sources,
        uncertainty_ready=uncertainty_ready,
        runtime_result=result,
        evidence_basis=evidence.evidence_basis,
    )


def default_live_value_loader(league_state: LeagueState) -> CurrentMarketValueRuntimeResult:
    """Run the governed NEXT-3 current market-value runtime."""

    return build_current_market_values(league_state)


@dataclass(frozen=True)
class ServedIntelligenceSnapshot:
    """Lightweight identity for a durable same-league last-good bundle.

    Heavy Forecast/Simulation/Value objects remain in persistence and are not
    duplicated in RAM merely to preserve presentation continuity.
    """

    league_id: str
    league_state_id: str
    as_of: datetime
    team_ids: tuple[str, ...]
    publication_generation_id: str | None = None


@dataclass(frozen=True)
class UserRuntimeContext:
    user_id: str
    league_state: LeagueState | None = None
    selected_team_id: str | None = None
    forecast_evidence: LiveForecastEvidence | None = None
    simulation_analytics: LiveSimulationAnalyticsResult | None = None
    value_evidence: CurrentMarketValueRuntimeResult | None = None
    served_intelligence: ServedIntelligenceSnapshot | None = None
    publication_generation_id: str | None = None
    intelligence_reused: bool = False


@dataclass(frozen=True)
class _PendingIntelligenceSnapshot:
    """Minimal in-memory reconciliation identity; heavy data lives on current context."""

    league_state_id: str


@dataclass(frozen=True)
class _WorkingPublicationGuard:
    """Published identity that a working generation is allowed to replace."""

    league_generation: int
    league_id: str
    league_state_id: str
    selected_team_id: str | None
    publication_generation_id: str | None


def _forecast_supplement_compatible(
    league_state: LeagueState,
    evidence: LiveForecastEvidence | None,
) -> bool:
    if evidence is None:
        return False
    if not league_consumes_fumbles_lost(league_state.league.rules):
        return True
    runtime = evidence.runtime_result
    return (
        bool(
            getattr(
                runtime,
                "fumbles_lost_supplement_authority_fingerprint",
                None,
            )
        )
        and (
            getattr(
                runtime,
                "fumbles_lost_supplement_model_version",
                None,
            )
            == FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
        )
        and (
            getattr(
                runtime,
                "fumbles_lost_supplement_league_state_id",
                None,
            )
            == league_state.state_id
        )
    )


def _complete_intelligence(context: UserRuntimeContext) -> bool:
    return (
        context.league_state is not None
        and context.forecast_evidence is not None
        and context.simulation_analytics is not None
        and context.value_evidence is not None
    )


def _terminal_intelligence(
    forecast_evidence: LiveForecastEvidence | None,
    simulation_analytics: LiveSimulationAnalyticsResult | None,
    value_evidence: CurrentMarketValueRuntimeResult | None,
) -> bool:
    """Whether current governed layers have reached a stable terminal capability state."""

    return bool(
        forecast_evidence is not None
        and value_evidence is not None
        and (
            simulation_analytics is not None
            or not forecast_evidence.uncertainty_ready
        )
    )


def _served_snapshot_from_context(
    context: UserRuntimeContext,
) -> ServedIntelligenceSnapshot | None:
    if (
        context.league_state is None
        or not _terminal_intelligence(
            context.forecast_evidence,
            context.simulation_analytics,
            context.value_evidence,
        )
    ):
        return None
    return ServedIntelligenceSnapshot(
        league_id=context.league_state.league.league_id,
        league_state_id=context.league_state.state_id,
        as_of=context.league_state.as_of,
        team_ids=tuple(sorted(team.team_id for team in context.league_state.teams)),
        publication_generation_id=context.publication_generation_id,
    )


class PrivateBetaRuntimeStore:
    """Small in-memory runtime store for the single-user/private beta.

    Canonical league state and model evidence live in process memory only. They
    are not written to the repository. A durable multi-user store can replace this
    interface later without changing model or presentation authority.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        # Serialize identity-changing league/team actions with the entire final
        # publication sequence without blocking ordinary foreground reads.
        self._publication_lock = RLock()
        self._contexts: dict[str, UserRuntimeContext] = {}
        self._working_contexts: dict[str, UserRuntimeContext] = {}
        self._working_publication_guards: dict[str, _WorkingPublicationGuard] = {}
        self._pending_intelligence: dict[str, _PendingIntelligenceSnapshot] = {}
        self._league_generations: dict[str, int] = {}
        self._read_local = local()

    def _published_context(self, user_id: str) -> UserRuntimeContext:
        return self._contexts.get(user_id, UserRuntimeContext(user_id=user_id))

    def get(self, user_id: str) -> UserRuntimeContext:
        """Return only the published generation to ordinary readers.

        Presentation promotion may install a thread-local read override so its own
        builders can compose the unpublished replacement generation without exposing
        that generation to concurrent foreground requests.
        """

        overrides = getattr(self._read_local, "contexts", None)
        if overrides is not None and user_id in overrides:
            return overrides[user_id]
        with self._lock:
            return self._published_context(user_id)

    @contextmanager
    def publication_sequence(self, user_id: str):
        """Serialize the complete final publication path against identity changes."""

        if not user_id.strip():
            raise ValueError("user_id cannot be blank")
        with self._publication_lock:
            yield

    def working_context(self, user_id: str) -> UserRuntimeContext:
        with self._lock:
            return self._working_contexts.get(user_id, self._published_context(user_id))

    def working_generation_active(self, user_id: str) -> bool:
        with self._lock:
            return user_id in self._working_contexts

    def working_target_state_id(self, user_id: str) -> str | None:
        with self._lock:
            working = self._working_contexts.get(user_id)
            return (
                working.league_state.state_id
                if working is not None and working.league_state is not None
                else None
            )

    def _mutation_context(self, user_id: str) -> UserRuntimeContext:
        return self._working_contexts.get(user_id, self._published_context(user_id))

    def _store_mutation_context(
        self,
        user_id: str,
        context: UserRuntimeContext,
    ) -> UserRuntimeContext:
        if user_id in self._working_contexts:
            self._working_contexts[user_id] = context
        else:
            self._contexts[user_id] = context
        return context

    def begin_working_generation(
        self,
        user_id: str,
        *,
        league_state: LeagueState | None = None,
    ) -> UserRuntimeContext:
        """Stage reconciliation from the published generation without mutating it."""

        if not user_id.strip():
            raise ValueError("user_id cannot be blank")
        with self._lock:
            published = self._published_context(user_id)
            target = league_state or published.league_state
            if target is None:
                raise ValueError("cannot begin intelligence reconciliation before a league is loaded")
            if (
                published.league_state is not None
                and published.league_state.league.league_id != target.league.league_id
            ):
                raise ValueError("working generation must belong to the published league")

            valid_team_ids = {team.team_id for team in target.teams}
            selected = (
                published.selected_team_id
                if published.selected_team_id in valid_team_ids
                else None
            )
            same_state = bool(
                published.league_state is not None
                and published.league_state.state_id == target.state_id
            )
            forecast = published.forecast_evidence
            forecast_reusable = same_state
            if (
                not same_state
                and published.league_state is not None
                and forecast is not None
            ):
                forecast_reusable = bool(
                    not any(
                        item.as_of > target.as_of
                        for item in (
                            forecast.raw_forecasts + forecast.league_scored_forecasts
                        )
                    )
                    and _forecast_supplement_compatible(target, forecast)
                    and forecast_input_fingerprint(published.league_state)
                    == forecast_input_fingerprint(target)
                )

            working = UserRuntimeContext(
                user_id=user_id,
                league_state=target,
                selected_team_id=selected,
                forecast_evidence=forecast if forecast_reusable else None,
                simulation_analytics=(
                    published.simulation_analytics if same_state else None
                ),
                value_evidence=published.value_evidence if same_state else None,
                served_intelligence=published.served_intelligence,
                publication_generation_id=None,
                intelligence_reused=same_state,
            )
            self._working_contexts[user_id] = working
            self._working_publication_guards[user_id] = _WorkingPublicationGuard(
                league_generation=self._league_generations.get(user_id, 0),
                league_id=published.league_state.league.league_id,
                league_state_id=published.league_state.state_id,
                selected_team_id=published.selected_team_id,
                publication_generation_id=published.publication_generation_id,
            )
            self._pending_intelligence[user_id] = _PendingIntelligenceSnapshot(
                league_state_id=target.state_id,
            )
            return working

    def abort_working_generation(self, user_id: str) -> UserRuntimeContext:
        """Discard unpublished work and leave the published generation untouched."""

        with self._lock:
            self._working_contexts.pop(user_id, None)
            self._working_publication_guards.pop(user_id, None)
            self._pending_intelligence.pop(user_id, None)
            return self._published_context(user_id)

    @contextmanager
    def read_context(self, user_id: str, context: UserRuntimeContext):
        """Pin reads on this thread to one explicit unpublished generation."""

        prior = getattr(self._read_local, "contexts", None)
        scoped = dict(prior or {})
        scoped[user_id] = context
        self._read_local.contexts = scoped
        try:
            yield context
        finally:
            if prior is None:
                try:
                    del self._read_local.contexts
                except AttributeError:
                    pass
            else:
                self._read_local.contexts = prior

    def publish_working_generation(
        self,
        user_id: str,
        *,
        publication_generation_id: str,
        durable_commit: Callable[[UserRuntimeContext], None] | None = None,
    ) -> UserRuntimeContext:
        """Commit and swap one working generation under a single identity lock.

        The optional durable commit executes only after the exact published
        league/team/generation identity that seeded the working generation has been
        revalidated, and while the same runtime lock remains held. Team selection,
        league activation and other publication identity changes therefore either
        happen before this critical section (causing publication to abort) or after
        the durable commit and in-memory swap have completed.
        """

        generation_id = str(publication_generation_id or "").strip()
        if not generation_id:
            raise ValueError("publication_generation_id cannot be blank")
        with self._publication_lock, self._lock:
            working = self._working_contexts.get(user_id)
            guard = self._working_publication_guards.get(user_id)
            if working is None or working.league_state is None or guard is None:
                raise ValueError("no working intelligence generation is available")
            if not _terminal_intelligence(
                working.forecast_evidence,
                working.simulation_analytics,
                working.value_evidence,
            ):
                raise ValueError("working intelligence generation is not terminal")
            published = self._published_context(user_id)
            if published.league_state is None:
                raise ValueError("published league disappeared during reconciliation")
            current_identity = (
                self._league_generations.get(user_id, 0),
                published.league_state.league.league_id,
                published.league_state.state_id,
                published.selected_team_id,
                published.publication_generation_id,
            )
            expected_identity = (
                guard.league_generation,
                guard.league_id,
                guard.league_state_id,
                guard.selected_team_id,
                guard.publication_generation_id,
            )
            if current_identity != expected_identity:
                raise ValueError(
                    "published league/team/generation identity changed during reconciliation"
                )
            if (
                published.league_state.league.league_id
                != working.league_state.league.league_id
            ):
                raise ValueError("published league changed during reconciliation")
            if published.selected_team_id != working.selected_team_id:
                raise ValueError("managed team changed during reconciliation")

            previous_state_id = published.league_state.state_id

            # Critical ordering: validate -> durable commit -> in-memory swap while
            # holding the same lock used by select_team/set_league_state. No managed
            # team or publication generation can change in between these operations.
            if durable_commit is not None:
                durable_commit(working)

            promoted = replace(
                working,
                served_intelligence=None,
                publication_generation_id=generation_id,
                intelligence_reused=False,
            )
            self._contexts[user_id] = promoted
            self._working_contexts.pop(user_id, None)
            self._working_publication_guards.pop(user_id, None)
            self._pending_intelligence.pop(user_id, None)
            if previous_state_id != working.league_state.state_id:
                self._league_generations[user_id] = (
                    self._league_generations.get(user_id, 0) + 1
                )
            return promoted

    def bind_publication_generation_id(
        self,
        user_id: str,
        publication_generation_id: str,
    ) -> UserRuntimeContext:
        """Bind a manifest generation to an already-published restored bundle."""

        generation_id = str(publication_generation_id or "").strip()
        if not generation_id:
            raise ValueError("publication_generation_id cannot be blank")
        with self._publication_lock, self._lock:
            current = self._published_context(user_id)
            if current.league_state is None:
                raise ValueError("cannot bind publication identity without a league")
            updated = replace(
                current,
                publication_generation_id=generation_id,
            )
            self._contexts[user_id] = updated
            return updated

    def league_generation(self, user_id: str) -> int:
        """Return the in-process league identity generation for job invalidation."""

        with self._lock:
            return self._league_generations.get(user_id, 0)

    def set_league_state(self, user_id: str, league_state: LeagueState) -> UserRuntimeContext:
        """Advance canonical State without evicting same-league last-good presentation.

        Current Forecast/Simulation/Value fields remain exact/compatible inputs for
        model consumers. A prior terminal same-league bundle is retained separately
        as served_intelligence so presentation can remain usable and explicitly stale
        while replacement intelligence is built for the new canonical State.
        """

        if not user_id.strip():
            raise ValueError("user_id cannot be blank")
        with self._publication_lock, self._lock:
            current = self._published_context(user_id)
            # Explicit State activation (connect/switch) supersedes any unpublished
            # work targeting the previous selection.
            self._working_contexts.pop(user_id, None)
            self._working_publication_guards.pop(user_id, None)
            self._pending_intelligence.pop(user_id, None)
            previous_state = current.league_state
            previous_state_id = (
                previous_state.state_id if previous_state is not None else None
            )
            if previous_state_id != league_state.state_id:
                self._league_generations[user_id] = (
                    self._league_generations.get(user_id, 0) + 1
                )

            valid_team_ids = {team.team_id for team in league_state.teams}
            same_league = bool(
                previous_state is not None
                and previous_state.league.league_id == league_state.league.league_id
            )
            selected = (
                current.selected_team_id
                if current.selected_team_id in valid_team_ids
                else None
            )

            # Exact same State can keep current governed intelligence in place.
            if (
                same_league
                and previous_state is not None
                and previous_state.state_id == league_state.state_id
            ):
                reused = UserRuntimeContext(
                    user_id=user_id,
                    league_state=league_state,
                    selected_team_id=selected,
                    forecast_evidence=current.forecast_evidence,
                    simulation_analytics=current.simulation_analytics,
                    value_evidence=current.value_evidence,
                    served_intelligence=current.served_intelligence,
                    publication_generation_id=current.publication_generation_id,
                    intelligence_reused=True,
                )
                self._contexts[user_id] = reused
                return reused

            served = None
            if same_league:
                served = (
                    _served_snapshot_from_context(current)
                    or current.served_intelligence
                )
                if (
                    served is not None
                    and served.league_id
                    != league_state.league.league_id
                ):
                    served = None

            forecast_evidence = current.forecast_evidence
            forecast_cutoff_compatible = bool(
                forecast_evidence is not None
                and not any(
                    item.as_of > league_state.as_of
                    for item in (
                        forecast_evidence.raw_forecasts
                        + forecast_evidence.league_scored_forecasts
                    )
                )
            )
            pending = self._pending_intelligence.get(user_id)
            pending_compatible = (
                pending is None
                or pending.league_state_id == league_state.state_id
            )
            forecast_reusable = bool(
                same_league
                and previous_state is not None
                and forecast_evidence is not None
                and pending_compatible
                and forecast_cutoff_compatible
                and _forecast_supplement_compatible(
                    league_state,
                    forecast_evidence,
                )
                and forecast_input_fingerprint(previous_state)
                == forecast_input_fingerprint(league_state)
            )

            context = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected if same_league else None,
                forecast_evidence=forecast_evidence if forecast_reusable else None,
                simulation_analytics=None,
                value_evidence=None,
                served_intelligence=served,
                # Partial Forecast compatibility is reuse, but the complete
                # intelligence bundle is not reused until exact-State layers attach.
                intelligence_reused=False,
            )
            self._contexts[user_id] = context
            # Any pending work belongs to the prior target unless it already matches
            # the newly activated exact State.
            if (
                not same_league
                or (
                    pending is not None
                    and pending.league_state_id != league_state.state_id
                )
            ):
                self._pending_intelligence.pop(user_id, None)
            return context

    def set_league_state_if_generation(
        self,
        user_id: str,
        league_state: LeagueState,
        *,
        expected_generation: int,
        expected_league_id: str | None = None,
    ) -> UserRuntimeContext | None:
        """Atomically activate State only while the caller still owns refresh authority."""

        with self._publication_lock, self._lock:
            if self._league_generations.get(user_id, 0) != expected_generation:
                return None
            current = self.get(user_id)
            if (
                expected_league_id is not None
                and (
                    current.league_state is None
                    or current.league_state.league.league_id != expected_league_id
                )
            ):
                return None
            return self.set_league_state(user_id, league_state)

    def set_forecast_evidence(
        self,
        user_id: str,
        evidence: LiveForecastEvidence,
        *,
        refreshed_league_state: LeagueState | None = None,
    ) -> UserRuntimeContext:
        """Attach NEXT-2 evidence, optionally advancing state past evidence cutoff."""

        with self._lock:
            current = self._mutation_context(user_id)
            league_state = refreshed_league_state or current.league_state
            if league_state is None:
                raise ValueError("cannot attach forecasts before a league is loaded")
            if (
                current.league_state is not None
                and current.league_state.league.league_id != league_state.league.league_id
            ):
                raise ValueError("cannot attach forecasts for a different loaded league")
            forecasts = evidence.raw_forecasts + evidence.league_scored_forecasts
            if any(item.as_of > league_state.as_of for item in forecasts):
                raise ValueError("forecast evidence cannot postdate canonical league state")
            selected = current.selected_team_id
            valid_team_ids = {team.team_id for team in league_state.teams}
            if selected not in valid_team_ids:
                selected = None
            pending = _PendingIntelligenceSnapshot(
                league_state_id=league_state.state_id,
            )
            self._pending_intelligence[user_id] = pending

            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected,
                forecast_evidence=evidence,
                simulation_analytics=None,
                value_evidence=None,
                served_intelligence=current.served_intelligence,
                intelligence_reused=False,
            )
            return self._store_mutation_context(user_id, updated)

    def set_simulation_analytics(
        self,
        user_id: str,
        result: LiveSimulationAnalyticsResult,
    ) -> UserRuntimeContext:
        """Attach Simulation only to the exact current State/Forecast identity."""

        with self._lock:
            current = self._mutation_context(user_id)
            result_state_id = result.league_view.context.league_state_id
            league_state = current.league_state
            forecast_evidence = current.forecast_evidence
            if (
                league_state is None
                or forecast_evidence is None
                or league_state.state_id != result_state_id
            ):
                raise ValueError(
                    "cannot attach simulation before matching current league and forecast evidence"
                )
            selected = current.selected_team_id
            if selected not in {team.team_id for team in league_state.teams}:
                selected = None
            self._pending_intelligence[user_id] = _PendingIntelligenceSnapshot(
                league_state_id=league_state.state_id,
            )
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected,
                forecast_evidence=forecast_evidence,
                simulation_analytics=result,
                value_evidence=None,
                served_intelligence=current.served_intelligence,
                intelligence_reused=False,
            )
            return self._store_mutation_context(user_id, updated)

    def set_value_evidence(
        self,
        user_id: str,
        result: CurrentMarketValueRuntimeResult,
    ) -> UserRuntimeContext:
        """Attach Value only to the exact current canonical State."""

        with self._lock:
            current = self._mutation_context(user_id)
            league_state = current.league_state
            if (
                league_state is None
                or league_state.state_id != result.league_state_id
            ):
                raise ValueError("Value evidence must match current LeagueState")
            selected = current.selected_team_id
            if selected not in {team.team_id for team in league_state.teams}:
                selected = None
            # Presentation continuity is promoted after all product-required layers
            # reconcile. Keep the prior served identity until that manifest succeeds.
            served = current.served_intelligence
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=current.simulation_analytics,
                value_evidence=result,
                served_intelligence=served,
                intelligence_reused=False,
            )
            self._pending_intelligence.pop(user_id, None)
            return self._store_mutation_context(user_id, updated)

    def set_intelligence_bundle(
        self,
        user_id: str,
        *,
        league_state: LeagueState,
        forecast_evidence: LiveForecastEvidence,
        simulation_analytics: LiveSimulationAnalyticsResult | None,
        value_evidence: CurrentMarketValueRuntimeResult | None,
    ) -> UserRuntimeContext:
        """Atomically attach one internally consistent intelligence snapshot."""

        forecasts = forecast_evidence.raw_forecasts + forecast_evidence.league_scored_forecasts
        if any(item.as_of > league_state.as_of for item in forecasts):
            raise ValueError("forecast evidence cannot postdate canonical league state")
        if simulation_analytics is not None and simulation_analytics.league_view.context.league_state_id != league_state.state_id:
            raise ValueError("simulation analytics must match intelligence LeagueState")
        if value_evidence is not None and value_evidence.league_state_id != league_state.state_id:
            raise ValueError("Value evidence must match intelligence LeagueState")

        with self._lock:
            current = self._mutation_context(user_id)
            if current.league_state is not None and current.league_state.league.league_id != league_state.league.league_id:
                raise ValueError("cannot attach intelligence for a different loaded league")
            selected = current.selected_team_id
            valid_team_ids = {team.team_id for team in league_state.teams}
            if selected not in valid_team_ids:
                selected = None
            # Do not evict stale presentation merely because core F/S/V is terminal;
            # hosted product reconciliation clears it after the replacement read model
            # is durably promoted.
            served = current.served_intelligence
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=league_state,
                selected_team_id=selected,
                forecast_evidence=forecast_evidence,
                simulation_analytics=simulation_analytics,
                value_evidence=value_evidence,
                served_intelligence=served,
                intelligence_reused=False,
            )
            self._pending_intelligence.pop(user_id, None)
            return self._store_mutation_context(user_id, updated)

    def set_served_intelligence(
        self,
        user_id: str,
        snapshot: ServedIntelligenceSnapshot | None,
    ) -> UserRuntimeContext:
        """Attach lightweight presentation-only same-league last-good identity."""

        with self._lock:
            current = self.get(user_id)
            if (
                snapshot is not None
                and current.league_state is not None
                and snapshot.league_id != current.league_state.league.league_id
            ):
                raise ValueError("served intelligence must belong to the loaded league")
            updated = UserRuntimeContext(
                user_id=current.user_id,
                league_state=current.league_state,
                selected_team_id=current.selected_team_id,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=current.simulation_analytics,
                value_evidence=current.value_evidence,
                served_intelligence=snapshot,
                publication_generation_id=current.publication_generation_id,
                intelligence_reused=current.intelligence_reused,
            )
            self._contexts[user_id] = updated
            return updated

    def select_team_if_working_generation_active(
        self,
        user_id: str,
        team_id: str,
    ) -> tuple[UserRuntimeContext, UserRuntimeContext] | None:
        """Select a team only if unpublished work is still active at serialization."""

        if not team_id.strip():
            raise ValueError("team_id cannot be blank")
        with self._publication_lock, self._lock:
            working = self._working_contexts.get(user_id)
            if working is None:
                return None
            return working, self.select_team(user_id, team_id)

    def select_team(self, user_id: str, team_id: str) -> UserRuntimeContext:
        if not team_id.strip():
            raise ValueError("team_id cannot be blank")
        with self._publication_lock, self._lock:
            current = self._published_context(user_id)
            if current.league_state is None:
                raise ValueError("cannot select team before a league is loaded")
            valid_team_ids = {team.team_id for team in current.league_state.teams}
            if team_id not in valid_team_ids:
                raise ValueError("selected team does not belong to loaded league")
            if team_id == current.selected_team_id:
                return current

            # Managed-team identity participates in reconciliation authority. A
            # selection that wins before publication interrupts the working
            # generation before any durable publication commit can begin.
            self._league_generations[user_id] = (
                self._league_generations.get(user_id, 0) + 1
            )
            self._working_contexts.pop(user_id, None)
            self._working_publication_guards.pop(user_id, None)
            self._pending_intelligence.pop(user_id, None)
            updated = UserRuntimeContext(
                user_id=user_id,
                league_state=current.league_state,
                selected_team_id=team_id,
                forecast_evidence=current.forecast_evidence,
                simulation_analytics=current.simulation_analytics,
                value_evidence=current.value_evidence,
                served_intelligence=(
                    replace(
                        current.served_intelligence,
                        publication_generation_id=None,
                    )
                    if current.served_intelligence is not None
                    else None
                ),
                # Presentation snapshots are team-specific. A selection change
                # invalidates the old presentation generation identity; the next
                # presentation promotion/reconciliation will bind a new one.
                publication_generation_id=None,
                intelligence_reused=current.intelligence_reused,
            )
            self._contexts[user_id] = updated
            return updated

    def clear(self, user_id: str) -> None:
        with self._publication_lock, self._lock:
            self._contexts.pop(user_id, None)
            self._working_contexts.pop(user_id, None)
            self._working_publication_guards.pop(user_id, None)
            self._pending_intelligence.pop(user_id, None)
            self._league_generations[user_id] = self._league_generations.get(user_id, 0) + 1
