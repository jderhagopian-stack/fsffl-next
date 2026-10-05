from pathlib import Path
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from fsffl.product.presentation_continuity import (
    PRESENTATION_MANIFEST_ARTIFACT_KIND,
    PRESENTATION_MODEL_VERSION,
    LEGACY_PRESENTATION_MODEL_VERSION,
    REQUIRED_PRESENTATION_SURFACES,
    HOME_SURFACE,
    FRANCHISE_SURFACE,
    LEAGUE_ATLAS_SURFACE,
    LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
    MARKET_VALUE_LENSES_ALL_SURFACE,
    MARKET_VALUE_LENSES_ROSTERED_SURFACE,
    PresentationContinuityStore,
)
from fsffl.product.intrinsic_background import IntrinsicBuildStatus
from fsffl.product import league_value_lens_routes
from fsffl.product.league_value_lens_routes import install_league_value_lens_routes
from fsffl.product.runtime import (
    PrivateBetaRuntimeStore,
    ServedIntelligenceSnapshot,
    UserRuntimeContext,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Team,
    TeamState,
)


class MemoryPersistence:
    def __init__(self) -> None:
        self.artifacts = []
        self.read_count = 0

    def put_artifact(self, record) -> None:
        self.artifacts.append(record)

    def get_reusable_artifact(self, key):
        self.read_count += 1
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


def _state(as_of: datetime, *, league_id: str = "sleeper:123") -> LeagueState:
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Continuity League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=as_of,
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


def _runtime(
    state: LeagueState,
    *,
    served: LeagueState | None = None,
    served_generation_id: str | None = None,
    selected_team_id: str = "a",
) -> UserRuntimeContext:
    return UserRuntimeContext(
        user_id="jimmy",
        league_state=state,
        selected_team_id=selected_team_id,
        served_intelligence=(
            ServedIntelligenceSnapshot(
                league_id=served.league.league_id,
                league_state_id=served.state_id,
                as_of=served.as_of,
                team_ids=tuple(sorted(team.team_id for team in served.teams)),
                publication_generation_id=served_generation_id,
            )
            if served is not None
            else None
        ),
    )


def _builders(prefix: str):
    return tuple(
        (
            surface,
            lambda surface=surface: {
                "status": "ready",
                "league_state_id": f"{prefix}-state",
                "surface": surface,
                "rows": [{"id": "x", "value": 1}],
            },
        )
        for surface in REQUIRED_PRESENTATION_SURFACES
    )


def test_manifest_last_promotion_and_stale_read_are_truthful() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    result = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )

    assert result is not None
    assert result.league_state_id == old.state_id
    assert continuity.has_snapshot(
        user_id="jimmy",
        league_id=old.league.league_id,
        league_state_id=old.state_id,
    )
    assert persistence.artifacts[-1].key.artifact_kind == PRESENTATION_MANIFEST_ARTIFACT_KIND
    assert persistence.artifacts[-1].key.model_version == PRESENTATION_MODEL_VERSION

    current = _state(old.as_of + timedelta(minutes=5))
    payload = continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id=result.publication_generation_id,
        ),
        surface=HOME_SURFACE,
    )
    assert payload is not None
    assert payload["surface"] == HOME_SURFACE
    assert payload["intelligence_freshness"]["status"] == "stale_last_good"
    assert payload["league_id"] == old.league.league_id
    assert payload["intelligence_freshness"]["target_state_id"] == current.state_id
    assert payload["intelligence_freshness"]["served_state_id"] == old.state_id
    assert payload["intelligence_freshness"]["target_league_id"] == current.league.league_id
    assert payload["intelligence_freshness"]["served_league_id"] == old.league.league_id
    continuity_meta = payload["presentation_continuity"]
    assert continuity_meta["mode"] == "stale_last_good"
    assert continuity_meta["target_league_id"] == current.league.league_id
    assert continuity_meta["served_league_id"] == old.league.league_id
    assert continuity_meta["target_league_state_id"] == current.state_id
    assert continuity_meta["served_league_state_id"] == old.state_id
    assert continuity_meta["served_as_of"] == old.as_of.isoformat()
    assert continuity_meta["promotion_id"]
    franchise = continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id=result.publication_generation_id,
        ),
        surface=FRANCHISE_SURFACE,
    )
    assert franchise is not None
    assert franchise["intelligence_freshness"]["status"] == "stale_last_good"
    assert franchise["publication_generation_id"] == payload["publication_generation_id"]
    assert franchise["presentation_continuity"]["served_league_state_id"] == old.state_id


