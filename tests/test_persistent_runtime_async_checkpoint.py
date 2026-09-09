from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic, sleep

from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    ProviderRef,
    RosterSlot,
    Team,
    TeamState,
)


class MemoryPersistence:
    def __init__(self) -> None:
        self.user = None
        self.league = None
        self.teams = {}
        self.artifacts = []
        self.market = []

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

    def get_sync_cursor(self, **kwargs):
        return None

    def put_sync_cursor(self, record):
        pass

    def get_reusable_artifact(self, key):
        return next((row for row in self.artifacts if row.key == key and row.reusable), None)

    def get_latest_reusable_artifact(self, *, artifact_kind, scope_kind, scope_id, model_version):
        rows = [
            row for row in self.artifacts
            if row.reusable
            and row.key.artifact_kind == artifact_kind
            and row.key.scope_kind == scope_kind
            and row.key.scope_id == scope_id
            and row.key.model_version == model_version
        ]
        return max(rows, key=lambda row: row.computed_at) if rows else None

    def put_artifact(self, record):
        self.artifacts.append(record)

    def invalidate_scope(self, **kwargs):
        pass

    def append_market_value_snapshot(self, **kwargs):
        self.market.append(kwargs)


def _state() -> LeagueState:
    league_id = "sleeper:123"
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Test League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
                scoring=(),
            ),
            provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
        ),
        as_of=datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(TeamState(team_id="t1", roster=()), TeamState(team_id="t2", roster=())),
        players=(),
        player_states=(),
    )


def test_state_only_checkpoint_is_async_and_restores_after_restart() -> None:
    persistence = MemoryPersistence()
    runtime = PersistentPrivateBetaRuntimeStore(persistence)
    state = _state()

    before = monotonic()
    runtime.set_league_state("jimmy", state)
    elapsed = monotonic() - before
    assert elapsed < 0.25

    deadline = monotonic() + 2
    while persistence.user is None and monotonic() < deadline:
        sleep(0.01)
    assert persistence.user is not None

    restarted = PersistentPrivateBetaRuntimeStore(persistence)
    restored = restarted.get("jimmy")
    assert restored.league_state == state
    assert restored.forecast_evidence is None
    assert restored.simulation_analytics is None
    assert restored.value_evidence is None
