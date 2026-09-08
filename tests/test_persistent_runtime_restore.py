from __future__ import annotations

from datetime import UTC, datetime

from fsffl.persistence.session import persist_runtime_snapshot, restore_runtime_snapshot
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


def _league_state() -> LeagueState:
    league_id = "sleeper:123"
    rules = LeagueRules(
        team_count=2,
        roster_size=1,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Test League",
            season=2026,
            rules=rules,
            provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
        ),
        as_of=datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(TeamState(team_id="t1", roster=()), TeamState(team_id="t2", roster=())),
        players=(),
        player_states=(),
    )


def test_state_and_selected_team_restore_without_reingestion() -> None:
    persistence = MemoryPersistence()
    state = _league_state()

    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t2",
    )
    restored = restore_runtime_snapshot(persistence, user_id="jimmy")

    assert restored is not None
    assert restored.league_state == state
    assert restored.league_state.state_id == state.state_id
    assert restored.selected_team_id == "t2"
    assert restored.forecast_evidence is None
    assert len(persistence.teams) == 2


def test_restore_fails_closed_when_snapshot_hash_does_not_match_context() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    persist_runtime_snapshot(persistence, user_id="jimmy", league_state=state, selected_team_id=None)
    persistence.user = persistence.user.__class__(
        **{**persistence.user.__dict__, "state_hash": "wrong"}
    )

    assert restore_runtime_snapshot(persistence, user_id="jimmy") is None
