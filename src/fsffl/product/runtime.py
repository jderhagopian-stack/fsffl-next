from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Callable

from fsffl.providers.acquisition import ProviderBackedStateService
from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.state.models import LeagueState


LiveStateLoader = Callable[[str], LeagueState]


def default_sleeper_state_loader(league_external_id: str) -> LeagueState:
    """Materialize current canonical state through the governed provider path."""

    service = ProviderBackedStateService(
        source=SleeperLiveSource(),
        normalizer=SleeperSnapshotNormalizer(),
    )
    return service.materialize_live(league_external_id=league_external_id)


@dataclass(frozen=True)
class UserRuntimeContext:
    user_id: str
    league_state: LeagueState | None = None
    selected_team_id: str | None = None


class PrivateBetaRuntimeStore:
    """Small in-memory runtime store for the single-user/private beta.

    Canonical league state lives in process memory only. It is not written to the
    repository. A durable multi-user store can replace this interface later.
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
            )
            self._contexts[user_id] = updated
            return updated

    def clear(self, user_id: str) -> None:
        with self._lock:
            self._contexts.pop(user_id, None)
