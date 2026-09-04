from __future__ import annotations

from collections.abc import Iterable, Protocol
from datetime import datetime

from .models import LeagueState


class StateSnapshotStore(Protocol):
    def save(self, state: LeagueState) -> None: ...

    def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None: ...


class StateMaterializer(Protocol):
    def materialize(self, league_id: str, as_of: datetime) -> LeagueState: ...


class InMemorySnapshotStore:
    """Simple deterministic store for tests and local development.

    Production storage is intentionally deferred; downstream code depends on the
    protocol rather than on a database choice.
    """

    def __init__(self, states: Iterable[LeagueState] = ()) -> None:
        self._states: list[LeagueState] = []
        for state in states:
            self.save(state)

    def save(self, state: LeagueState) -> None:
        self._states = [
            existing
            for existing in self._states
            if not (
                existing.league.league_id == state.league.league_id
                and existing.as_of == state.as_of
            )
        ]
        self._states.append(state)
        self._states.sort(key=lambda item: (item.league.league_id, item.as_of))

    def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None:
        candidates = [
            state
            for state in self._states
            if state.league.league_id == league_id and state.as_of <= as_of
        ]
        return max(candidates, key=lambda item: item.as_of) if candidates else None
