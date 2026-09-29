from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol

from .models import LeagueState


class StateSnapshotStore(Protocol):
    def save(self, state: LeagueState) -> None: ...

    def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None: ...

    def recent_at_or_before(
        self,
        league_id: str,
        as_of: datetime,
        *,
        limit: int = 32,
    ) -> tuple[LeagueState, ...]: ...


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
                and existing.state_id == state.state_id
            )
        ]
        self._states.append(state)

    def recent_at_or_before(
        self,
        league_id: str,
        as_of: datetime,
        *,
        limit: int = 32,
    ) -> tuple[LeagueState, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        indexed = [
            (index, state)
            for index, state in enumerate(self._states)
            if state.league.league_id == league_id and state.as_of <= as_of
        ]
        indexed.sort(key=lambda item: (item[1].as_of, item[0]), reverse=True)
        return tuple(state for _index, state in indexed[:limit])

    def latest_at_or_before(self, league_id: str, as_of: datetime) -> LeagueState | None:
        recent = self.recent_at_or_before(league_id, as_of, limit=1)
        return recent[0] if recent else None
