from datetime import UTC, datetime

from fastapi.testclient import TestClient

from fsffl.analytics.league import LeagueAnalyticsView, LeagueTeamAnalyticsRow
from fsffl.analytics.models import AnalyticsContext
from fsffl.product.webapp import create_app


def _league_view() -> LeagueAnalyticsView:
    context = AnalyticsContext(
        league_id="l1",
        league_state_id="s1",
        as_of=datetime(2026, 9, 5, tzinfo=UTC),
        generated_at=datetime(2026, 9, 5, 1, tzinfo=UTC),
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


def test_health_is_available_without_beta_auth(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "1")
    monkeypatch.setenv("FSFFL_BETA_USERNAME", "jimmy")
    monkeypatch.setenv("FSFFL_BETA_PASSWORD", "secret")
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_private_shell_requires_credentials_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "1")
    monkeypatch.setenv("FSFFL_BETA_USERNAME", "jimmy")
    monkeypatch.setenv("FSFFL_BETA_PASSWORD", "secret")
    client = TestClient(create_app())
    assert client.get("/").status_code == 401
    response = client.get("/", auth=("jimmy", "secret"))
    assert response.status_code == 200
    assert "FSFFL NEXT" in response.text


def test_chart_endpoint_fails_explicitly_without_loaded_league(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app())
    response = client.get("/api/league/chart?metric=expected_wins")
    assert response.status_code == 409
    assert "No league analytics provider" in response.json()["detail"]


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


def test_product_context_reflects_loaded_state(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    view = _league_view()
    client = TestClient(create_app(league_view_provider=lambda: view))
    payload = client.get("/api/product-context").json()
    assert payload["league_id"] == "l1"
    assert payload["state_id"] == "s1"
