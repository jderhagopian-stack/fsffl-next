from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from threading import Thread

from fsffl.product.presentation_continuity import (
    REQUIRED_PRESENTATION_SURFACES,
    PresentationContinuityStore,
)
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.state.models import League, LeagueRules, LeagueState, Team, TeamState


class MemoryPersistence:
    def __init__(self) -> None:
        self.artifacts = []

    def put_artifact(self, record) -> None:
        self.artifacts.append(record)

    def get_reusable_artifact(self, key):
        return next(
            (
                row
                for row in reversed(self.artifacts)
                if row.key == key and row.reusable
            ),
            None,
        )

    def get_latest_reusable_artifact(
        self,
        *,
        artifact_kind,
        scope_kind,
        scope_id,
        model_version,
    ):
        rows = [
            row
            for row in self.artifacts
            if row.reusable
            and row.key.artifact_kind == artifact_kind
            and row.key.scope_kind == scope_kind
            and row.key.scope_id == scope_id
            and row.key.model_version == model_version
        ]
        return max(rows, key=lambda row: row.computed_at) if rows else None


def _state() -> LeagueState:
    league_id = "sleeper:atomic"
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Atomic League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=datetime(2026, 9, 28, 12, 0, tzinfo=UTC),
        teams=(
            Team(team_id="a", league_id=league_id, display_name="Alpha"),
            Team(team_id="b", league_id=league_id, display_name="Beta"),
        ),
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=(),
        player_states=(),
    )


def _forecast(state: LeagueState, label: str):
    return SimpleNamespace(
        raw_forecasts=(),
        league_scored_forecasts=(),
        uncertainty_ready=True,
        runtime_result=SimpleNamespace(simulation_authority_blockers=()),
        model_version=label,
    )


def _simulation(state: LeagueState, label: str):
    return SimpleNamespace(
        league_view=SimpleNamespace(
            context=SimpleNamespace(league_state_id=state.state_id)
        ),
        label=label,
    )


def _value(state: LeagueState, label: str):
    return SimpleNamespace(
        league_state_id=state.state_id,
        estimates=(),
        fsffl_cardinal_values=(),
        pick_variant_market_values=(),
        label=label,
    )


def _published_store():
    state = _state()
    store = PrivateBetaRuntimeStore()
    store.set_league_state("jimmy", state)
    f1 = _forecast(state, "forecast-1")
    s1 = _simulation(state, "simulation-1")
    v1 = _value(state, "value-1")
    store.set_intelligence_bundle(
        "jimmy",
        league_state=state,
        forecast_evidence=f1,
        simulation_analytics=s1,
        value_evidence=v1,
    )
    store.bind_publication_generation_id("jimmy", "generation-1")
    return store, state, f1, s1, v1


def test_same_state_reconciliation_never_mutates_published_generation_incrementally():
    store, state, f1, s1, v1 = _published_store()

    store.begin_working_generation("jimmy", league_state=state)
    f2 = _forecast(state, "forecast-2")
    store.set_forecast_evidence("jimmy", f2)

    published = store.get("jimmy")
    working = store.working_context("jimmy")
    assert published.forecast_evidence is f1
    assert published.simulation_analytics is s1
    assert published.value_evidence is v1
    assert published.publication_generation_id == "generation-1"
    assert working.forecast_evidence is f2
    assert working.simulation_analytics is None
    assert working.value_evidence is None

    s2 = _simulation(state, "simulation-2")
    v2 = _value(state, "value-2")
    store.set_simulation_analytics("jimmy", s2)
    store.set_value_evidence("jimmy", v2)

    # Even a terminal working bundle remains invisible until one publish swap.
    assert store.get("jimmy").publication_generation_id == "generation-1"
    promoted = store.publish_working_generation(
        "jimmy",
        publication_generation_id="generation-2",
    )
    assert promoted.forecast_evidence is f2
    assert promoted.simulation_analytics is s2
    assert promoted.value_evidence is v2
    assert promoted.publication_generation_id == "generation-2"
    assert store.working_generation_active("jimmy") is False


def test_interrupted_working_generation_preserves_prior_publication():
    store, state, f1, s1, v1 = _published_store()
    store.begin_working_generation("jimmy", league_state=state)
    store.set_forecast_evidence("jimmy", _forecast(state, "replacement"))

    restored = store.abort_working_generation("jimmy")

    assert restored.forecast_evidence is f1
    assert restored.simulation_analytics is s1
    assert restored.value_evidence is v1
    assert restored.publication_generation_id == "generation-1"


def test_promotion_read_override_is_thread_local_and_does_not_leak_working_generation():
    store, state, f1, _s1, _v1 = _published_store()
    working = store.begin_working_generation("jimmy", league_state=state)
    f2 = _forecast(state, "forecast-2")
    store.set_forecast_evidence("jimmy", f2)
    working = store.working_context("jimmy")

    observed = []

    with store.read_context("jimmy", working):
        assert store.get("jimmy").forecast_evidence is f2
        thread = Thread(
            target=lambda: observed.append(store.get("jimmy").forecast_evidence)
        )
        thread.start()
        thread.join(timeout=2)

    assert observed == [f1]
    assert store.get("jimmy").forecast_evidence is f1


def test_all_persisted_surfaces_resolve_from_one_publication_generation():
    store, state, _f1, _s1, _v1 = _published_store()
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    runtime = store.get("jimmy")

    result = continuity.promote(
        user_id="jimmy",
        runtime=runtime,
        builders=tuple(
            (
                surface,
                lambda surface=surface: {
                    "status": "ready",
                    "surface": surface,
                    "league_state_id": state.state_id,
                },
            )
            for surface in REQUIRED_PRESENTATION_SURFACES
        ),
    )
    assert result is not None
    published = store.bind_publication_generation_id(
        "jimmy",
        result.publication_generation_id,
    )

    generation_ids = set()
    for surface in REQUIRED_PRESENTATION_SURFACES:
        payload = continuity.load_for_runtime(
            user_id="jimmy",
            runtime=published,
            surface=surface,
        )
        assert payload is not None
        generation_ids.add(payload["publication_generation_id"])
        assert payload["presentation_continuity"]["mode"] == "published"

    assert generation_ids == {result.publication_generation_id}
