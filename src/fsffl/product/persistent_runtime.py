from __future__ import annotations

import logging
from dataclasses import replace
from time import monotonic
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from threading import RLock

from fsffl.persistence import PersistenceStore, persistence_store_from_env
from fsffl.persistence.session import (
    persist_league_last_good_identity,
    persist_runtime_snapshot,
    restore_last_good_state_identity,
    restore_runtime_snapshot,
    restore_state_bound_intelligence,
)
from fsffl.state.history import StateSnapshotStore

from .runtime import (
    PrivateBetaRuntimeStore,
    ServedIntelligenceSnapshot,
    UserRuntimeContext,
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
            return self._persistence is None
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
                        ),
                    )
                if snapshot.selected_team_id is not None:
                    super().select_team(user_id, snapshot.selected_team_id)
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
                forecast, simulation, values = restore_state_bound_intelligence(
                    self._persistence,
                    league_state=league_state,
                )
                if forecast is not None:
                    context = super().set_intelligence_bundle(
                        user_id,
                        league_state=league_state,
                        forecast_evidence=forecast,
                        simulation_analytics=simulation,
                        value_evidence=values,
                    )
                    self._contexts[user_id] = replace(
                        context,
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
                        context = super().set_served_intelligence(
                            user_id,
                            ServedIntelligenceSnapshot(
                                league_id=last_good_state.league.league_id,
                                league_state_id=last_good_state.state_id,
                                as_of=last_good_state.as_of,
                                team_ids=tuple(
                                    sorted(team.team_id for team in last_good_state.teams)
                                ),
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
        """Reuse only artifacts bound to the currently selected exact State."""

        current = super().get(user_id)
        if self._persistence is None or current.league_state is None:
            return current
        forecast, simulation, values = restore_state_bound_intelligence(
            self._persistence,
            league_state=current.league_state,
        )
        if forecast is None:
            return current
        restored = super().set_intelligence_bundle(
            user_id,
            league_state=current.league_state,
            forecast_evidence=forecast,
            simulation_analytics=simulation,
            value_evidence=values,
        )
        reused = replace(restored, intelligence_reused=True)
        self._contexts[user_id] = reused
        _logger.info(
            "FSFFL exact-state intelligence reuse user=%s league=%s state=%s forecast=%s simulation=%s value=%s",
            user_id,
            current.league_state.league.league_id,
            current.league_state.state_id,
            forecast is not None,
            simulation is not None,
            values is not None,
        )
        return reused

    def set_forecast_evidence(self, user_id: str, evidence, *, refreshed_league_state=None):
        context = super().set_forecast_evidence(
            user_id,
            evidence,
            refreshed_league_state=refreshed_league_state,
        )
        self._checkpoint_async(user_id, context)
        return context

    def set_simulation_analytics(self, user_id: str, result):
        context = super().set_simulation_analytics(user_id, result)
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
        self._checkpoint_async(user_id, context)
        return context

    def select_team(self, user_id: str, team_id: str):
        context = super().select_team(user_id, team_id)
        self._checkpoint_async(user_id, context)
        return context
