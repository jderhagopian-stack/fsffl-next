from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic, sleep

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.persistence.contracts import SyncCursorRecord
from fsffl.persistence.runtime_cache import SIMULATION_MODEL_VERSION
from fsffl.persistence.session import persist_runtime_snapshot
from fsffl.product.hosted_connect import (
    LeagueConnectStatus,
    install_hosted_connect_routes,
)
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.product.simulation_runtime import LiveSimulationAnalyticsResult
from fsffl.product.webapp import require_beta_user
from fsffl.providers.sleeper_live import SleeperSyncProbe
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
        self.cursor = None

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
        row = self.cursor
        if row is None:
            return None
        if (row.provider, row.scope_kind, row.scope_id) != (provider, scope_kind, scope_id):
            return None
        return row

    def put_sync_cursor(self, record):
        self.cursor = record

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

    def invalidate_scope(self, **kwargs):
        pass

    def append_market_value_snapshot(self, **kwargs):
        pass


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
            name="Restart Test League",
            season=2026,
            rules=rules,
            provider_refs=(ProviderRef(provider="sleeper", external_id="123"),),
        ),
        as_of=datetime(2026, 9, 10, 1, 0, tzinfo=UTC),
        teams=(
            Team(team_id="t1", league_id=league_id, display_name="One"),
            Team(team_id="t2", league_id=league_id, display_name="Two"),
        ),
        team_states=(TeamState(team_id="t1", roster=()), TeamState(team_id="t2", roster=())),
        players=(),
        player_states=(),
    )


class NoopBehavioralCoordinator:
    def __init__(self) -> None:
        self.starts = 0

    def start(self, **kwargs):
        self.starts += 1


def test_restart_restore_plus_matching_probe_skips_full_sleeper_reload() -> None:
    persistence = MemoryPersistence()
    state = _league_state()
    persist_runtime_snapshot(
        persistence,
        user_id="jimmy",
        league_state=state,
        selected_team_id="t1",
    )

    now = datetime.now(UTC)
    probe = SleeperSyncProbe(
        league_external_id="123",
        captured_at=now,
        season=2026,
        week=3,
        fingerprint="unchanged-league",
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
                "last_full_refresh_at": now.isoformat(),
            },
            synced_at=now,
            source_updated_at=probe.captured_at,
        )
    )

    # A new runtime instance represents a hosted-process restart. It starts empty and
    # must recover the league from durable storage before revalidation begins.
    runtime = PersistentPrivateBetaRuntimeStore(persistence)
    full_loader_calls = 0

    def full_state_loader(league_external_id: str) -> LeagueState:
        nonlocal full_loader_calls
        full_loader_calls += 1
        raise AssertionError("unchanged restored league must not trigger full Sleeper reload")

    behavioral = NoopBehavioralCoordinator()
    app = FastAPI()
    app.dependency_overrides[require_beta_user] = lambda: "jimmy"
    coordinator = install_hosted_connect_routes(
        app,
        runtime_store=runtime,
        state_loader=full_state_loader,
        behavioral_coordinator=behavioral,
        persistence_store=persistence,
        sync_probe_loader=lambda league_external_id: probe,
        full_refresh_seconds=3600,
    )

    restored = runtime.get("jimmy")
    assert restored.league_state == state
    assert restored.selected_team_id == "t1"

    response = TestClient(app).post(
        "/api/connect/sleeper/background/refresh",
        json={"league_external_id": "123"},
    )
    assert response.status_code == 200

    deadline = monotonic() + 2
    current = coordinator.current("jimmy")
    while monotonic() < deadline and current is not None and current.status in {
        LeagueConnectStatus.QUEUED,
        LeagueConnectStatus.RUNNING,
    }:
        sleep(0.01)
        current = coordinator.current("jimmy")

    assert current is not None
    assert current.status == LeagueConnectStatus.COMPLETED
    assert full_loader_calls == 0
    assert behavioral.starts == 0
    assert runtime.get("jimmy").league_state == state


def test_durable_simulation_cache_version_matches_current_authoritative_result() -> None:
    assert (
        LiveSimulationAnalyticsResult.model_fields["model_version"].default
        == SIMULATION_MODEL_VERSION
    )
