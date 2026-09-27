from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.product.presentation_continuity import (
    PRESENTATION_MANIFEST_ARTIFACT_KIND,
    PRESENTATION_MODEL_VERSION,
    REQUIRED_PRESENTATION_SURFACES,
    HOME_SURFACE,
    PresentationContinuityStore,
)
from fsffl.product.runtime import ServedIntelligenceSnapshot, UserRuntimeContext
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


def _state(as_of: datetime) -> LeagueState:
    league_id = "sleeper:123"
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
        runtime=_runtime(current, served=old),
        surface=HOME_SURFACE,
    )
    assert payload is not None
    assert payload["surface"] == HOME_SURFACE
    assert payload["intelligence_freshness"]["status"] == "stale_last_good"
    assert payload["intelligence_freshness"]["target_state_id"] == current.state_id
    assert payload["intelligence_freshness"]["served_state_id"] == old.state_id
    continuity_meta = payload["presentation_continuity"]
    assert continuity_meta["mode"] == "stale_last_good"
    assert continuity_meta["target_league_state_id"] == current.state_id
    assert continuity_meta["served_league_state_id"] == old.state_id
    assert continuity_meta["served_as_of"] == old.as_of.isoformat()
    assert continuity_meta["promotion_id"]


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
    continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )
    current = _state(old.as_of + timedelta(minutes=5))
    rebuilding = _runtime(current, served=old)
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
    continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old, selected_team_id="a"),
        builders=_builders("old"),
    )
    current = _state(old.as_of + timedelta(minutes=5))

    assert continuity.load_for_runtime(
        user_id="jimmy",
        runtime=_runtime(current, served=old, selected_team_id="b"),
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
    continuity.promote(
        user_id="jimmy",
        runtime=_runtime(old),
        builders=_builders("old"),
    )

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
        runtime=_runtime(current, served=old),
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
