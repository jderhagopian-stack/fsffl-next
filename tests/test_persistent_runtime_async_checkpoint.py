from __future__ import annotations

from datetime import UTC, datetime
from threading import Event
from time import monotonic, sleep

from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 10, 7, 0, tzinfo=UTC)


class MemoryPersistence:
    def __init__(self) -> None:
        self.user = None
        self.league = None
        self.teams = {}

    def get_user_runtime_context(self, *, user_id):
        return self.user if self.user and self.user.user_id == user_id else None

    def put_user_runtime_context(self, record):
        self.user = record

    def get_league_snapshot(self, *, provider, league_id, season):
        row = self.league
        return row if row and (row.provider, row.league_id, row.season) == (provider, league_id, season) else None

    def put_league_snapshot(self, record):
        self.league = record

    def get_team_snapshot(self, *, provider, league_id, team_id):
        return self.teams.get((provider, league_id, team_id))

    def put_team_snapshot(self, record):
        self.teams[(record.provider, record.league_id, record.team_id)] = record

    def get_sync_cursor(self, **_kwargs):
        return None

    def put_sync_cursor(self, _record):
        pass

    def get_reusable_artifact(self, _key):
        return None

    def get_latest_reusable_artifact(self, **_kwargs):
        return None

    def put_artifact(self, _record):
        pass

    def invalidate_scope(self, **_kwargs):
        pass

    def append_market_value_snapshot(self, **_kwargs):
        pass

    def append_user_perceived_latency(self, _record):
        pass


def _state() -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=NOW, effective_at=NOW)
    league = League(
        league_id="sleeper:123",
        name="Test",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(ScoringRule(stat="pass_yd", points=0.04),),
        ),
        provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(
            Team(team_id="team:a", league_id=league.league_id, display_name="A"),
            Team(team_id="team:b", league_id=league.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(team_id="team:a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.QB),)),
            TeamState(team_id="team:b", roster=(RosterEntry(player_id="p2", slot=RosterSlot.QB),)),
        ),
        players=(
            Player(player_id="p1", full_name="One", position=Position.QB),
            Player(player_id="p2", full_name="Two", position=Position.QB),
        ),
        player_states=(
            PlayerState(player_id="p1", as_of=NOW, status=PlayerStatus.ACTIVE, provenance=provenance),
            PlayerState(player_id="p2", as_of=NOW, status=PlayerStatus.ACTIVE, provenance=provenance),
        ),
        provenance=(provenance,),
    )


class SlowPersistence(MemoryPersistence):
    def put_league_snapshot(self, record):
        sleep(0.1)
        super().put_league_snapshot(record)


class WriteFailingPersistence(MemoryPersistence):
    def __init__(self) -> None:
        super().__init__()
        self.write_attempted = Event()

    def put_league_snapshot(self, record):
        self.write_attempted.set()
        raise RuntimeError("disk unavailable")


def test_runtime_mutation_returns_before_slow_checkpoint_completes() -> None:
    persistence = SlowPersistence()
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)

    started = monotonic()
    context = runtime.set_league_state("jimmy", _state())
    elapsed = monotonic() - started

    assert context.league_state is not None
    assert elapsed < 0.08

    deadline = monotonic() + 2
    while persistence.get_user_runtime_context(user_id="jimmy") is None and monotonic() < deadline:
        sleep(0.01)
    assert persistence.get_user_runtime_context(user_id="jimmy") is not None


def test_failed_async_checkpoint_does_not_replace_authoritative_runtime_state() -> None:
    persistence = WriteFailingPersistence()
    runtime = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    state = _state()

    context = runtime.set_league_state("jimmy", state)

    assert persistence.write_attempted.wait(timeout=2)
    current = runtime.get("jimmy")
    assert context.league_state == state
    assert current.league_state == state
    assert persistence.get_user_runtime_context(user_id="jimmy") is None
