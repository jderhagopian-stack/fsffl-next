from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fsffl.product.scenario_cache import (
    _durable_key,
    ScenarioComputationStage,
    ScenarioDependencyPlan,
    clear_scenario_cache,
    run_cached_scenario_simulation,
    run_progressive_scenario_simulation,
    scenario_cache_status,
    scenario_stage_simulation_count,
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


def _result(state_id: str, *, simulation_count: int = 50_000):
    return SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state_id),
        ),
        simulation_result=SimpleNamespace(simulation_count=simulation_count),
        scenario_preparation=SimpleNamespace(),
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


def _progressive_loader(calls: list[tuple[str, int]]):
    def canonical(state, evidence):
        calls.append(("confirmation", 50_000))
        return _result(state.state_id, simulation_count=50_000)

    canonical.__fsffl_cache_identity__ = "test-canonical"
    canonical.__fsffl_simulation_model_version__ = "test-simulation-v1"

    def factory(count: int, label: str):
        def loader(state, evidence):
            calls.append((label, count))
            return _result(state.state_id, simulation_count=count)

        loader.__fsffl_cache_identity__ = f"test-{label}-{count}"
        loader.__fsffl_simulation_model_version__ = f"test-simulation-{label}-{count}"
        return loader

    canonical.__fsffl_progressive_loader_factory__ = factory
    return canonical


def test_progressive_stage_counts_and_non_authoritative_labels() -> None:
    clear_scenario_cache()
    calls: list[tuple[str, int]] = []
    loader = _progressive_loader(calls)
    baseline = _result("baseline", simulation_count=50_000)
    plan = ScenarioDependencyPlan(
        affected_team_ids=("a",),
        reusable_team_ids=("b",),
        planned_mode="full_recompute",
        structure_compatible=False,
        forecast_compatible=True,
        baseline_preparation_available=True,
        reasons=("global_simulation_dependency_changed",),
    )

    with patch(
        "fsffl.product.scenario_cache.build_scenario_dependency_plan",
        return_value=plan,
    ):
        screening, _, screening_meta = run_progressive_scenario_simulation(
            _State("baseline"),
            _State("screening"),
            _Evidence(),
            baseline,
            simulation_loader=loader,
            stage=ScenarioComputationStage.SCREENING,
        )
        provisional, _, provisional_meta = run_progressive_scenario_simulation(
            _State("baseline"),
            _State("provisional"),
            _Evidence(),
            baseline,
            simulation_loader=loader,
            stage=ScenarioComputationStage.PROVISIONAL,
        )

    assert scenario_stage_simulation_count(ScenarioComputationStage.SCREENING) == 1_000
    assert scenario_stage_simulation_count(ScenarioComputationStage.PROVISIONAL) == 5_000
    assert scenario_stage_simulation_count(ScenarioComputationStage.CONFIRMATION) == 50_000
    assert screening.simulation_result.simulation_count == 1_000
    assert screening_meta.authoritative is False
    assert screening_meta.deeper_stage_available == ScenarioComputationStage.PROVISIONAL
    assert screening_meta.authority_label == "non_authoritative_scenario_preview"
    assert provisional.simulation_result.simulation_count == 5_000
    assert provisional_meta.authoritative is False
    assert provisional_meta.deeper_stage_available == ScenarioComputationStage.CONFIRMATION
    assert calls == [("screening", 1_000), ("provisional", 5_000)]


