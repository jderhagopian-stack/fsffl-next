"""Small real-API journey: canonical assets, partial analysis, bounded search.

Deliberately no Forecast/Simulation artifacts: missing evidence must remain explicit.
No providers, persistence, or production data are used.
"""
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fsffl.product.quick_frontier_routes import install_quick_frontier_routes
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.webapp import create_app, require_beta_user
from fsffl.state.models import League, LeagueRules, LeagueState, Player, PlayerState, Provenance, RosterEntry, Team, TeamState


def test_bilateral_journey_preserves_state_ownership_and_missing_authority(monkeypatch):
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    league = League(league_id="synthetic", name="Synthetic", season=2026,
                   rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()))
    state = LeagueState(
        league=league, as_of=datetime(2026, 9, 5, tzinfo=UTC),
        teams=tuple(Team(team_id=t, league_id=league.league_id, display_name=t) for t in ("a", "b")),
        team_states=tuple(TeamState(team_id=t, roster=(RosterEntry(player_id=p, slot="BENCH"),))
                          for t, p in (("a", "p1"), ("b", "p2"))),
        players=tuple(Player(player_id=p, full_name=p, position="WR") for p in ("p1", "p2")),
        player_states=tuple(PlayerState(player_id=p, as_of=datetime(2026, 9, 5, tzinfo=UTC),
                            provenance=Provenance(source="synthetic", retrieved_at=datetime(2026, 9, 5, tzinfo=UTC), effective_at=datetime(2026, 9, 5, tzinfo=UTC))) for p in ("p1", "p2")),
    )
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state)
    store.select_team("local-beta-user", "a")
    app = create_app(runtime_store=store)
    install_quick_frontier_routes(app, runtime_store=store, require_user=require_beta_user)
    client = TestClient(app)
    browser = client.get("/api/trade-center/browser")
    assert browser.status_code == 200
    assert browser.json()["state_id"] == state.state_id
    package = dict(counterparty_team_id="b", focal_asset_refs=["player:p1"], counterparty_asset_refs=["player:p2"])
    for route in ("analyze", "frontier/quick", "frontier"):
        response = client.post(f"/api/trade-center/{route}", json=package)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["state_id_before"] == state.state_id
        assert result["focal_team_id"] == "a"
        assert result["counterparty_team_id"] == "b"
        if route == "analyze":
            assert not result["availability"]["competitive_outcomes"]
        else:
            assert not result["authority"]["acceptance_probability"]
    simulation = client.post("/api/trade-center/simulate", json=package)
    assert simulation.status_code == 409  # No invented Simulation evidence.
    for route in ("analyze", "frontier/quick", "frontier", "simulate"):
        wrong_owner = {**package, "focal_asset_refs": ["player:p2"]}
        response = client.post(f"/api/trade-center/{route}", json=wrong_owner)
        assert response.status_code == 422
    assert store.get("local-beta-user").league_state == state  # All scenario work is non-mutating.
