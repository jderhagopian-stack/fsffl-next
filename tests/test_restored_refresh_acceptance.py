from __future__ import annotations

from types import SimpleNamespace

import pytest

from fsffl.product.background_jobs import (
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
from fsffl.product.state_first_acceptance import (
    StateFirstAcceptanceError,
    _probe_surface_during_simulation,
)


def test_restored_refresh_probes_foreground_surfaces_during_simulation() -> None:
    job = SimpleNamespace(
        job_id="job-exact",
        status=IntelligenceJobStatus.RUNNING,
        phase=IntelligenceJobPhase.RUNNING_SIMULATION,
    )
    jobs = SimpleNamespace(current=lambda _user_id: job)
    store = SimpleNamespace(get=lambda _user_id: "published-runtime")
    calls: list[tuple[str, object]] = []

    def surface_probe(label: str, runtime: object) -> dict[str, object]:
        calls.append((label, runtime))
        return {"readiness_status": "rebuilding"}

    result = _probe_surface_during_simulation(
        jobs=jobs,
        user_id="jimmy",
        job_id="job-exact",
        surface_probe=surface_probe,
        store=store,
        timeout_seconds=0.1,
    )

    assert result == {"readiness_status": "rebuilding"}
    assert calls == [("restored_refresh_during_simulation", "published-runtime")]


def test_restored_refresh_requires_foreground_probe_before_job_finishes() -> None:
    job = SimpleNamespace(
        job_id="job-exact",
        status=IntelligenceJobStatus.COMPLETED,
        phase=IntelligenceJobPhase.COMPLETED,
    )
    jobs = SimpleNamespace(current=lambda _user_id: job)

    with pytest.raises(StateFirstAcceptanceError, match="did not expose active Simulation"):
        _probe_surface_during_simulation(
            jobs=jobs,
            user_id="jimmy",
            job_id="job-exact",
            surface_probe=lambda _label, _runtime: {},
            store=SimpleNamespace(get=lambda _user_id: None),
            timeout_seconds=0.1,
        )
