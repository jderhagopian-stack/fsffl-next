import pytest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
)
from fsffl.product.runtime import LiveForecastEvidence, PrivateBetaRuntimeStore
from fsffl.product.persistent_runtime import PersistentPrivateBetaRuntimeStore
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    ScoringRule,
    Team,
    TeamState,
)


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


def _evidence(*, uncertainty_ready: bool = True) -> LiveForecastEvidence:
    return LiveForecastEvidence(
        raw_forecasts=(),
        league_scored_forecasts=(),
        successful_source_ids=("test",),
        failed_sources=(),
        uncertainty_ready=uncertainty_ready,
        runtime_result=object(),  # type: ignore[arg-type]
    )


def test_newer_same_league_state_supersedes_inflight_result_without_split() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    initial = _state(t0)
    refresh_state = _state(t0 + timedelta(minutes=1))
    reconnect_state = _state(t0 + timedelta(minutes=2))

    store.set_league_state("u", initial)
    evidence = _evidence()
    store.set_forecast_evidence("u", evidence, refreshed_league_state=refresh_state)

    # A newer State identity supersedes the pending build. Hosted orchestration
    # normally coalesces this case, but runtime safety still rejects an old result.
    store.set_league_state("u", reconnect_state)
    simulation = SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=refresh_state.state_id)
        )
    )
    with pytest.raises(ValueError, match="matching league and forecast evidence"):
        store.set_simulation_analytics("u", simulation)  # type: ignore[arg-type]
    assert store.get("u").league_state == reconnect_state


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

    advanced = store.set_league_state("u", refreshed_state)
    assert advanced.league_state == refreshed_state
    assert advanced.simulation_analytics is None
    assert advanced.value_evidence is None
    assert advanced.served_intelligence is not None
    assert advanced.served_intelligence.league_state == last_good_state
    assert advanced.served_intelligence.simulation_analytics is old_simulation
    assert advanced.served_intelligence.value_evidence is old_value

    new_forecast = _evidence()
    after_forecast = store.set_forecast_evidence(
        "u",
        new_forecast,
        refreshed_league_state=refreshed_state,
    )
    assert after_forecast.league_state == refreshed_state
    assert after_forecast.served_intelligence is not None

    new_simulation = _simulation_for(refreshed_state)
    after_simulation = store.set_simulation_analytics("u", new_simulation)  # type: ignore[arg-type]
    assert after_simulation.league_state == refreshed_state
    assert after_simulation.value_evidence is None
    assert after_simulation.served_intelligence is not None

    new_value = _value_for(refreshed_state)
    promoted = store.set_value_evidence("u", new_value)  # type: ignore[arg-type]
    assert promoted.league_state == refreshed_state
    assert promoted.forecast_evidence is new_forecast
    assert promoted.simulation_analytics is new_simulation
    assert promoted.value_evidence is new_value
    assert promoted.served_intelligence is None


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

    store.set_league_state("u", refreshed_state)
    store.set_forecast_evidence(
        "u",
        _evidence(),
        refreshed_league_state=refreshed_state,
    )
    # Value may succeed while Simulation remains missing; the new target State
    # stays canonical but last-good remains presentation-available.
    retained = store.set_value_evidence("u", _value_for(refreshed_state))  # type: ignore[arg-type]

    assert retained.league_state == refreshed_state
    assert retained.simulation_analytics is None
    assert retained.value_evidence is not None
    assert retained.served_intelligence is not None
    assert retained.served_intelligence.league_state == last_good_state
    assert retained.served_intelligence.simulation_analytics is old_simulation
    assert retained.served_intelligence.value_evidence is old_value


def test_stable_partial_target_atomically_promotes_without_simulation() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    old_state = _state(t0)
    target = _state(t0 + timedelta(minutes=1))
    store.set_league_state("u", old_state)
    store.set_intelligence_bundle(
        "u",
        league_state=old_state,
        forecast_evidence=_evidence(),
        simulation_analytics=_simulation_for(old_state),  # type: ignore[arg-type]
        value_evidence=_value_for(old_state),  # type: ignore[arg-type]
    )
    store.set_league_state("u", target)
    partial = _evidence(uncertainty_ready=False)
    store.set_forecast_evidence("u", partial, refreshed_league_state=target)
    promoted = store.set_value_evidence("u", _value_for(target))  # type: ignore[arg-type]

    assert promoted.league_state == target
    assert promoted.forecast_evidence is partial
    assert promoted.simulation_analytics is None
    assert promoted.value_evidence is not None
    assert promoted.served_intelligence is None


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


def test_same_league_provider_state_advances_before_downstream_reconciliation() -> None:
    store = PersistentPrivateBetaRuntimeStore(persistence_store=None)
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
    store._last_good_guard_users.add("u")

    current = store.set_league_state("u", newer_provider_state)

    assert current.league_state == newer_provider_state
    assert current.simulation_analytics is None
    assert current.value_evidence is None
    # Compatible raw Forecast may be reused, but old exact-State downstream
    # outputs may not masquerade as current.
    assert current.forecast_evidence is old_forecast
    assert current.served_intelligence is not None
    assert current.served_intelligence.league_state == last_good_state
    assert current.served_intelligence.simulation_analytics is old_simulation



def test_same_league_state_change_advances_job_generation_but_exact_state_reuse_does_not() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    first = _state(t0)
    second = _state(t0 + timedelta(minutes=1))

    store.set_league_state("u-generation", first)
    after_first = store.league_generation("u-generation")
    store.set_league_state("u-generation", first)
    assert store.league_generation("u-generation") == after_first

    store.set_league_state("u-generation", second)
    assert store.league_generation("u-generation") == after_first + 1



def _fum_lost_state(as_of: datetime) -> LeagueState:
    state = _state(as_of)
    rules = state.league.rules.model_copy(
        update={"scoring": (ScoringRule(stat="fum_lost", points=-2.0),)}
    )
    return state.model_copy(
        update={"league": state.league.model_copy(update={"rules": rules})}
    )


def _state_bound_fum_lost_evidence(state: LeagueState) -> LiveForecastEvidence:
    return LiveForecastEvidence(
        raw_forecasts=(),
        league_scored_forecasts=(),
        successful_source_ids=("one", "two"),
        failed_sources=(),
        uncertainty_ready=True,
        runtime_result=SimpleNamespace(
            fumbles_lost_supplement_authority_fingerprint="authority",
            fumbles_lost_supplement_model_version=(
                FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
            ),
            fumbles_lost_supplement_league_state_id=state.state_id,
            model_version="state-bound-fixture-v1",
            evaluation_as_of=state.as_of,
        ),  # type: ignore[arg-type]
    )


def test_same_league_state_advance_never_reuses_fum_lost_supplement_from_prior_state() -> None:
    store = PrivateBetaRuntimeStore()
    t0 = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    first = _fum_lost_state(t0)
    second = _fum_lost_state(t0 + timedelta(minutes=1))
    evidence = _state_bound_fum_lost_evidence(first)

    store.set_league_state("u-fum", first)
    store.set_forecast_evidence(
        "u-fum",
        evidence,
        refreshed_league_state=first,
    )
    exact = store.set_league_state("u-fum", first)
    assert exact.forecast_evidence is evidence

    advanced = store.set_league_state("u-fum", second)
    assert advanced.league_state == second
    assert advanced.forecast_evidence is None
    assert advanced.simulation_analytics is None
    assert advanced.value_evidence is None
