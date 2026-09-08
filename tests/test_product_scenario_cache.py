from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fsffl.product.scenario_cache import (
    clear_scenario_cache,
    run_cached_scenario_simulation,
    scenario_cache_status,
)


class _Value:
    def __init__(self, value: str) -> None:
        self.value = value


class _Observation:
    def __init__(self, *, player_id: str = "p1", mean: float = 100.0) -> None:
        self.player_id = player_id
        self.horizon = _Value("season")
        self.metric = _Value("fantasy_points")
        self.as_of = datetime(2026, 9, 7, tzinfo=UTC)
        self.source = "test-source"
        self.model_version = "test-forecast-v1"
        self.mean = mean

    def model_dump_json(self) -> str:
        return f'{{"player_id":"{self.player_id}","mean":{self.mean}}}'


class _Evidence:
    def __init__(self, *, mean: float = 100.0) -> None:
        self.model_version = "test-live-evidence-v1"
        self.successful_source_ids = ("source-a", "source-b")
        self.league_scored_forecasts = (_Observation(mean=mean),)


class _State:
    def __init__(self, state_id: str) -> None:
        self.state_id = state_id


def _result(state_id: str):
    return SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state_id),
        )
    )


def test_exact_scenario_is_simulated_once_then_reused() -> None:
    clear_scenario_cache()
    calls = 0

    def loader(state, evidence):
        nonlocal calls
        calls += 1
        return _result(state.state_id)

    state = _State("state-a")
    evidence = _Evidence()
    first, first_hit = run_cached_scenario_simulation(state, evidence, simulation_loader=loader)
    second, second_hit = run_cached_scenario_simulation(state, evidence, simulation_loader=loader)

    assert first is second
    assert first_hit is False
    assert second_hit is True
    assert calls == 1
    assert scenario_cache_status()["hits"] == 1


def test_changed_state_or_forecast_forces_fresh_authoritative_simulation() -> None:
    clear_scenario_cache()
    calls = 0

    def loader(state, evidence):
        nonlocal calls
        calls += 1
        return _result(state.state_id)

    run_cached_scenario_simulation(_State("state-a"), _Evidence(mean=100.0), simulation_loader=loader)
    run_cached_scenario_simulation(_State("state-b"), _Evidence(mean=100.0), simulation_loader=loader)
    run_cached_scenario_simulation(_State("state-a"), _Evidence(mean=101.0), simulation_loader=loader)

    assert calls == 3
    assert scenario_cache_status()["misses"] == 3


def test_cache_rejects_loader_result_for_wrong_state() -> None:
    clear_scenario_cache()

    def loader(state, evidence):
        return _result("wrong-state")

    try:
        run_cached_scenario_simulation(_State("expected-state"), _Evidence(), simulation_loader=loader)
    except ValueError as exc:
        assert "exact changed LeagueState" in str(exc)
    else:
        raise AssertionError("scenario cache must reject a mismatched Simulation result")


def test_cache_is_bounded_and_is_performance_only() -> None:
    source = scenario_cache_status()
    assert source["max_entries"] == 64
    assert source["authority"] == "performance-only exact-result reuse"
