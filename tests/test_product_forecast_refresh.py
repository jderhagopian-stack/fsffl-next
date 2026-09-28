from datetime import UTC, datetime
from time import monotonic, sleep

from fastapi.testclient import TestClient

from fsffl.forecast.current_runtime import LiveForecastRuntimeResult
from fsffl.forecast.live_ensemble import LiveEnsembleCoverage
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.product.runtime import LiveForecastEvidence
from fsffl.product.webapp import create_app
from fsffl.state.models import League, LeagueRules, LeagueState, Player, PlayerState, Position, Provenance, RosterEntry, RosterSlot, Team, TeamState

AS_OF = datetime(2026, 9, 5, 20, tzinfo=UTC)


def _state() -> LeagueState:
    provenance = Provenance(source="sleeper", retrieved_at=AS_OF, effective_at=AS_OF)
    league = League(league_id="sleeper:123", name="Beta", season=2026, rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()))
    player = Player(player_id="p1", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL")
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=(Team(team_id="a", league_id=league.league_id, display_name="Alpha"), Team(team_id="b", league_id=league.league_id, display_name="Beta")),
        team_states=(TeamState(team_id="a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.BENCH),)), TeamState(team_id="b", roster=())),
        players=(player,),
        player_states=(PlayerState(player_id="p1", as_of=AS_OF, nfl_team="BAL", provenance=provenance),),
    )


def _forecast() -> ForecastObservation:
    provenance = Provenance(source="fsffl:live_equal_weight", retrieved_at=AS_OF, effective_at=AS_OF)
    return ForecastObservation(
        player_id="p1",
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 3, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=350.0, stddev=20.0),
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v1",
        as_of=AS_OF,
        provenance=provenance,
    )


def _evidence() -> LiveForecastEvidence:
    forecast = _forecast()
    coverage = LiveEnsembleCoverage(
        independent_source_ids=("cbs", "fftoday"),
        excluded_aggregate_source_ids=(),
        active_source_ids=("cbs", "fftoday"),
        observation_count=2,
        minimum_independent_sources=2,
    )
    runtime = LiveForecastRuntimeResult(
        raw_ensemble=(),
        fantasy_point_forecasts=(forecast,),
        coverage=coverage,
        successful_source_ids=("cbs", "fftoday"),
        failed_sources=(),
        evaluation_as_of=AS_OF,
    )
    return LiveForecastEvidence(
        raw_forecasts=(),
        league_scored_forecasts=(forecast,),
        successful_source_ids=("cbs", "fftoday"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=runtime,
    )


def test_refresh_forecasts_does_not_publish_partial_generation_when_downstream_fails(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    client = TestClient(create_app(state_loader=lambda _: _state(), forecast_loader=lambda _: _evidence()))
    client.post("/api/connect/sleeper", json={"league_external_id": "123"})
    client.post("/api/select-team", json={"team_id": "a"})

    refreshed = client.post("/api/intelligence/refresh-forecasts")
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] in {"queued", "running"}

    # Forecast may complete inside the unpublished working generation, but a later
    # downstream failure must not leak that half-built generation to foreground reads.
    deadline = monotonic() + 2
    job = None
    while monotonic() < deadline:
        job = client.get("/api/intelligence/jobs/current").json()
        if job["status"] in {"completed", "failed", "interrupted"}:
            break
        sleep(0.01)
    assert job is not None
    assert job["status"] == "failed"

    context = client.get("/api/product-context").json()
    assert context["forecast_ready"] is False
    assert context["forecast_sources"] == []
    assert context["capability_readiness"]["publication"]["working_generation_active"] is False

    team = client.get("/api/my-team").json()
    assert all(not player["forecasts"] for player in team["players"])
