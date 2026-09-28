from __future__ import annotations

import logging
from dataclasses import replace
from time import monotonic
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import RLock

from fsffl.persistence import PersistenceStore, persistence_store_from_env
from fsffl.persistence.session import (
    migrate_legacy_last_good_identity,
    persist_league_last_good_identity,
    persist_forecast_replay_decision,
    persist_runtime_snapshot,
    restore_forecast_replay_decision,
    restore_last_good_state_identity,
    restore_runtime_snapshot,
    restore_published_generation_identity,
    restore_published_state_bound_intelligence,
    restore_state_bound_forecast,
    restore_state_bound_intelligence,
    restore_state_bound_raw_forecast_evidence,
)
from fsffl.state.history import StateSnapshotStore

from .runtime import (
    PrivateBetaRuntimeStore,
    ServedIntelligenceSnapshot,
    UserRuntimeContext,
    raw_forecast_compatibility_reasons,
    raw_forecast_input_fingerprint,
    replay_live_forecast_evidence_for_state,
)

_logger = logging.getLogger("fsffl.product.persistence")


class PersistentPrivateBetaRuntimeStore(PrivateBetaRuntimeStore):
    """Durability wrapper around the proven in-memory private-beta runtime.

    Postgres is a reusable state/artifact cache only. Any persistence failure fails open
    to the existing runtime so storage can never become a second model authority or a
    single point of failure for calculations already in memory.

    Hosted latency rule: persistence never sits on the user-request path. Canonical
    league State is checkpointed as soon as it is usable, and richer Forecast /
    Simulation / Value checkpoints follow in mutation order on one serialized worker.
    The same worker may also retain exact canonical State snapshots in the State-history
    store; that history is read-only persistence of State authority, never reconstruction.
    """

    def __init__(
        self,
        persistence_store: PersistenceStore | None = None,
        *,
        state_snapshot_store: StateSnapshotStore | None = None,
    ) -> None:
        super().__init__()
        self._persistence = persistence_store if persistence_store is not None else persistence_store_from_env()
        self._state_history = state_snapshot_store
        self._restore_lock = RLock()
        self._restore_attempted: set[str] = set()
        self._checkpoint_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="fsffl-persist",
        )
        self._checkpoint_futures: dict[str, Future[bool]] = {}
        self._checkpoint_state_ids: dict[str, str] = {}
        self._last_good_guard_users: set[str] = set()
        self._forecast_replay_decisions: dict[str, dict[str, object]] = {}

    def _record_forecast_replay_decision(
        self,
        user_id: str,
        *,
        league_state,
        decision: dict[str, object],
    ) -> None:
        payload = {
            **decision,
            "target_league_id": league_state.league.league_id,
            "target_state_id": league_state.state_id,
        }
        self._forecast_replay_decisions[user_id] = payload
        if self._persistence is not None:
            try:
                persist_forecast_replay_decision(
                    self._persistence,
                    user_id=user_id,
                    league_state=league_state,
                    decision=payload,
                )
            except Exception as exc:
                _logger.warning(
                    "FSFFL Forecast replay decision persistence failed user=%s league=%s state=%s error=%s",
                    user_id,
                    league_state.league.league_id,
                    league_state.state_id,
                    exc,
                )
        _logger.info(
            "FSFFL Forecast replay decision user=%s league=%s target_state=%s selection=%s raw_compatibility=%s reason=%s rejection_components=%s prior_state=%s",
            user_id,
            league_state.league.league_id,
            league_state.state_id,
            payload.get("selection"),
            payload.get("raw_compatibility"),
            payload.get("reason"),
            payload.get("rejection_components"),
            payload.get("prior_state_id"),
        )

    def forecast_replay_decision(self, user_id: str) -> dict[str, object] | None:
        current = super().get(user_id)
        if current.league_state is None:
            return None
        cached = self._forecast_replay_decisions.get(user_id)
        if cached is not None and cached.get("target_state_id") == current.league_state.state_id:
            return dict(cached)
        if self._persistence is None:
            return None
        try:
            restored = restore_forecast_replay_decision(
                self._persistence,
                user_id=user_id,
                league_state=current.league_state,
            )
        except Exception as exc:
            _logger.warning(
                "FSFFL Forecast replay decision restore failed user=%s state=%s error=%s",
                user_id,
                current.league_state.state_id,
                exc,
            )
            return None
        if restored is not None:
            self._forecast_replay_decisions[user_id] = restored
            return dict(restored)
        return None

    @property
    def persistence_enabled(self) -> bool:
        return self._persistence is not None

    def _persist_state_history(self, league_state) -> None:
        if self._state_history is None:
            return
        try:
            self._state_history.save(league_state)
        except Exception as exc:  # history retention must also fail open
            _logger.warning("FSFFL State history checkpoint failed league=%s error=%s", league_state.league.league_id, exc)

    def _checkpoint_state_history_async(self, league_state) -> None:
        if self._state_history is None:
            return
        self._checkpoint_executor.submit(self._persist_state_history, league_state)

    def _persist_context(self, user_id: str, context: UserRuntimeContext) -> bool:
        if context.league_state is None:
            return True
        started = monotonic()
        durable = True
        if self._persistence is not None:
            try:
                persist_runtime_snapshot(
                    self._persistence,
                    user_id=user_id,
                    league_state=context.league_state,
                    selected_team_id=context.selected_team_id,
                    forecast_evidence=context.forecast_evidence,
                    simulation_analytics=context.simulation_analytics,
                    value_evidence=context.value_evidence,
                )
            except Exception as exc:  # persistence must not break authoritative runtime
                durable = False
                _logger.warning("FSFFL persistence checkpoint failed user=%s error=%s", user_id, exc)
        self._persist_state_history(context.league_state)
        _logger.info(
            "FSFFL persistence checkpoint completed user=%s league=%s state=%s forecast=%s simulation=%s value=%s served_state=%s durable=%s elapsed=%.3fs",
            user_id,
            context.league_state.league.league_id,
            context.league_state.state_id,
            bool(context.forecast_evidence),
            bool(context.simulation_analytics),
            bool(context.value_evidence),
            (
                context.served_intelligence.league_state_id
                if context.served_intelligence is not None
                else None
            ),
            durable,
            max(0.0, monotonic() - started),
        )
        return durable

    def _checkpoint_async(
        self,
        user_id: str,
        context: UserRuntimeContext,
    ) -> Future[bool] | None:
        if context.league_state is None or (
            self._persistence is None and self._state_history is None
        ):
            return None
        # One worker preserves mutation order. Within the same exact State, a newer
        # context subsumes an older queued checkpoint (State -> Forecast -> Simulation
        # -> Value), so cancel queued superseded work before appending the latest
        # snapshot. A running checkpoint is never interrupted, and cross-State work is
        # never cancelled: prior-state durability must remain intact across switches.
        state_id = context.league_state.state_id
        with self._restore_lock:
            previous = self._checkpoint_futures.get(user_id)
            previous_state_id = self._checkpoint_state_ids.get(user_id)
            if (
                previous is not None
                and previous_state_id == state_id
                and not previous.done()
                and previous.cancel()
            ):
                _logger.info(
                    "FSFFL persistence checkpoint coalesced user=%s state=%s",
                    user_id,
                    state_id,
                )
            future = self._checkpoint_executor.submit(
                self._persist_context,
                user_id,
                context,
            )
            self._checkpoint_futures[user_id] = future
            self._checkpoint_state_ids[user_id] = state_id
        return future

    def wait_for_checkpoint(self, user_id: str, *, timeout: float = 30.0) -> bool:
        """Wait for the latest serialized checkpoint without moving persistence onto the request path."""

        with self._restore_lock:
            future = self._checkpoint_futures.get(user_id)
        if future is None:
            return True
        try:
            return bool(future.result(timeout=timeout))
        except FutureTimeoutError:
            _logger.warning("FSFFL persistence checkpoint timed out user=%s", user_id)
            return False
        except Exception as exc:
            _logger.warning("FSFFL persistence checkpoint wait failed user=%s error=%s", user_id, exc)
            return False

    def _restore_once(self, user_id: str) -> None:
        if self._persistence is None:
            return
        started = monotonic()
        with self._restore_lock:
            if user_id in self._restore_attempted:
                return
            self._restore_attempted.add(user_id)
            try:
                snapshot = restore_runtime_snapshot(self._persistence, user_id=user_id)
                if snapshot is None:
                    return
                super().set_league_state(user_id, snapshot.league_state)
                if snapshot.forecast_evidence is not None:
                    restored = super().set_intelligence_bundle(
                        user_id,
                        league_state=snapshot.league_state,
                        forecast_evidence=snapshot.forecast_evidence,
                        simulation_analytics=snapshot.simulation_analytics,
                        value_evidence=snapshot.value_evidence,
                    )
                    self._contexts[user_id] = replace(
                        restored,
                        intelligence_reused=True,
                    )
                elif snapshot.value_evidence is not None:
                    restored = super().set_value_evidence(
                        user_id,
                        snapshot.value_evidence,
                    )
                    self._contexts[user_id] = replace(
                        restored,
                        intelligence_reused=True,
                    )
                if (
                    snapshot.served_league_id is not None
                    and snapshot.served_league_state_id is not None
                    and snapshot.served_as_of is not None
                ):
                    super().set_served_intelligence(
                        user_id,
                        ServedIntelligenceSnapshot(
                            league_id=snapshot.served_league_id,
                            league_state_id=snapshot.served_league_state_id,
                            as_of=snapshot.served_as_of,
                            team_ids=snapshot.served_team_ids,
                            publication_generation_id=(
                                snapshot.served_publication_generation_id
                            ),
                        ),
                    )
                if snapshot.selected_team_id is not None:
                    super().select_team(user_id, snapshot.selected_team_id)
                if snapshot.publication_generation_id is not None:
                    super().bind_publication_generation_id(
                        user_id,
                        snapshot.publication_generation_id,
                    )
                if (
                    snapshot.restored_from_last_good
                    and snapshot.forecast_evidence is not None
                    and snapshot.simulation_analytics is not None
                    and snapshot.value_evidence is not None
                ):
                    self._last_good_guard_users.add(user_id)
                else:
                    self._last_good_guard_users.discard(user_id)
                # Existing durable runtime rows may predate the point-in-time history
                # table. Retain the exact restored canonical state asynchronously so
                # restart recovery naturally backfills history without reingestion or
                # placing database writes on the user-request path.
                self._checkpoint_state_history_async(snapshot.league_state)
                _logger.info(
                    "FSFFL durable runtime restored user=%s league=%s forecast=%s simulation=%s value=%s",
                    user_id,
                    snapshot.league_state.league.league_id,
                    snapshot.forecast_evidence is not None,
                    snapshot.simulation_analytics is not None,
                    snapshot.value_evidence is not None,
                )
                _logger.info(
                    "FSFFL persist-first restore timing user=%s elapsed=%.3fs complete_bundle=%s",
                    user_id,
                    max(0.0, monotonic() - started),
                    (
                        snapshot.forecast_evidence is not None
                        and snapshot.simulation_analytics is not None
                        and snapshot.value_evidence is not None
                    ),
                )
                if self._persistence is not None:
                    # Upgrade compatibility: when the canonical current State is
                    # partial but restore found an older served identity through the
                    # legacy user-scoped record, migrate that league now before a
                    # later league switch overwrites the legacy pointer.
                    if snapshot.served_league_id is not None:
                        migrate_legacy_last_good_identity(
                            self._persistence,
                            user_id=user_id,
                            league_id=snapshot.served_league_id,
                        )

                    migrate_state = (
                        snapshot.league_state
                        if snapshot.forecast_evidence is not None
                        and snapshot.value_evidence is not None
                        and (
                            snapshot.simulation_analytics is not None
                            or not snapshot.forecast_evidence.uncertainty_ready
                        )
                        else None
                    )
                    if migrate_state is not None:
                        persist_league_last_good_identity(
                            self._persistence,
                            user_id=user_id,
                            league_state=migrate_state,
                            selected_team_id=snapshot.selected_team_id,
                        )
            except Exception as exc:
                _logger.warning("FSFFL persistence restore failed user=%s error=%s", user_id, exc)

    def restore_user(self, user_id: str) -> UserRuntimeContext:
        """Synchronously restore the last-good exact-compatible beta context.

        Hosted startup may call this before accepting traffic so the first useful
        request consumes persisted evidence instead of paying lazy-restore latency.
        """

        if not user_id.strip():
            raise ValueError("user_id cannot be blank")
        return self.get(user_id)

    def get(self, user_id: str) -> UserRuntimeContext:
        current = super().get(user_id)
        if current.league_state is None:
            self._restore_once(user_id)
            current = super().get(user_id)
        return current

    def set_league_state(self, user_id: str, league_state):
        current = super().get(user_id)
        previous_league_id = (
            current.league_state.league.league_id
            if current.league_state is not None
            else None
        )

        # Before a cross-league switch, checkpoint the current terminal identity.
        # Existing served-last-good identities are already durable and need no heavy
        # in-memory object graph to be rewritten.
        if (
            self._persistence is not None
            and previous_league_id is not None
            and previous_league_id != league_state.league.league_id
            and current.league_state is not None
            and current.forecast_evidence is not None
            and current.value_evidence is not None
            and (
                current.simulation_analytics is not None
                or not current.forecast_evidence.uncertainty_ready
            )
        ):
            try:
                persist_league_last_good_identity(
                    self._persistence,
                    user_id=user_id,
                    league_state=current.league_state,
                    selected_team_id=current.selected_team_id,
                )
            except Exception as exc:
                _logger.warning(
                    "FSFFL league last-good migration failed user=%s league=%s error=%s",
                    user_id,
                    previous_league_id,
                    exc,
                )

        context = super().set_league_state(user_id, league_state)
        if previous_league_id != league_state.league.league_id:
            self._last_good_guard_users.discard(user_id)
        with self._restore_lock:
            self._restore_attempted.add(user_id)

        # Reuse exact-State persisted authority first. If it is absent, restore
        # same-league last-good as presentation-only stale context.
        if self._persistence is not None:
            try:
                forecast, simulation, values, publication_generation_id = (
                    restore_published_state_bound_intelligence(
                        self._persistence,
                        user_id=user_id,
                        league_state=league_state,
                    )
                )
                manifest_generation_id, manifest_team_id = (
                    restore_published_generation_identity(
                        self._persistence,
                        user_id=user_id,
                        league_state=league_state,
                    )
                )
                if manifest_generation_id != publication_generation_id:
                    manifest_team_id = None
                if forecast is not None:
                    context = super().set_intelligence_bundle(
                        user_id,
                        league_state=league_state,
                        forecast_evidence=forecast,
                        simulation_analytics=simulation,
                        value_evidence=values,
                    )
                    selected_team_id = context.selected_team_id or manifest_team_id
                    bound_generation_id = (
                        publication_generation_id
                        if selected_team_id == manifest_team_id
                        else None
                    )
                    self._contexts[user_id] = replace(
                        context,
                        selected_team_id=selected_team_id,
                        publication_generation_id=bound_generation_id,
                        intelligence_reused=True,
                    )
                elif values is not None:
                    context = super().set_value_evidence(user_id, values)
                    selected_team_id = context.selected_team_id or manifest_team_id
                    bound_generation_id = (
                        publication_generation_id
                        if selected_team_id == manifest_team_id
                        else None
                    )
                    self._contexts[user_id] = replace(
                        context,
                        selected_team_id=selected_team_id,
                        publication_generation_id=bound_generation_id,
                        intelligence_reused=True,
                    )
                else:
                    last_good = restore_last_good_state_identity(
                        self._persistence,
                        user_id=user_id,
                        league_id=league_state.league.league_id,
                    )
                    if (
                        last_good is not None
                        and last_good[0].state_id != league_state.state_id
                    ):
                        last_good_state = last_good[0]
                        served_generation_id, served_team_id = (
                            restore_published_generation_identity(
                                self._persistence,
                                user_id=user_id,
                                league_state=last_good_state,
                            )
                        )
                        if served_team_id != context.selected_team_id:
                            served_generation_id = None
                        context = super().set_served_intelligence(
                            user_id,
                            ServedIntelligenceSnapshot(
                                league_id=last_good_state.league.league_id,
                                league_state_id=last_good_state.state_id,
                                as_of=last_good_state.as_of,
                                team_ids=tuple(
                                    sorted(team.team_id for team in last_good_state.teams)
                                ),
                                publication_generation_id=served_generation_id,
                            ),
                        )
            except Exception as exc:
                _logger.warning(
                    "FSFFL league intelligence restore failed user=%s league=%s state=%s error=%s",
                    user_id,
                    league_state.league.league_id,
                    league_state.state_id,
                    exc,
                )

        context = self._contexts.get(user_id, context)
        self._checkpoint_async(user_id, context)
        return context

    def restore_exact_state_intelligence(self, user_id: str) -> UserRuntimeContext:
        """Reuse exact-State authority, then replay compatible raw Forecast truth.

        Raw provider evidence compatibility is intentionally narrower than downstream
        scoring/state compatibility. Scoring, supplements, fantasy-week derivation,
        Simulation and Value rebuild independently for the target State.
        """

        current = self.working_context(user_id)
        if self._persistence is None or current.league_state is None:
            return current
        target_state = current.league_state

        forecast, simulation, values = restore_state_bound_intelligence(
            self._persistence,
            league_state=target_state,
        )
        if forecast is not None:
            restored = super().set_intelligence_bundle(
                user_id,
                league_state=target_state,
                forecast_evidence=forecast,
                simulation_analytics=simulation,
                value_evidence=values,
            )
            reused = replace(restored, intelligence_reused=True)
            self._store_mutation_context(user_id, reused)
            self._record_forecast_replay_decision(
                user_id,
                league_state=target_state,
                decision={
                    "selection": "exact_state_reuse",
                    "raw_compatibility": "exact_state",
                    "reason": "exact_state_forecast_artifact_available",
                    "rejection_components": [],
                    "prior_state_id": target_state.state_id,
                    "prior_evidence_model_version": forecast.model_version,
                    "prior_evidence_basis": forecast.evidence_basis,
                    "prior_successful_source_ids": list(forecast.successful_source_ids),
                    "prior_raw_observation_count": len(forecast.raw_forecasts),
                    "raw_prior_fingerprint": raw_forecast_input_fingerprint(target_state),
                    "raw_target_fingerprint": raw_forecast_input_fingerprint(target_state),
                    "downstream_rebuild_components": [],
                    "fresh_acquisition_required": False,
                    "served_last_good_available": bool(current.served_intelligence),
                },
            )
            return reused

        last_good = restore_last_good_state_identity(
            self._persistence,
            user_id=user_id,
            league_id=target_state.league.league_id,
        )
        if last_good is None:
            self._record_forecast_replay_decision(
                user_id,
                league_state=target_state,
                decision={
                    "selection": "fresh_acquisition",
                    "raw_compatibility": "not_evaluated",
                    "reason": "no_same_league_last_good_state",
                    "rejection_components": ["prior_state_unavailable"],
                    "prior_state_id": None,
                    "downstream_rebuild_components": [
                        "league_scoring",
                        "fantasy_regular_season",
                        "state_supplements",
                        "simulation",
                        "value",
                    ],
                    "fresh_acquisition_required": True,
                    "served_last_good_available": bool(current.served_intelligence),
                },
            )
            return current

        prior_state, _selected = last_good
        prior_forecast = restore_state_bound_raw_forecast_evidence(
            self._persistence,
            league_state=prior_state,
        )
        if prior_forecast is None:
            self._record_forecast_replay_decision(
                user_id,
                league_state=target_state,
                decision={
                    "selection": "fresh_acquisition",
                    "raw_compatibility": "not_evaluated",
                    "reason": "prior_governed_raw_forecast_artifact_unavailable",
                    "rejection_components": ["prior_raw_forecast_artifact_unavailable"],
                    "prior_state_id": prior_state.state_id,
                    "downstream_rebuild_components": [
                        "league_scoring",
                        "fantasy_regular_season",
                        "state_supplements",
                        "simulation",
                        "value",
                    ],
                    "fresh_acquisition_required": True,
                    "served_last_good_available": bool(current.served_intelligence),
                },
            )
            return current

        rejection_components = list(
            raw_forecast_compatibility_reasons(prior_state, target_state)
        )
        prior_raw_fingerprint = raw_forecast_input_fingerprint(prior_state)
        target_raw_fingerprint = raw_forecast_input_fingerprint(target_state)
        if rejection_components or prior_raw_fingerprint != target_raw_fingerprint:
            if not rejection_components:
                rejection_components = ["raw_forecast_material_inputs_changed"]
            self._record_forecast_replay_decision(
                user_id,
                league_state=target_state,
                decision={
                    "selection": "fresh_acquisition",
                    "raw_compatibility": "incompatible",
                    "reason": "raw_forecast_material_inputs_changed",
                    "rejection_components": rejection_components,
                    "prior_state_id": prior_state.state_id,
                    "prior_evidence_model_version": prior_forecast.model_version,
                    "prior_evidence_basis": prior_forecast.evidence_basis,
                    "prior_successful_source_ids": list(prior_forecast.successful_source_ids),
                    "prior_raw_observation_count": len(prior_forecast.raw_forecasts),
                    "raw_prior_fingerprint": prior_raw_fingerprint,
                    "raw_target_fingerprint": target_raw_fingerprint,
                    "downstream_rebuild_components": [
                        "raw_provider_ensemble",
                        "league_scoring",
                        "fantasy_regular_season",
                        "state_supplements",
                        "simulation",
                        "value",
                    ],
                    "fresh_acquisition_required": True,
                    "served_last_good_available": bool(current.served_intelligence),
                },
            )
            return current

        try:
            replayed = replay_live_forecast_evidence_for_state(
                target_state,
                prior_forecast,
            )
        except Exception as exc:
            self._record_forecast_replay_decision(
                user_id,
                league_state=target_state,
                decision={
                    "selection": "fresh_acquisition",
                    "raw_compatibility": "compatible",
                    "reason": f"downstream_replay_failed:{type(exc).__name__}",
                    "rejection_components": ["downstream_replay_runtime_failure"],
                    "prior_state_id": prior_state.state_id,
                    "prior_evidence_model_version": prior_forecast.model_version,
                    "prior_evidence_basis": prior_forecast.evidence_basis,
                    "prior_successful_source_ids": list(prior_forecast.successful_source_ids),
                    "prior_raw_observation_count": len(prior_forecast.raw_forecasts),
                    "raw_prior_fingerprint": prior_raw_fingerprint,
                    "raw_target_fingerprint": target_raw_fingerprint,
                    "downstream_rebuild_components": [
                        "league_scoring",
                        "fantasy_regular_season",
                        "state_supplements",
                        "simulation",
                        "value",
                    ],
                    "fresh_acquisition_required": True,
                    "served_last_good_available": bool(current.served_intelligence),
                    "error": str(exc),
                },
            )
            return current

        restored = super().set_forecast_evidence(
            user_id,
            replayed,
            refreshed_league_state=target_state,
        )
        reused = replace(restored, intelligence_reused=True)
        self._store_mutation_context(user_id, reused)
        if not self.working_generation_active(user_id):
            self._checkpoint_async(user_id, reused)
        self._record_forecast_replay_decision(
            user_id,
            league_state=target_state,
            decision={
                "selection": "raw_replay",
                "raw_compatibility": "compatible",
                "reason": "governed_raw_provider_ensemble_replayed",
                "rejection_components": [],
                "prior_state_id": prior_state.state_id,
                "prior_evidence_model_version": prior_forecast.model_version,
                "prior_evidence_basis": prior_forecast.evidence_basis,
                "prior_successful_source_ids": list(prior_forecast.successful_source_ids),
                "prior_raw_observation_count": len(prior_forecast.raw_forecasts),
                "raw_prior_fingerprint": prior_raw_fingerprint,
                "raw_target_fingerprint": target_raw_fingerprint,
                "downstream_rebuild_components": [
                    "league_scoring",
                    "fantasy_regular_season",
                    "state_supplements",
                    "simulation",
                    "value",
                ],
                "fresh_acquisition_required": False,
                "served_last_good_available": bool(current.served_intelligence),
                "replayed_successful_source_ids": list(replayed.successful_source_ids),
                "simulation_authority_blockers": list(
                    replayed.runtime_result.simulation_authority_blockers
                ),
            },
        )
        return reused

    def set_forecast_evidence(self, user_id: str, evidence, *, refreshed_league_state=None):
        context = super().set_forecast_evidence(
            user_id,
            evidence,
            refreshed_league_state=refreshed_league_state,
        )
        if not self.working_generation_active(user_id):
            self._checkpoint_async(user_id, context)
        return context

    def set_simulation_analytics(self, user_id: str, result):
        context = super().set_simulation_analytics(user_id, result)
        if not self.working_generation_active(user_id):
            self._checkpoint_async(user_id, context)
        return context

    def set_value_evidence(self, user_id: str, result):
        context = super().set_value_evidence(user_id, result)
        if (
            context.league_state is not None
            and context.league_state.state_id == result.league_state_id
            and all(
                item is not None
                for item in (
                    context.forecast_evidence,
                    context.simulation_analytics,
                    context.value_evidence,
                )
            )
        ):
            self._last_good_guard_users.discard(user_id)
        if not self.working_generation_active(user_id):
            self._checkpoint_async(user_id, context)
        return context

    def set_intelligence_bundle(
        self,
        user_id: str,
        *,
        league_state,
        forecast_evidence,
        simulation_analytics,
        value_evidence,
    ):
        context = super().set_intelligence_bundle(
            user_id,
            league_state=league_state,
            forecast_evidence=forecast_evidence,
            simulation_analytics=simulation_analytics,
            value_evidence=value_evidence,
        )
        if (
            context.league_state is not None
            and context.league_state.state_id == league_state.state_id
            and all(
                item is not None
                for item in (
                    context.forecast_evidence,
                    context.simulation_analytics,
                    context.value_evidence,
                )
            )
        ):
            self._last_good_guard_users.discard(user_id)
        if not self.working_generation_active(user_id):
            self._checkpoint_async(user_id, context)
        return context

    def checkpoint_working_generation(self, user_id: str) -> bool:
        """Durably checkpoint replacement artifacts without moving publication authority."""

        context = self.working_context(user_id)
        if context.league_state is None:
            return False
        if self._persistence is None:
            return True
        # Drain any older serialized checkpoint before writing working artifacts
        # synchronously, so an earlier State-only write cannot race after publication.
        if not self.wait_for_checkpoint(user_id, timeout=180.0):
            return False
        try:
            published = super().get(user_id)
            if (
                published.league_state is not None
                and published.forecast_evidence is not None
                and published.value_evidence is not None
                and (
                    published.simulation_analytics is not None
                    or not published.forecast_evidence.uncertainty_ready
                )
            ):
                # Upgrade/bootstrap guard: establish an exact published manifest
                # before newer same-State working artifacts enter the reusable cache.
                # This prevents a crash from making "latest" unpublished artifacts
                # restart-authoritative on the first refresh after deployment.
                generation_id = (
                    published.publication_generation_id
                    or f"bootstrap:{published.league_state.state_id}"
                )
                persist_runtime_snapshot(
                    self._persistence,
                    user_id=user_id,
                    league_state=published.league_state,
                    selected_team_id=published.selected_team_id,
                    forecast_evidence=published.forecast_evidence,
                    simulation_analytics=published.simulation_analytics,
                    value_evidence=published.value_evidence,
                    publish_context=True,
                    publication_generation_id=generation_id,
                )
                if published.publication_generation_id is None:
                    super().bind_publication_generation_id(
                        user_id,
                        generation_id,
                    )
            persist_runtime_snapshot(
                self._persistence,
                user_id=user_id,
                league_state=context.league_state,
                selected_team_id=context.selected_team_id,
                forecast_evidence=context.forecast_evidence,
                simulation_analytics=context.simulation_analytics,
                value_evidence=context.value_evidence,
                publish_context=False,
            )
            self._persist_state_history(context.league_state)
            _logger.info(
                "FSFFL working generation artifacts checkpointed user=%s state=%s",
                user_id,
                context.league_state.state_id,
            )
            return True
        except Exception as exc:
            _logger.warning(
                "FSFFL working generation checkpoint failed user=%s error=%s",
                user_id,
                exc,
            )
            return False

    def publish_working_generation(
        self,
        user_id: str,
        *,
        publication_generation_id: str,
    ):
        def durable_commit(working: UserRuntimeContext) -> None:
            if self._persistence is None:
                return
            # This callback executes inside the runtime publication lock after
            # league/team/generation identity validation and before the in-memory
            # swap. select_team/set_league_state therefore cannot advance identity
            # during the durable manifest+pointer commit.
            persist_runtime_snapshot(
                self._persistence,
                user_id=user_id,
                league_state=working.league_state,
                selected_team_id=working.selected_team_id,
                forecast_evidence=working.forecast_evidence,
                simulation_analytics=working.simulation_analytics,
                value_evidence=working.value_evidence,
                publish_context=True,
                publication_generation_id=publication_generation_id,
            )
            self._persist_state_history(working.league_state)

        context = super().publish_working_generation(
            user_id,
            publication_generation_id=publication_generation_id,
            durable_commit=durable_commit,
        )
        self._last_good_guard_users.discard(user_id)
        return context

    def bind_publication_generation_id(
        self,
        user_id: str,
        publication_generation_id: str,
    ):
        context = super().bind_publication_generation_id(
            user_id,
            publication_generation_id,
        )
        forecast = context.forecast_evidence
        values = context.value_evidence
        simulation = context.simulation_analytics
        if (
            self._persistence is not None
            and context.league_state is not None
            and forecast is not None
            and values is not None
            and (
                simulation is not None
                or not forecast.uncertainty_ready
            )
        ):
            persist_runtime_snapshot(
                self._persistence,
                user_id=user_id,
                league_state=context.league_state,
                selected_team_id=context.selected_team_id,
                forecast_evidence=forecast,
                simulation_analytics=simulation,
                value_evidence=values,
                publish_context=True,
                publication_generation_id=publication_generation_id,
            )
        return context

    def select_team(self, user_id: str, team_id: str):
        context = super().select_team(user_id, team_id)
        self._checkpoint_async(user_id, context)
        return context
