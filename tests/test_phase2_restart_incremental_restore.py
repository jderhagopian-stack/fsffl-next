from __future__ import annotations

from datetime import UTC, datetime
from time import sleep

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.persistence import SyncCursorRecord
from fsffl.persistence.session import persist_runtime_snapshot
from fsffl.product.hosted_connect import install_hosted_connect_routes
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.providers.sleeper_live import SleeperSyncProbe
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
        self.cursors = {}
        self.artifacts = []

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

    def get_sync_cursor(self, *, provider, scope_kind, scope_id):
        return self.cursors.get((provider, scope_kind, scope_id))

    def put_sync_cursor(self, record):
        self.cursors[(record.provider, record.scope_kind, record.scope_id)] = record

    def get_reusable_artifact(self, key):
        return next((row for row in self.artifacts if row.key == key and row.reusable), None)

    def get_latest_reusable_artifact(self, *, artifact_kind, scope_kind, scope_id, model_version):
        rows = [
            row
            for row in self.artifacts
            if row.reusable
            and row.key.artifact_kind == artifact_kind
            and row.key.scope_kind == scope_kind
            and row.key.scope_id == scope_id
            and row.key.model_version == model_version
        ]
        return max(rows, key=lambda row: row.computed_at) if rows else None

    def put_artifact(self, record):
        self.artifacts.append(record)

    def invalidate_scope(self, **_kwargs):
        pass

    def append_market_value_snapshot(self, **_kwargs):
        pass

    def append_user_perceived_latency(self, _record):
        pass


class NoopBehavioralCoordinator:
    def start(self, **_kwargs):
        raise AssertionError("unchanged restored state should not rebuild Behavioral evidence")


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


def test_unchanged_restored_league_uses_probe_without_full_loader() -> None:
    persistence = MemoryPersistence()
    state = _state()
    persist_runtime_snapshot(
        persistence,
        user_id="local-beta-user",
        league_state=state,
        selected_team_id="team:a",
    )

    probe_time = datetime.now(UTC)
    probe = SleeperSyncProbe(
        league_external_id="123",
        captured_at=probe_time,
        season=2026,
        week=1,
        fingerprint="same-provider-fingerprint",
    )
    persistence.put_sync_cursor(
        SyncCursorRecord(
            provider="sleeper",
            scope_kind="league_refresh",
            scope_id="123",
            cursor_payload={
                "probe_fingerprint": probe.fingerprint,
                "season": probe.season,
                "week": probe.week,
                "last_full_refresh_at": probe_time.isoformat(),
            },
            synced_at=probe_time,
            source_updated_at=probe.captured_at,
        )
    )

    restarted = PersistentPrivateBetaRuntimeStore(persistence_store=persistence)
    restored = restarted.get("local-beta-user")
    assert restored.league_state == state
    assert restored.selected_team_id == "team:a"

    full_loader_calls = 0
    probe_calls: list[str] = []

    def full_loader(_league_external_id: str) -> LeagueState:
        nonlocal full_loader_calls
        full_loader_calls += 1
        raise AssertionError("unchanged state should not require a full Sleeper acquisition")

    def sync_probe_loader(league_external_id: str) -> SleeperSyncProbe:
        probe_calls.append(league_external_id)
        return probe

    app = FastAPI()
    install_hosted_connect_routes(
        app,
        runtime_store=restarted,
        state_loader=full_loader,
        behavioral_coordinator=NoopBehavioralCoordinator(),  # type: ignore[arg-type]
        persistence_store=persistence,
        sync_probe_loader=sync_probe_loader,
    )
    client = TestClient(app)
    response = client.post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "123"},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    payload = {}
    for _ in range(200):
        current = client.get("/api/connect/sleeper/background/current")
        payload = current.json()
        if payload["job_id"] == job_id and payload["status"] in {"completed", "failed"}:
            break
        sleep(0.01)
    else:
        raise AssertionError("background refresh did not complete")

    assert payload["status"] == "completed", payload
    assert probe_calls == ["123"]
    assert full_loader_calls == 0