def test_published_surface_reads_validate_only_requested_payload_after_promotion() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    state = _state(datetime(2026, 9, 30, 12, 0, tzinfo=UTC))
    result = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(state),
        builders=_builders("current"),
    )
    assert result is not None
    published = replace(
        _runtime(state),
        publication_generation_id=result.publication_generation_id,
    )

    before = persistence.read_count
    first = continuity.load_for_runtime(
        user_id="jimmy", runtime=published, surface=HOME_SURFACE
    )
    first_reads = persistence.read_count - before
    before = persistence.read_count
    second = continuity.load_for_runtime(
        user_id="jimmy", runtime=published, surface=HOME_SURFACE
    )
    second_reads = persistence.read_count - before

    assert first is not None and second is not None
    assert first_reads == second_reads == 2  # manifest + requested surface
    assert second["publication_generation_id"] == result.publication_generation_id

    surface_record = next(
        row
        for row in persistence.artifacts
        if row.key.artifact_kind == "runtime_presentation_surface"
        and row.payload.get("surface") == HOME_SURFACE
    )
    surface_record.payload["payload"]["surface"] = "tampered"
    assert continuity.load_for_runtime(
        user_id="jimmy", runtime=published, surface=HOME_SURFACE
    ) is None


def test_working_generation_promotion_cannot_freeze_staged_value_lenses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _state(datetime(2026, 9, 30, 12, 0, tzinfo=UTC))
    runtime = PrivateBetaRuntimeStore()
    runtime.set_league_state("jimmy", state)
    runtime.select_team("jimmy", state.teams[0].team_id)
    runtime.begin_working_generation("jimmy", league_state=state)
    working = replace(
        runtime.working_context("jimmy"),
        forecast_evidence=object(),
    )
    runtime._working_contexts["jimmy"] = working
    assert runtime.working_generation_active("jimmy")

    record = SimpleNamespace(
        status=IntrinsicBuildStatus.COMPLETED,
        contract=object(),
        league_state_id=state.state_id,
        forecast_coordinate="forecast-v1",
        response_budget_exceeded=False,
        created_at=state.as_of,
        updated_at=state.as_of,
        error=None,
    )

    class ReadyIntrinsicCoordinator:
        def current(self, _context):
            return record

        def request(self, _context):
            raise AssertionError("completed Intrinsic must be reused during promotion")

    monkeypatch.setattr(
        league_value_lens_routes,
        "build_league_value_lenses",
        lambda _context, _intrinsic, **_kwargs: {
            "status": "ready",
            "contract_version": "fixture",
            "league_state_id": state.state_id,
            "broad_market": {"status": "ready"},
            "fsffl_intrinsic": {"status": "full", "player_count": 1},
            "all_player_forecast": {"status": "ready"},
            "players": [
                {
                    "player_id": "dak",
                    "broad_market_percentile": 0.73,
                    "intrinsic_percentile": 0.82,
                    "comparison_available": True,
                }
            ],
        },
    )

    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    app = FastAPI()
    install_league_value_lens_routes(
        app,
        runtime_store=runtime,
        contract_loader=lambda _context: (_ for _ in ()).throw(
            AssertionError("the ready background contract must be reused")
        ),
        require_user=lambda: "jimmy",
        background_coordinator=ReadyIntrinsicCoordinator(),  # type: ignore[arg-type]
        presentation_payload_loader=lambda user_id, context, surface: continuity.load_for_runtime(
            user_id=user_id,
            runtime=context,
            surface=surface,
        ),
    )
    endpoint = next(
        route.endpoint
        for route in app.routes
        if getattr(route, "path", None) == "/api/league/value-lenses"
    )

    def build_surface(surface: str):
        if surface == MARKET_VALUE_LENSES_ROSTERED_SURFACE:
            return endpoint(user_id="jimmy", universe="rostered")
        if surface == MARKET_VALUE_LENSES_ALL_SURFACE:
            return endpoint(user_id="jimmy", universe="all")
        return {"status": "ready", "surface": surface}

    with runtime.read_context("jimmy", working):
        promoted = continuity.promote(
            user_id="jimmy",
            runtime=working,
            builders=tuple(
                (surface, lambda surface=surface: build_surface(surface))
                for surface in REQUIRED_PRESENTATION_SURFACES
            ),
        )
    assert promoted is not None
    published = replace(
        working,
        publication_generation_id=promoted.publication_generation_id,
    )

    loaded = {
        surface: continuity.load_for_runtime(
            user_id="jimmy",
            runtime=published,
            surface=surface,
        )
        for surface in REQUIRED_PRESENTATION_SURFACES
    }
    assert all(payload is not None for payload in loaded.values())
    generations = {
        payload["publication_generation_id"]
        for payload in loaded.values()
        if payload is not None
    }
    assert generations == {promoted.publication_generation_id}
    for surface in (
        MARKET_VALUE_LENSES_ROSTERED_SURFACE,
        MARKET_VALUE_LENSES_ALL_SURFACE,
    ):
        payload = loaded[surface]
        assert payload is not None
        assert payload["status"] == "ready"
        assert payload["surface_readiness"]["status"] == "ready"
        assert payload["fsffl_intrinsic"]["status"] == "full"
        assert payload["players"][0]["broad_market_percentile"] == 0.73
        assert payload["players"][0]["intrinsic_percentile"] == 0.82
    assert loaded[HOME_SURFACE] is not None
    assert loaded[FRANCHISE_SURFACE] is not None
    assert loaded[LEAGUE_ATLAS_SURFACE] is not None


