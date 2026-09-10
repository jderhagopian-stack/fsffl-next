from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fsffl.persistence.memory import InMemoryPersistenceStore
from fsffl.product.hosted_connect import install_hosted_connect_routes
from fsffl.product.persistent_runtime import PersistentBetaRuntimeStore
from fsffl.product.runtime import UserRuntimeContext
from fsffl.product.sync_cursor import SleeperSyncProbe
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
    persistence = InMemoryPersistenceStore()
    runtime = PersistentBetaRuntimeStore(persistence_store=persistence)
    state = _state()
    runtime.set_league_state("jimmy", state)
    runtime.select_team("jimmy", "team:a")

    probe = SleeperSyncProbe(
        league_external_id="123",
        season=2026,
        week=1,
        fingerprint="same-provider-fingerprint",
        observed_at=NOW,
    )
    persistence.put_sleeper_sync_cursor("jimmy", probe.to_record())

    restarted = PersistentBetaRuntimeStore(persistence_store=persistence)
    restored = restarted.restore("jimmy")
    assert restored is not None
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

    from fastapi import FastAPI

    app = FastAPI()
    install_hosted_connect_routes(
        app,
        store=restarted,
        state_loader=full_loader,
        sync_probe_loader=sync_probe_loader,
    )
    client = TestClient(app)
    response = client.post("/api/connect/sleeper/background/refresh", json={"league_id": "123"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    for _ in range(100):
        current = client.get("/api/connect/sleeper/background/current")
        payload = current.json()
        if payload["job_id"] == job_id and payload["status"] in {"succeeded", "failed"}:
            break
    else:
        raise AssertionError("background refresh did not complete")

    assert payload["status"] == "succeeded", payload
    assert probe_calls == ["123"]
    assert full_loader_calls == 0
