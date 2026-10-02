from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from fsffl.product.background_jobs import (
    IntelligenceJobPhase,
    IntelligenceJobStatus,
)
import fsffl.product.state_first_acceptance as acceptance_module
from fsffl.product.state_first_acceptance import (
    FSFFL_ACCEPTANCE_LEAGUE,
    StateFirstAcceptanceError,
    _probe_surface_during_simulation,
    resolve_staged_acceptance_user,
    stage_restored_refresh_partial_acceptance,
)


def test_staged_acceptance_user_never_reuses_source_identity() -> None:
    assert resolve_staged_acceptance_user(
        source_user_id="jimmy",
        configured_acceptance_user_id="jimmy",
    ) == "runtime-availability-production-acceptance"
    assert resolve_staged_acceptance_user(
        source_user_id="jimmy",
        configured_acceptance_user_id="isolated-acceptance",
    ) == "isolated-acceptance"


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


@dataclass(frozen=True)
class _FakeValue:
    league_state_id: str


@dataclass(frozen=True)
class _FakeState:
    as_of: datetime

    @property
    def league(self):
        return SimpleNamespace(league_id=f"sleeper:{FSFFL_ACCEPTANCE_LEAGUE}")

    @property
    def state_id(self) -> str:
        return f"state:{self.as_of.isoformat()}"

    def model_copy(self, *, update):
        return replace(self, **update)


class _FakeAcceptanceStore:
    def __init__(self, source):
        self.source = source
        self.contexts = {"jimmy": source}
        self.durable = {}
        self.reset_count = 0

    def wait_for_checkpoint(self, _user_id, *, timeout):
        assert timeout == 180.0
        return True

    def reset_in_memory_for_acceptance_restore(self, user_id):
        self.contexts.pop(user_id, None)
        self.reset_count += 1

    def restore_user(self, user_id):
        if user_id == "jimmy":
            return self.source
        if user_id not in self.contexts:
            self.contexts[user_id] = self.durable[user_id]
        return self.contexts[user_id]

    def set_league_state(self, user_id, league_state):
        prior = self.contexts.get(user_id)
        served = None
        if (
            prior is not None
            and prior.league_state is not None
            and prior.forecast_evidence is not None
            and prior.simulation_analytics is not None
            and prior.value_evidence is not None
        ):
            served = SimpleNamespace(
                league_state_id=prior.league_state.state_id,
                publication_generation_id=prior.publication_generation_id,
            )
        context = SimpleNamespace(
            user_id=user_id,
            league_state=league_state,
            selected_team_id=(prior.selected_team_id if prior is not None else None),
            forecast_evidence=None,
            simulation_analytics=None,
            value_evidence=None,
            served_intelligence=served,
            publication_generation_id=None,
        )
        self.contexts[user_id] = context
        self.durable[user_id] = context
        return context

    def select_team(self, user_id, team_id):
        context = self.contexts[user_id]
        updated = SimpleNamespace(**{**context.__dict__, "selected_team_id": team_id})
        self.contexts[user_id] = updated
        self.durable[user_id] = updated
        return updated

    def set_intelligence_bundle(
        self,
        user_id,
        *,
        league_state,
        forecast_evidence,
        simulation_analytics,
        value_evidence,
    ):
        context = self.contexts[user_id]
        updated = SimpleNamespace(
            **{
                **context.__dict__,
                "league_state": league_state,
                "forecast_evidence": forecast_evidence,
                "simulation_analytics": simulation_analytics,
                "value_evidence": value_evidence,
            }
        )
        self.contexts[user_id] = updated
        self.durable[user_id] = updated
        return updated

    def bind_publication_generation_id(self, user_id, publication_generation_id):
        context = self.contexts[user_id]
        updated = SimpleNamespace(
            **{
                **context.__dict__,
                "publication_generation_id": publication_generation_id,
            }
        )
        self.contexts[user_id] = updated
        self.durable[user_id] = updated
        return updated

    def get(self, user_id):
        return self.contexts[user_id]


def test_acceptance_staging_reproduces_cold_partial_restore_without_touching_source(
    monkeypatch,
) -> None:
    s0 = _FakeState(datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc))
    source = SimpleNamespace(
        user_id="jimmy",
        league_state=s0,
        selected_team_id="team-a",
        forecast_evidence=object(),
        simulation_analytics=object(),
        value_evidence=_FakeValue(league_state_id=s0.state_id),
        served_intelligence=None,
        publication_generation_id="source-generation",
    )
    store = _FakeAcceptanceStore(source)

    monkeypatch.setattr(
        acceptance_module,
        "league_material_fingerprint",
        lambda _state: "same-material",
    )
    replayed_forecast = object()
    monkeypatch.setattr(
        acceptance_module,
        "replay_live_forecast_evidence_for_state",
        lambda _state, _forecast: replayed_forecast,
    )

    cloned = []

    def clone(source_user_id, acceptance_user_id, source_context):
        cloned.append((source_user_id, acceptance_user_id, source_context.state_id if hasattr(source_context, "state_id") else source_context.league_state.state_id))
        return "presentation-generation"

    result = stage_restored_refresh_partial_acceptance(
        store=store,
        source_user_id="jimmy",
        acceptance_user_id="acceptance",
        clone_presentation_snapshot=clone,
    )

    restored = store.get("acceptance")
    assert source.simulation_analytics is not None
    assert restored.league_state.state_id != s0.state_id
    assert restored.forecast_evidence is replayed_forecast
    assert restored.simulation_analytics is None
    assert restored.value_evidence.league_state_id == restored.league_state.state_id
    assert restored.served_intelligence.league_state_id == s0.state_id
    assert store.reset_count == 2
    assert result["served_state_id"] == s0.state_id
    assert result["target_state_id"] == restored.league_state.state_id
    assert cloned[0][:2] == ("jimmy", "acceptance")