def test_stale_read_is_pinned_to_served_publication_generation() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    assert promoted is not None

    current = _state(old.as_of + timedelta(minutes=5))
    payload = continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id=promoted.publication_generation_id,
        ),
        surface=HOME_SURFACE,
    )
    assert payload is not None
    assert payload["publication_generation_id"] == promoted.publication_generation_id

    assert continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id="different-generation",
        ),
        surface=HOME_SURFACE,
    ) is None



def test_unproven_current_publication_falls_back_to_proven_served_generation() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    assert promoted is not None

    current = _state(old.as_of + timedelta(minutes=5))
    transitional = replace(
        _runtime(
            current,
            served=old,
            served_generation_id=promoted.publication_generation_id,
        ),
        # Restart/revalidation can temporarily expose a runtime/core publication
        # identity before an exact current-State presentation manifest is provable.
        publication_generation_id="unproven-current-generation",
    )

    loaded = {
        surface: continuity.load_for_runtime(
            user_id="jimmy",
            runtime=transitional,
            surface=surface,
        )
        for surface in REQUIRED_PRESENTATION_SURFACES
    }

    assert all(payload is not None for payload in loaded.values())
    assert {
        payload["publication_generation_id"]
        for payload in loaded.values()
        if payload is not None
    } == {promoted.publication_generation_id}
    assert {
        payload["presentation_continuity"]["mode"]
        for payload in loaded.values()
        if payload is not None
    } == {"stale_last_good"}
    assert {
        payload["intelligence_freshness"]["served_state_id"]
        for payload in loaded.values()
        if payload is not None
    } == {old.state_id}
    assert {
        payload["intelligence_freshness"]["target_state_id"]
        for payload in loaded.values()
        if payload is not None
    } == {current.state_id}


def test_proven_current_publication_wins_after_atomic_promotion() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    old_promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    assert old_promoted is not None

    current = _state(old.as_of + timedelta(minutes=5))
    current_runtime = _runtime(
        current,
        served=old,
        served_generation_id=old_promoted.publication_generation_id,
    )
    current_promoted = continuity.promote(
        user_id="jimmy",
        runtime=current_runtime,
        builders=_builders("current"),
    )
    assert current_promoted is not None

    published = replace(
        current_runtime,
        publication_generation_id=current_promoted.publication_generation_id,
    )
    loaded = continuity.load_for_runtime(
        user_id="jimmy",
        runtime=published,
        surface=FRANCHISE_SURFACE,
    )

    assert loaded is not None
    assert loaded["publication_generation_id"] == current_promoted.publication_generation_id
    assert loaded["presentation_continuity"]["mode"] == "published"
    assert loaded["intelligence_freshness"]["status"] == "current"


def test_interrupted_promotion_never_exposes_partial_manifest() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    state = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))

    def fail():
        raise RuntimeError("surface builder failed")

    builders = (
        ("home", lambda: {"status": "ready"}),
        ("franchise", fail),
    )
    with pytest.raises(RuntimeError, match="surface builder failed"):
        continuity.promote(
            user_id="jimmy",
            runtime=_runtime(state),
            builders=builders,
        )

    assert not continuity.has_snapshot(
        user_id="jimmy",
        league_id=state.league.league_id,
        league_state_id=state.state_id,
        required_surfaces=("home", "franchise"),
    )
    assert all(
        row.key.artifact_kind != PRESENTATION_MANIFEST_ARTIFACT_KIND
        for row in persistence.artifacts
    )


def test_promotion_builders_cannot_recursively_read_old_stale_snapshot() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    assert promoted is not None
    current = _state(old.as_of + timedelta(minutes=5))
    rebuilding = _runtime(
        current,
        served=old,
        served_generation_id=promoted.publication_generation_id,
    )
    recursive_results = []

    def builder(surface: str):
        recursive_results.append(
            continuity.load_for_runtime(
                user_id="jimmy",
                runtime=rebuilding,
                surface=surface,
            )
        )
        return {
            "status": "ready",
            "league_state_id": current.state_id,
            "surface": surface,
        }

    continuity.promote(
        user_id="jimmy",
        runtime=rebuilding,
        builders=tuple(
            (surface, lambda surface=surface: builder(surface))
            for surface in REQUIRED_PRESENTATION_SURFACES
        ),
    )

    assert recursive_results
    assert all(item is None for item in recursive_results)
    assert continuity.has_snapshot(
        user_id="jimmy",
        league_id=current.league.league_id,
        league_state_id=current.state_id,
    )



