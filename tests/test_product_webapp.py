from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from types import SimpleNamespace
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


def test_managed_team_view_uses_state_only_during_initial_enrichment(monkeypatch) -> None:
    from fsffl.product.runtime import UserRuntimeContext
    from fsffl.product import webapp as product_webapp

    runtime = UserRuntimeContext(
        user_id="u1",
        league_state=_canonical_state(),
        selected_team_id="a",
        forecast_evidence=object(),  # type: ignore[arg-type]
    )

    def unexpected_forecast_rebuild(_runtime):
        raise AssertionError("foreground read rebuilt forecast-lineup analytics")

    monkeypatch.setattr(
        product_webapp,
        "_forecast_lineup_result",
        unexpected_forecast_rebuild,
    )
    payload = product_webapp._managed_team_view_payload(
        runtime,
        state_only_while_enriching=True,
    )
    assert payload["team_id"] == "a"
    assert payload["context"]["warnings"][0]["code"] == "team_runtime_not_enriched"


def test_home_and_franchise_use_lightweight_read_path_while_job_is_active() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text()
    assert source.count("state_only_while_enriching=enrichment_running") >= 2
    assert 'current_job.status.value in {"queued", "running"}' in source


def test_failed_forecast_reports_exact_blocked_stage_and_keeps_state_usable(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")

    def failed_forecast(_state):
        raise RuntimeError("forecast source gate")

    client = TestClient(
        create_app(
            state_loader=lambda _: _canonical_state(),
            forecast_loader=failed_forecast,
        )
    )
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    client.post("/api/select-team", json={"team_id": "a"})
    started = client.post("/api/intelligence/jobs")
    assert started.status_code == 200

    deadline = monotonic() + 2
    status_payload = None
    while monotonic() < deadline:
        status_payload = client.get("/api/intelligence/status").json()
        if status_payload["job"]["status"] == "failed":
            break
        sleep(0.01)

    assert status_payload is not None
    assert status_payload["job"]["status"] == "failed"
    assert status_payload["job"]["failure_phase"] == "building_forecasts"
    assert status_payload["blocked_stage"] == "forecast"
    assert status_payload["served_state"]["league_id"] == "sleeper:123"
    assert status_payload["served_state"]["selected_team_id"] == "a"
    assert status_payload["served_state"]["roster_usable"] is True
    readiness = {item["stage"]: item for item in status_payload["stages"]}
    assert readiness["state"]["readiness"] == "ready"
    assert readiness["analytics"]["readiness"] == "ready"
    assert readiness["forecast"]["readiness"] == "blocked"
    assert "roster State remains usable" in readiness["forecast"]["message"]

    team = client.get("/api/my-team")
    assert team.status_code == 200
    assert team.json()["team_id"] == "a"



def test_partial_forecast_job_completes_without_simulation_and_keeps_forecast_visible(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state = _canonical_state()
    observation = SimpleNamespace(as_of=state.as_of)
    family = SimpleNamespace(
        model_dump=lambda mode="json": {
            "family": "kicker",
            "status": "UNSUPPORTED",
            "supported_rule_stats": [],
            "provisional_rule_stats": [],
            "omitted_rule_stats": ["fgm_50p"],
            "reason_codes": ["separate_k_dst_forecast_authority_required"],
            "blocks_full_downstream_authority": True,
        }
    )
    runtime_result = SimpleNamespace(
        partial_fantasy_point_forecasts=(),
        family_coverage=(family,),
        simulation_authority_blockers=(
            "separate_k_dst_forecast_authority_required",
        ),
        model_version="fixture-shared-forecast-v1",
        evaluation_as_of=state.as_of,
    )
    evidence = SimpleNamespace(
        raw_forecasts=(observation,),
        league_scored_forecasts=(),
        successful_source_ids=("provider-a", "provider-b"),
        failed_sources=(),
        uncertainty_ready=False,
        runtime_result=runtime_result,
        evidence_basis="live_full_season",
        model_version="fixture-evidence-v1",
    )
    value = SimpleNamespace(
        league_state_id=state.state_id,
        estimates=(),
        successful_source_ids=(),
        coverage="unavailable",
        fsffl_cardinal_values=(),
        cardinal_player_coverage="unavailable",
    )
    simulation_calls = []

    def should_not_simulate(*args, **kwargs):
        simulation_calls.append((args, kwargs))
        raise AssertionError("partial Forecast must not be silently promoted to Simulation")

    client = TestClient(
        create_app(
            state_loader=lambda _: state,
            forecast_loader=lambda _state: evidence,
            simulation_loader=should_not_simulate,
            value_loader=lambda _state: value,
        )
    )
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    started = client.post("/api/intelligence/jobs")
    assert started.status_code == 200

    deadline = monotonic() + 2
    current = None
    while monotonic() < deadline:
        current = client.get("/api/intelligence/jobs/current").json()
        if current["status"] == "completed":
            break
        sleep(0.01)

    assert current is not None
    assert current["status"] == "completed"
    assert "Forecast and current Value evidence are ready" in current["message"]
    assert "Simulation remains unavailable" in current["message"]
    assert "separate_k_dst_forecast_authority_required" in current["message"]
    assert simulation_calls == []
    assert current["forecast_ready"] is True
    assert current["forecast_raw_observation_count"] == 1
    assert current["simulation_ready"] is False
    assert current["value_ready"] is False

    status_payload = client.get("/api/intelligence/status").json()
    assert status_payload["forecast_raw_observation_count"] == 1
    assert status_payload["forecast_simulation_blockers"] == [
        "separate_k_dst_forecast_authority_required"
    ]
    readiness = {
        item["stage"]: item
        for item in status_payload["stages"]
    }
    assert readiness["forecast"]["readiness"] == "ready"
    assert readiness["team_utility"]["readiness"] == "waiting_for_input"

    coverage = client.get("/api/forecast/current/coverage")
    assert coverage.status_code == 200
    payload = coverage.json()
    assert payload["raw_observation_count"] == 1
    assert payload["authoritative_scored_count"] == 0
    assert payload["simulation_authority_blockers"] == [
        "separate_k_dst_forecast_authority_required"
    ]



def _full_runtime_fixture(state: LeagueState):
    observation = SimpleNamespace(as_of=state.as_of)
    runtime_result = SimpleNamespace(
        partial_fantasy_point_forecasts=(),
        family_coverage=(),
        simulation_authority_blockers=(),
        evaluation_as_of=state.as_of,
    )
    evidence = SimpleNamespace(
        raw_forecasts=(observation,),
        league_scored_forecasts=(observation,),
        successful_source_ids=("provider-a", "provider-b"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=runtime_result,
        evidence_basis="live_full_season",
        model_version="fixture-full-evidence-v1",
    )
    simulation = SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state.state_id)
        ),
        simulation_result=SimpleNamespace(simulation_count=50_000),
        team_views=(),
    )
    value = SimpleNamespace(
        league_state_id=state.state_id,
        estimates=(object(),),
        successful_source_ids=("market-a",),
        coverage=1.0,
        fsffl_cardinal_values=(),
        cardinal_player_coverage=0.0,
        pick_variant_market_values=(),
    )
    return evidence, simulation, value


