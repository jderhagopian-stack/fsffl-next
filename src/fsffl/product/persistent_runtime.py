from __future__ import annotations

import logging
from threading import RLock

from fsffl.persistence import PersistenceStore, persistence_store_from_env
from fsffl.persistence.session import persist_runtime_snapshot, restore_runtime_snapshot

from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext

_logger = logging.getLogger("fsffl.product.persistence")


class PersistentPrivateBetaRuntimeStore(PrivateBetaRuntimeStore):
    """Durability wrapper around the proven in-memory private-beta runtime.

    Postgres is a reusable state/artifact cache only. Any persistence failure fails open
    to the existing runtime so storage can never become a second model authority or a
    single point of failure for calculations already in memory.
    """

    def __init__(self, persistence_store: PersistenceStore | None = None) -> None:
        super().__init__()
        self._persistence = persistence_store if persistence_store is not None else persistence_store_from_env()
        self._restore_lock = RLock()
        self._restore_attempted: set[str] = set()

    @property
    def persistence_enabled(self) -> bool:
        return self._persistence is not None

    def _checkpoint(self, user_id: str, context: UserRuntimeContext) -> None:
        if self._persistence is None or context.league_state is None:
            return
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
            _logger.warning("FSFFL persistence checkpoint failed user=%s error=%s", user_id, exc)

    def _restore_once(self, user_id: str) -> None:
        if self._persistence is None:
            return
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
                    super().set_intelligence_bundle(
                        user_id,
                        league_state=snapshot.league_state,
                        forecast_evidence=snapshot.forecast_evidence,
                        simulation_analytics=snapshot.simulation_analytics,
                        value_evidence=snapshot.value_evidence,
                    )
                if snapshot.selected_team_id is not None:
                    super().select_team(user_id, snapshot.selected_team_id)
                _logger.info(
                    "FSFFL durable runtime restored user=%s league=%s forecast=%s simulation=%s value=%s",
                    user_id,
                    snapshot.league_state.league.league_id,
                    snapshot.forecast_evidence is not None,
                    snapshot.simulation_analytics is not None,
                    snapshot.value_evidence is not None,
                )
            except Exception as exc:
                _logger.warning("FSFFL persistence restore failed user=%s error=%s", user_id, exc)

    def get(self, user_id: str) -> UserRuntimeContext:
        current = super().get(user_id)
        if current.league_state is None:
            self._restore_once(user_id)
            current = super().get(user_id)
        return current

    def set_league_state(self, user_id: str, league_state):
        context = super().set_league_state(user_id, league_state)
        with self._restore_lock:
            self._restore_attempted.add(user_id)
        self._checkpoint(user_id, context)
        return context

    def set_forecast_evidence(self, user_id: str, evidence, *, refreshed_league_state=None):
        context = super().set_forecast_evidence(
            user_id,
            evidence,
            refreshed_league_state=refreshed_league_state,
        )
        self._checkpoint(user_id, context)
        return context

    def set_simulation_analytics(self, user_id: str, result):
        context = super().set_simulation_analytics(user_id, result)
        self._checkpoint(user_id, context)
        return context

    def set_value_evidence(self, user_id: str, result):
        context = super().set_value_evidence(user_id, result)
        self._checkpoint(user_id, context)
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
        self._checkpoint(user_id, context)
        return context

    def select_team(self, user_id: str, team_id: str):
        context = super().select_team(user_id, team_id)
        self._checkpoint(user_id, context)
        return context
