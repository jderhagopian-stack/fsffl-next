from datetime import UTC, datetime
import hashlib

from fastapi.testclient import TestClient

from fsffl.analytics.league import LeagueAnalyticsView, LeagueTeamAnalyticsRow
from fsffl.analytics.models import AnalyticsContext
from fsffl.product.webapp import create_app
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _league_view() -> LeagueAnalyticsView:
    context = AnalyticsContext(
        schema_version="1",
        league_id="l1",
        league_state_id="s1",
        as_of=datetime(2026, 9, 5, tzinfo=UTC),
        generated_at=datetime(2026, 9, 5, 1, tzinfo=UTC),
        lineage=(),
    )
    return LeagueAnalyticsView(
        context=context,
        teams=(
            LeagueTeamAnalyticsRow(
                team_id="a",
                display_name="Alpha",
                player_count=10,
                draft_pick_count=3,
                expected_wins=9.0,
            ),
            LeagueTeamAnalyticsRow(
                team_id="b",
                display_name="Beta",
                player_count=10,
                draft_pick_count=4,
                expected_wins=7.0,
            ),
        ),
    )


def _canonical_state() -> LeagueState:
    as_of = datetime(2026, 9, 5, tzinfo=UTC)
    league = League(
        league_id="sleeper:123",
        name="Beta League",
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


def _set_beta_auth(monkeypatch, password: str = "secret") -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "1")
    monkeypatch.setenv("FSFFL_BETA_USERNAME", "jimmy")
    monkeypatch.setenv(
        "FSFFL_BETA_PASSWORD_SHA256",
        hashlib.sha256(password.encode("utf-8")).hexdigest(),
    )


def test_health_is_available_without_beta_auth(monkeypatch) -> None:
    _set_beta_auth(monkeypatch)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_private_shell_requires_credentials_when_enabled(monkeypatch) -> None:
    _set_beta_auth(monkeypatch)
    client = TestClient(create_app())
    assert client.get("/").status_code == 401
    assert client.get("/", auth=("jimmy", "wrong")).status_code == 401
    response = client.get("/", auth=("jimmy", "secret"))
    assert response.status_code == 200
    assert "FSFFL NEXT" in response.text


def test_chart_endpoint_requires_loaded_league_without_external_analytics(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app())
    response = client.get("/api/league/chart?metric=expected_wins")
    assert response.status_code == 409
    assert "No league is loaded" in response.json()["detail"]


def test_chart_endpoint_renders_next7_metric_view(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    view = _league_view()
    client = TestClient(create_app(league_view_provider=lambda: view))
    response = client.get("/api/league/chart?metric=expected_wins")
    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "bar"
    assert [point["label"] for point in payload["series"][0]["points"]] == ["Alpha", "Beta"]
    assert [point["y"] for point in payload["series"][0]["points"]] == [9.0, 7.0]


def test_product_context_reflects_loaded_analytics_state(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    view = _league_view()
    client = TestClient(create_app(league_view_provider=lambda: view))
    payload = client.get("/api/product-context").json()
    assert payload["league_id"] == "l1"
    assert payload["state_id"] == "s1"


def test_connect_sleeper_loads_canonical_state_without_network(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    calls: list[str] = []

    def loader(league_id: str) -> LeagueState:
        calls.append(league_id)
        return _canonical_state()

    client = TestClient(create_app(state_loader=loader))
    response = client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    assert response.status_code == 200
    payload = response.json()
    assert calls == ["123"]
    assert payload["league_id"] == "sleeper:123"
    assert payload["league_name"] == "Beta League"
    assert [team["display_name"] for team in payload["teams"]] == ["Alpha", "Beta"]
    assert payload["state_id"]


def test_loaded_state_immediately_exposes_state_derived_league_chart(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _canonical_state()))
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    response = client.get("/api/league/chart?metric=draft_pick_count")
    assert response.status_code == 200
    payload = response.json()
    assert [point["label"] for point in payload["series"][0]["points"]] == ["Alpha", "Beta"]
    assert [point["y"] for point in payload["series"][0]["points"]] == [0.0, 0.0]
    assert "state" in payload["source_model_versions"] or payload["source_model_versions"]


def test_runtime_status_names_ready_and_waiting_stages(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _canonical_state()))
    assert client.get("/api/intelligence/status").status_code == 409
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    payload = client.get("/api/intelligence/status").json()
    readiness = {item["stage"]: item["readiness"] for item in payload["stages"]}
    assert readiness["state"] == "ready"
    assert readiness["analytics"] == "ready"
    assert readiness["forecast"] == "waiting_for_input"
    assert readiness["value"] == "waiting_for_input"
    assert readiness["team_utility"] == "waiting_for_input"


def test_select_team_requires_loaded_league_and_valid_team(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _canonical_state()))
    assert client.post("/api/select-team", json={"team_id": "a"}).status_code == 422
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    bad = client.post("/api/select-team", json={"team_id": "not-there"})
    assert bad.status_code == 422
    good = client.post("/api/select-team", json={"team_id": "a"})
    assert good.status_code == 200
    assert good.json()["team_id"] == "a"


def test_my_team_exposes_state_only_view_with_missing_evidence_warning(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _canonical_state()))
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    client.post("/api/select-team", json={"team_id": "a"})
    response = client.get("/api/my-team")
    assert response.status_code == 200
    payload = response.json()
    assert payload["team_id"] == "a"
    assert payload["display_name"] == "Alpha"
    assert payload["context"]["warnings"][0]["code"] == "team_runtime_not_enriched"
