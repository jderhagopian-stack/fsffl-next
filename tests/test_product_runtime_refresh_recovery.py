import pytest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fsffl.product.runtime import LiveForecastEvidence, PrivateBetaRuntimeStore
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


def _state(as_of: datetime, *, league_id: str = "sleeper:123") -> LeagueState:
    league = League(
        league_id=league_id,
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


def _simulation_for(state: LeagueState):
    return SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state.state_id)
        )
    )


def _value_for(state: LeagueState):
    return SimpleNamespace(league_state_id=state.state_id)


def test_completed_last_good_bundle_survives_partial_refresh_until_atomic_promotion() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    last_good_state = _state(t0)
    refreshed_state = _state(t0 + timedelta(minutes=1))
    old_forecast = _evidence()
    old_simulation = _simulation_for(last_good_state)
    old_value = _value_for(last_good_state)
    store.set_league_state("u", last_good_state)
    store.set_intelligence_bundle(
        "u",
        league_state=last_good_state,
        forecast_evidence=old_forecast,
        simulation_analytics=old_simulation,  # type: ignore[arg-type]
        value_evidence=old_value,  # type: ignore[arg-type]
    )

    new_forecast = _evidence()
    after_forecast = store.set_forecast_evidence(
        "u",
        new_forecast,
        refreshed_league_state=refreshed_state,
    )
    assert after_forecast.league_state == last_good_state
    assert after_forecast.forecast_evidence is old_forecast
    assert after_forecast.simulation_analytics is old_simulation
    assert after_forecast.value_evidence is old_value

    new_simulation = _simulation_for(refreshed_state)
    after_simulation = store.set_simulation_analytics("u", new_simulation)  # type: ignore[arg-type]
    assert after_simulation.league_state == last_good_state
    assert after_simulation.value_evidence is old_value

    new_value = _value_for(refreshed_state)
    promoted = store.set_value_evidence("u", new_value)  # type: ignore[arg-type]
    assert promoted.league_state == refreshed_state
    assert promoted.forecast_evidence is new_forecast
    assert promoted.simulation_analytics is new_simulation
    assert promoted.value_evidence is new_value


def test_failed_partial_refresh_preserves_completed_last_good_bundle() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    last_good_state = _state(t0)
    refreshed_state = _state(t0 + timedelta(minutes=1))
    old_forecast = _evidence()
    old_simulation = _simulation_for(last_good_state)
    old_value = _value_for(last_good_state)
    store.set_league_state("u", last_good_state)
    store.set_intelligence_bundle(
        "u",
        league_state=last_good_state,
        forecast_evidence=old_forecast,
        simulation_analytics=old_simulation,  # type: ignore[arg-type]
        value_evidence=old_value,  # type: ignore[arg-type]
    )

    store.set_forecast_evidence(
        "u",
        _evidence(),
        refreshed_league_state=refreshed_state,
    )
    # Model a failed Simulation followed by an independently successful Value build.
    retained = store.set_value_evidence("u", _value_for(refreshed_state))  # type: ignore[arg-type]

    assert retained.league_state == last_good_state
    assert retained.forecast_evidence is old_forecast
    assert retained.simulation_analytics is old_simulation
    assert retained.value_evidence is old_value


def test_cross_league_switch_invalidates_old_refresh_generation() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    old_state = _state(t0, league_id="sleeper:123")
    new_state = _state(t0 + timedelta(minutes=1), league_id="sleeper:456")
    refreshed_old_state = _state(t0 + timedelta(minutes=2), league_id="sleeper:123")

    store.set_league_state("u", old_state)
    old_generation = store.league_generation("u")
    store.set_league_state("u", new_state)

    assert store.league_generation("u") > old_generation
    with pytest.raises(ValueError, match="different loaded league"):
        store.set_forecast_evidence(
            "u",
            _evidence(),
            refreshed_league_state=refreshed_old_state,
        )
    assert store.get("u").league_state == new_state


def test_same_league_provider_revalidation_cannot_demote_complete_bundle() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    last_good_state = _state(t0)
    newer_provider_state = _state(t0 + timedelta(minutes=5))
    old_forecast = _evidence()
    old_simulation = _simulation_for(last_good_state)
    old_value = _value_for(last_good_state)
    store.set_league_state("u", last_good_state)
    store.set_intelligence_bundle(
        "u",
        league_state=last_good_state,
        forecast_evidence=old_forecast,
        simulation_analytics=old_simulation,  # type: ignore[arg-type]
        value_evidence=old_value,  # type: ignore[arg-type]
    )

    retained = store.set_league_state("u", newer_provider_state)

    assert retained.league_state == last_good_state
    assert retained.forecast_evidence is old_forecast
    assert retained.simulation_analytics is old_simulation
    assert retained.value_evidence is old_value
    assert retained.intelligence_reused is True