def test_manual_refresh_syncs_state_before_any_intelligence_loader(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    initial = _canonical_state()
    synced = initial.model_copy(
        update={"as_of": datetime(2026, 9, 6, tzinfo=UTC)}
    )
    states = [initial, synced]
    loader_states: list[tuple[str, str]] = []

    def state_loader(_league_id: str) -> LeagueState:
        return states.pop(0)

    def forecast_loader(state: LeagueState):
        loader_states.append(("forecast", state.state_id))
        return _full_runtime_fixture(state)[0]

    def simulation_loader(state: LeagueState, _evidence):
        loader_states.append(("simulation", state.state_id))
        return _full_runtime_fixture(state)[1]

    def value_loader(state: LeagueState):
        loader_states.append(("value", state.state_id))
        return _full_runtime_fixture(state)[2]

    client = TestClient(
        create_app(
            state_loader=state_loader,
            forecast_loader=forecast_loader,
            simulation_loader=simulation_loader,
            value_loader=value_loader,
        )
    )
    connected = client.post(
        "/api/connect/sleeper",
        json={"league_external_id": "123"},
    )
    assert connected.status_code == 200
    assert connected.json()["state_id"] == initial.state_id

    started = client.post("/api/intelligence/jobs")
    assert started.status_code == 200

    deadline = monotonic() + 2
    current = None
    while monotonic() < deadline:
        current = client.get("/api/intelligence/jobs/current").json()
        if current["status"] == "completed":
            break
        sleep(0.01)

    assert current is not None
    assert current["status"] == "completed"
    assert current["state_id"] == synced.state_id
    assert loader_states == [
        ("forecast", synced.state_id),
        ("simulation", synced.state_id),
        ("value", synced.state_id),
    ]


def test_exact_state_reuse_skips_rebuild_loaders(monkeypatch) -> None:
    from fsffl.product.runtime import PrivateBetaRuntimeStore

    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state = _canonical_state()
    evidence, simulation, value = _full_runtime_fixture(state)

    class ReuseStore(PrivateBetaRuntimeStore):
        def restore_exact_state_intelligence(self, user_id: str):
            current = self.get(user_id)
            assert current.league_state is not None
            assert current.league_state.state_id == state.state_id
            restored = self.set_intelligence_bundle(
                user_id,
                league_state=current.league_state,
                forecast_evidence=evidence,
                simulation_analytics=simulation,
                value_evidence=value,
            )
            return restored

    calls: list[str] = []

    def fail_forecast(_state):
        calls.append("forecast")
        raise AssertionError("exact-state Forecast should be reused")

    def fail_simulation(_state, _evidence):
        calls.append("simulation")
        raise AssertionError("exact-state Simulation should be reused")

    def fail_value(_state):
        calls.append("value")
        raise AssertionError("exact-state Value should be reused")

    client = TestClient(
        create_app(
            runtime_store=ReuseStore(),
            state_loader=lambda _league_id: state,
            forecast_loader=fail_forecast,
            simulation_loader=fail_simulation,
            value_loader=fail_value,
        )
    )
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    started = client.post("/api/intelligence/jobs")
    assert started.status_code == 200

    deadline = monotonic() + 2
    current = None
    while monotonic() < deadline:
        current = client.get("/api/intelligence/jobs/current").json()
        if current["status"] == "completed":
            break
        sleep(0.01)

    assert current is not None
    assert current["status"] == "completed"
    assert "reused for this exact State" in current["message"]
    assert current["forecast_ready"] is True
    assert current["simulation_ready"] is True
    assert current["value_ready"] is True
    assert calls == []