def test_progressive_equivalent_stage_loaders_reuse_process_cache() -> None:
    clear_scenario_cache()
    calls: list[tuple[str, int]] = []
    loader = _progressive_loader(calls)
    baseline = _result("baseline", simulation_count=50_000)
    plan = ScenarioDependencyPlan(
        affected_team_ids=("a",),
        reusable_team_ids=("b",),
        planned_mode="full_recompute",
        structure_compatible=False,
        forecast_compatible=True,
        baseline_preparation_available=True,
        reasons=("global_simulation_dependency_changed",),
    )

    with patch(
        "fsffl.product.scenario_cache.build_scenario_dependency_plan",
        return_value=plan,
    ):
        first, first_hit, first_meta = run_progressive_scenario_simulation(
            _State("baseline"),
            _State("same-screening"),
            _Evidence(),
            baseline,
            simulation_loader=loader,
            stage=ScenarioComputationStage.SCREENING,
        )
        second, second_hit, second_meta = run_progressive_scenario_simulation(
            _State("baseline"),
            _State("same-screening"),
            _Evidence(),
            baseline,
            simulation_loader=loader,
            stage=ScenarioComputationStage.SCREENING,
        )

    assert first is second
    assert first_hit is False
    assert second_hit is True
    assert first_meta.authoritative is False
    assert second_meta.execution_mode == "cache_reuse"
    assert calls == [("screening", 1_000)]


def test_progressive_stage_fails_closed_when_loader_cannot_build_preview() -> None:
    clear_scenario_cache()

    def canonical(state, evidence):
        return _result(state.state_id)

    plan = ScenarioDependencyPlan(
        affected_team_ids=("a",),
        reusable_team_ids=("b",),
        planned_mode="full_recompute",
        structure_compatible=False,
        forecast_compatible=True,
        baseline_preparation_available=True,
        reasons=("global_simulation_dependency_changed",),
    )
    with patch(
        "fsffl.product.scenario_cache.build_scenario_dependency_plan",
        return_value=plan,
    ):
        with pytest.raises(
            ValueError,
            match="does not support non-authoritative progressive stages",
        ):
            run_progressive_scenario_simulation(
                _State("baseline"),
                _State("changed"),
                _Evidence(),
                _result("baseline"),
                simulation_loader=canonical,
                stage=ScenarioComputationStage.SCREENING,
            )


def test_no_competitive_dependency_change_reuses_authoritative_canonical_result() -> None:
    clear_scenario_cache()
    calls: list[tuple[str, int]] = []
    loader = _progressive_loader(calls)
    baseline = _result("baseline", simulation_count=50_000)
    plan = ScenarioDependencyPlan(
        affected_team_ids=(),
        reusable_team_ids=("a", "b"),
        planned_mode="reuse_competitive_simulation",
        structure_compatible=True,
        forecast_compatible=True,
        baseline_preparation_available=True,
    )

    def selective_runner(changed_state, evidence, baseline_result, received_plan, reuse):
        assert reuse is True
        assert received_plan == plan
        return _result(changed_state.state_id, simulation_count=50_000)

    loader.__fsffl_selective_runner__ = selective_runner

    with patch(
        "fsffl.product.scenario_cache.build_scenario_dependency_plan",
        return_value=plan,
    ):
        result, _, metadata = run_progressive_scenario_simulation(
            _State("baseline"),
            _State("changed"),
            _Evidence(),
            baseline,
            simulation_loader=loader,
            stage=ScenarioComputationStage.SCREENING,
        )

    assert result.simulation_result.simulation_count == 50_000
    assert metadata.requested_stage == ScenarioComputationStage.SCREENING
    assert metadata.requested_simulation_count == 1_000
    assert metadata.effective_simulation_count == 50_000
    assert metadata.authoritative is True
    assert metadata.execution_mode == "reuse_competitive_simulation"
    assert metadata.deeper_stage_available is None
    assert calls == []


def test_durable_scenario_key_separates_explicit_rng_model_versions() -> None:
    def loader(state, evidence):
        return _result(state.state_id)

    loader.__fsffl_simulation_model_version__ = "sim-python-replay-v1"
    python_key = _durable_key(_State("state-a"), _Evidence(), loader)
    loader.__fsffl_simulation_model_version__ = "sim-numpy-pcg64-v1"
    numpy_key = _durable_key(_State("state-a"), _Evidence(), loader)

    assert python_key.model_version == "sim-python-replay-v1"
    assert numpy_key.model_version == "sim-numpy-pcg64-v1"
    assert python_key.input_fingerprint == numpy_key.input_fingerprint
