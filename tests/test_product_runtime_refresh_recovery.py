from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fsffl.product.runtime import LiveForecastEvidence, PrivateBetaRuntimeStore
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _state(as_of: datetime) -> LeagueState:
    league = League(
        league_id="sleeper:123",
        name="Recovery League",
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
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(),
        player_states=(),
    )


def _evidence() -> LiveForecastEvidence:
    return LiveForecastEvidence(
        raw_forecasts=(),
        league_scored_forecasts=(),
        successful_source_ids=("test",),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=object(),  # type: ignore[arg-type]
    )


def test_same_league_reconnect_cannot_split_one_intelligence_refresh() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    initial = _state(t0)
    refresh_state = _state(t0 + timedelta(minutes=1))
    reconnect_state = _state(t0 + timedelta(minutes=2))

    store.set_league_state("u", initial)
    evidence = _evidence()
    store.set_forecast_evidence("u", evidence, refreshed_league_state=refresh_state)

    # Session recovery reconnects the same league while Simulation is still running.
    store.set_league_state("u", reconnect_state)
    assert store.get("u").forecast_evidence is None

    simulation = SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=refresh_state.state_id)
        )
    )
    store.set_simulation_analytics("u", simulation)  # type: ignore[arg-type]
    recovered = store.get("u")
    assert recovered.league_state == refresh_state
    assert recovered.forecast_evidence is evidence
    assert recovered.simulation_analytics is simulation

    value = SimpleNamespace(league_state_id=refresh_state.state_id)
    store.set_value_evidence("u", value)  # type: ignore[arg-type]
    completed = store.get("u")
    assert completed.league_state == refresh_state
    assert completed.forecast_evidence is evidence
    assert completed.simulation_analytics is simulation
    assert completed.value_evidence is value