def test_stale_snapshot_is_rejected_after_managed_team_changes() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old, selected_team_id="a"),
        builders=_builders("old"),
    )
    assert promoted is not None
    current = _state(old.as_of + timedelta(minutes=5))

    assert continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id=promoted.publication_generation_id,
            selected_team_id="b",
        ),
        surface=HOME_SURFACE,
    ) is None
    assert not continuity.has_snapshot(
        user_id="jimmy",
        league_id=old.league.league_id,
        league_state_id=old.state_id,
        selected_team_id="b",
    )


def test_failed_repromotion_of_same_state_keeps_prior_generation_atomic() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    promoted = continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    assert promoted is not None

    def fail():
        raise RuntimeError("replacement failed")

    with pytest.raises(RuntimeError, match="replacement failed"):
        continuity.promote(
            user_id="jimmy",
            runtime=_runtime(old),
            builders=(
                (REQUIRED_PRESENTATION_SURFACES[0], lambda: {"surface": "new-home"}),
                (REQUIRED_PRESENTATION_SURFACES[1], fail),
            ),
        )

    current = _state(old.as_of + timedelta(minutes=5))
    payload = continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(
            current,
            served=old,
            served_generation_id=promoted.publication_generation_id,
        ),
        surface=HOME_SURFACE,
    )
    assert payload is not None
    assert payload["surface"] == HOME_SURFACE


def test_snapshot_integrity_rejects_payload_mutation() -> None:
    persistence = MemoryPersistence()
    continuity = PresentationContinuityStore(persistence)
    old = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    surface_record = next(
        row
        for row in persistence.artifacts
        if row.key.artifact_kind == "runtime_presentation_surface"
    )
    surface_record.payload["payload"]["surface"] = "tampered"

    assert not continuity.has_snapshot(
        user_id="jimmy",
        league_id=old.league.league_id,
        league_state_id=old.state_id,
        selected_team_id="a",
    )



def test_fast_snapshot_hint_is_warmed_only_after_strict_validation() -> None:
    persistence = MemoryPersistence()
    state = _state(datetime(2026, 9, 27, 12, 0, tzinfo=UTC))
    continuity = PresentationContinuityStore(persistence)
    continuity.promote(
        user_id="jimmy",
        runtime=_runtime(state),
        builders=_builders("current"),
    )

    assert continuity.known_snapshot_available(
        user_id="jimmy",
        league_id=state.league.league_id,
        league_state_id=state.state_id,
        selected_team_id="a",
    )

    # A fresh process/store object has no in-memory hint until the durable
    # manifest/surfaces pass the unchanged strict integrity validation.
    cold = PresentationContinuityStore(persistence)
    assert not cold.known_snapshot_available(
        user_id="jimmy",
        league_id=state.league.league_id,
        league_state_id=state.state_id,
        selected_team_id="a",
    )
    assert cold.has_snapshot(
        user_id="jimmy",
        league_id=state.league.league_id,
        league_state_id=state.state_id,
        selected_team_id="a",
    )
    assert cold.known_snapshot_available(
        user_id="jimmy",
        league_id=state.league.league_id,
        league_state_id=state.state_id,
        selected_team_id="a",
    )


def test_dynasty_position_rooms_are_required_in_atomic_presentation_publication() -> None:
    assert LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE in REQUIRED_PRESENTATION_SURFACES


def test_dynasty_publication_bumps_cache_version_and_keeps_legacy_migration_contract() -> None:
    assert PRESENTATION_MODEL_VERSION == "runtime-presentation-continuity-v2"
    assert LEGACY_PRESENTATION_MODEL_VERSION == "runtime-presentation-continuity-v1"


def test_dynasty_preparation_waits_through_coordinator_watchdog_and_startup_backfills() -> None:
    source = Path("src/fsffl/product/persistent_webapp.py").read_text(encoding="utf-8")
    assert "timeout_seconds=240.0" in source
    assert "timeout_seconds=400.0" in source
    assert "if legacy_migration:\n                            _prepare_presentation_for_user" not in source
    assert (
        "_prepare_presentation_for_user(_beta_restore_user, context)\n"
        "                        promotion = _promote_presentation_for_user"
    ) in source
