from types import SimpleNamespace

from fsffl.product.opportunity_workspace_cache import make_cached_opportunity_workspace


def _runtime(*, state=None, forecast=None, simulation=None, value=None):
    return SimpleNamespace(
        league_state=state or SimpleNamespace(state_id="state-1"),
        selected_team_id="team-1",
        forecast_evidence=forecast or SimpleNamespace(model_version="forecast-v1"),
        simulation_analytics=simulation or SimpleNamespace(model_version="simulation-v1"),
        value_evidence=value or SimpleNamespace(model_version="value-v1"),
    )


def test_exact_runtime_workspace_is_reused_without_rebuilding() -> None:
    calls = []

    def builder(runtime, *, candidate_limit=80, bilateral_evaluation_limit=1):
        calls.append((runtime, candidate_limit, bilateral_evaluation_limit))
        return {"status": "ready", "call": len(calls)}

    cached = make_cached_opportunity_workspace(builder)
    runtime = _runtime()

    first = cached(runtime)
    second = cached(runtime)

    assert first is second
    assert first == {"status": "ready", "call": 1}
    assert len(calls) == 1


def test_replacing_authoritative_evidence_forces_cache_miss() -> None:
    calls = []

    def builder(runtime, *, candidate_limit=80, bilateral_evaluation_limit=1):
        calls.append(runtime)
        return {"call": len(calls)}

    cached = make_cached_opportunity_workspace(builder)
    shared_state = SimpleNamespace(state_id="state-1")
    first_runtime = _runtime(state=shared_state)
    second_runtime = _runtime(
        state=shared_state,
        forecast=first_runtime.forecast_evidence,
        simulation=first_runtime.simulation_analytics,
        value=SimpleNamespace(model_version="value-v1"),
    )

    assert cached(first_runtime)["call"] == 1
    assert cached(second_runtime)["call"] == 2
    assert len(calls) == 2


def test_compute_policy_is_part_of_cache_key() -> None:
    calls = []

    def builder(runtime, *, candidate_limit=80, bilateral_evaluation_limit=1):
        calls.append((candidate_limit, bilateral_evaluation_limit))
        return {"call": len(calls)}

    cached = make_cached_opportunity_workspace(builder)
    runtime = _runtime()

    assert cached(runtime, candidate_limit=80, bilateral_evaluation_limit=1)["call"] == 1
    assert cached(runtime, candidate_limit=40, bilateral_evaluation_limit=1)["call"] == 2
    assert cached(runtime, candidate_limit=80, bilateral_evaluation_limit=0)["call"] == 3
    assert len(calls) == 3
