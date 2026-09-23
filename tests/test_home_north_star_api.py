from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fsffl.product.webapp import create_app
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _state() -> LeagueState:
    as_of = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
    league = League(
        league_id="sleeper:home-test",
        name="Home Test",
        season=2026,
        rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
    )
    teams = (
        Team(team_id="a", league_id=league.league_id, display_name="Alpha"),
        Team(team_id="b", league_id=league.league_id, display_name="Beta"),
    )
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=teams,
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=(),
        player_states=(),
    )


def test_home_endpoint_consumes_attached_evidence_without_launching_simulation(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    simulation_calls = []

    def forbidden_simulation(*args, **kwargs):
        simulation_calls.append((args, kwargs))
        raise AssertionError("Home must not launch Simulation")

    client = TestClient(
        create_app(
            state_loader=lambda _: _state(),
            simulation_loader=forbidden_simulation,
        )
    )
    client.post("/api/connect/sleeper", json={"league_external_id": "home-test"})
    client.post("/api/select-team", json={"team_id": "a"})

    response = client.get("/api/home")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_version"] == "home-north-star-v1"
    assert payload["managed_team_id"] == "a"
    assert payload["team_view"]["team_id"] == "a"
    assert payload["simulation"]["status"] == "unavailable"
    assert payload["authority"]["market_search_launched"] is False
    assert payload["authority"]["changed_state_simulation_launched"] is False
    assert simulation_calls == []


def test_home_endpoint_fails_closed_without_managed_team(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _state()))
    client.post("/api/connect/sleeper", json={"league_external_id": "home-test"})
    response = client.get("/api/home")
    assert response.status_code == 409
    assert "managed team" in response.json()["detail"].lower()
