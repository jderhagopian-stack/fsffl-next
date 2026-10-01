from __future__ import annotations

from types import SimpleNamespace

from fsffl.product.background_jobs import (
    IntelligenceJobPhase,
    IntelligenceJobStatus,
    IntelligencePhaseTiming,
)
from fsffl.product.state_first_acceptance import (
    _artifact_identity_snapshot,
    _wait_for_job,
)


def test_acceptance_identity_trace_binds_state_forecast_simulation_and_publication() -> None:
    forecast = SimpleNamespace(
        model_version="next8-live-forecast-evidence-v7",
        evidence_basis="live_full_season",
        successful_source_ids=("provider-a", "provider-b"),
        league_scored_forecasts=(),
    )
    simulation_result = SimpleNamespace(
        model_version="next8-live-simulation-analytics-v8",
        simulation_count=50_000,
        seed=20260905,
        rng_protocol="numpy-pcg64-batched-gauss-v1",
        rng_batch_size=500,
        rng_runtime_version="numpy-2.5.3;python-3.12.10",
        simulation_input_fingerprint="simulation-input-digest",
    )
    simulation = SimpleNamespace(
        simulation_result=simulation_result,
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id="state-exact")
        ),
    )
    runtime = SimpleNamespace(
        league_state=SimpleNamespace(state_id="state-exact"),
        forecast_evidence=forecast,
        simulation_analytics=simulation,
        value_evidence=SimpleNamespace(model_version="value-model-v1"),
        publication_generation_id="publication-exact",
    )

    identity = _artifact_identity_snapshot(runtime)

    assert identity["state_id"] == "state-exact"
    assert identity["forecast"]["state_id"] == "state-exact"
    assert identity["forecast"]["artifact_model_version"]
    assert identity["forecast"]["simulation_input_fingerprint"]
    assert identity["simulation"]["state_id"] == "state-exact"
    assert ":numpy-pcg64-batched-gauss-v1;batch=500;count=50000;" in identity[
        "simulation"
    ]["artifact_model_version"]
    assert identity["simulation"]["input_fingerprint"] == "simulation-input-digest"
    assert identity["simulation"]["simulation_count"] == 50_000
    assert identity["simulation"]["rng_batch_size"] == 500
    assert identity["publication_generation_id"] == "publication-exact"
    assert identity["current_value_model_version"] == "value-model-v1"


def test_acceptance_job_report_preserves_total_and_phase_timings() -> None:
    completed = SimpleNamespace(
        job_id="job-exact",
        status=IntelligenceJobStatus.COMPLETED,
        phase=IntelligenceJobPhase.COMPLETED,
        message="complete",
        error=None,
        league_state_id="state-exact",
        total_elapsed_seconds=12.5,
        phase_timings=(
            IntelligencePhaseTiming(
                phase=IntelligenceJobPhase.RUNNING_SIMULATION,
                elapsed_seconds=4.25,
            ),
        ),
    )
    jobs = SimpleNamespace(current=lambda _user_id: completed)

    result = _wait_for_job(
        jobs=jobs,
        user_id="acceptance-user",
        job_id="job-exact",
        timeout_seconds=1,
        poll_seconds=0,
    )

    assert result["total_elapsed_seconds"] == 12.5
    assert result["phase_timings"] == [
        {"phase": "running_simulation", "elapsed_seconds": 4.25}
    ]
