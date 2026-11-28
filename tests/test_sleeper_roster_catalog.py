from dataclasses import asdict, replace
from time import monotonic, sleep
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from fsffl.product.hosted_connect import install_hosted_connect_routes
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.product.runtime import default_sleeper_state_loader
from fsffl.product.trade_center_view import build_trade_center_browser_view
from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.providers.sleeper import IncompleteSleeperRosterCatalog, SleeperNormalizer
from fsffl.providers.sleeper_live import SleeperLiveSource
from tests.test_persistent_runtime_restore import MemoryPersistence
from tests.test_sleeper_normalizer import AS_OF, bundle


@pytest.mark.parametrize("row", [None, {}, {"position": "  "}])
def test_unresolved_rostered_position_fails_before_state_creation(row):
    source = bundle()
    players = dict(source.players, p4=row)
    with pytest.raises(IncompleteSleeperRosterCatalog, match="rostered player ID p4"):
        SleeperNormalizer().normalize(replace(source, players=players), as_of=AS_OF)


def test_explicitly_unsupported_position_keeps_existing_coverage():
    source = bundle()
    players = dict(source.players, p4={"position": "LB"})
    state = SleeperNormalizer().normalize(replace(source, players=players), as_of=AS_OF)
    assert {entry.player_id for team in state.team_states for entry in team.roster} == {
        "sleeper:player:p1", "sleeper:player:p2", "sleeper:player:p3",
    }


def test_incomplete_catalog_on_connect_and_refresh_then_valid_roster_move(monkeypatch):
    source = bundle()
    payload = asdict(source)
    del payload["players"]["p4"]

    def fetch_latest(self, *, league_external_id):
        return ProviderSnapshot("sleeper", league_external_id, AS_OF, payload)

    monkeypatch.setattr(SleeperLiveSource, "fetch_latest", fetch_latest)
    db = MemoryPersistence()
    store = PersistentPrivateBetaRuntimeStore(db)
    app = FastAPI()
    downstream = Mock()
    install_hosted_connect_routes(
        app, runtime_store=store, state_loader=default_sleeper_state_loader,
        behavioral_coordinator=downstream,
    )
    client = TestClient(app)
    path = "/api/connect/sleeper/background"
    user_id = "local-beta-user"
    team_id = "sleeper:123:team:2"

    def run(action):
        response = client.post(path + action, json={"league_external_id": "123"})
        assert response.status_code == 200
        deadline = monotonic() + 5
        while monotonic() < deadline:
            job = client.get(path + "/current").json()
            if job["status"] in {"completed", "failed"}:
                return job
            sleep(0.01)
        pytest.fail("Background import did not finish")

    def restored_assets():
        runtime = PersistentPrivateBetaRuntimeStore(db).restore_user(user_id)
        assert runtime.selected_team_id == team_id
        view = build_trade_center_browser_view(runtime.league_state, focal_team_id=team_id)
        assets = {asset.player_id for asset in view.focal_team.assets if asset.player_id}
        return runtime.league_state.state_id, assets

    first = run("")
    assert first["status"] == "failed" and "rostered player ID p4" in first["message"]
    assert store.get(user_id).league_state is None and db.league is None
    downstream.start.assert_not_called()

    payload["players"]["p4"] = source.players["p4"]
    assert run("")["status"] == "completed"
    store.select_team(user_id, team_id)
    assert store.wait_for_managed_team_checkpoint(user_id, team_id=team_id)
    verified = restored_assets()
    assert verified[1] == {"sleeper:player:p3", "sleeper:player:p4"}

    del payload["players"]["p4"]
    failure = run("/refresh")
    assert failure["status"] == "failed" and "rostered player ID p4" in failure["message"]
    assert "Stored league data remains available" in failure["message"]
    assert store.get(user_id).league_state.state_id == verified[0]
    assert restored_assets() == verified
    downstream.start.assert_called_once()

    # Sleeper now records an actual drop. Missing unrostered metadata is harmless.
    payload["rosters"][1]["players"].remove("p4")
    payload["rosters"][1]["taxi"].remove("p4")
    assert run("/refresh")["status"] == "completed"
    assert store.wait_for_checkpoint(user_id)
    updated, assets = restored_assets()
    assert updated != verified[0] and assets == {"sleeper:player:p3"}
