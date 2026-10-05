from __future__ import annotations

from datetime import UTC, datetime
from time import monotonic, sleep

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord
from fsffl.product.foundation4_career_forward_runtime import (
    CAREER_INTRINSIC_ARTIFACT_KIND,
    CAREER_INTRINSIC_SCOPE_KIND,
    LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
    LEGACY_FOUNDATION4_SCOPE_KIND,
    FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
    FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
    CareerIntrinsicLoader,
    Foundation4CareerForwardShadowLoader,
)
from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_CURRENT_COHORT_SIZE,
    FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    provide_foundation4_terminal_features,
)
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.product.foundation4_shadow_routes import (
    FOUNDATION4_CAREER_FORWARD_ENDPOINT,
    FOUNDATION4_Y4_Y7_ENDPOINT,
    install_foundation4_shadow_routes,
)
from fsffl.product.intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
)
from fsffl.product.runtime import PrivateBetaRuntimeStore, UserRuntimeContext
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    RosterSlot,
    ScoringRule,
)
from fsffl.value.shapley_intrinsic_contract import (
    CompletedSourceFactProvenance,
    DiagnosticH1Evidence,
    ShapleyHorizonProvenance,
    ShapleyHorizonUncertainty,
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
    ShapleyIntrinsicCoverage,
    ShapleyIntrinsicHorizonContribution,
    ShapleyIntrinsicPlayerEstimate,
)


class MemoryPersistence:
    def __init__(self) -> None:
        self.artifacts = []

    def get_reusable_artifact(self, key):
        return next(
            (
                row
                for row in reversed(self.artifacts)
                if row.key == key and getattr(row, "reusable", True)
            ),
            None,
        )

    def put_artifact(self, record):
        self.artifacts.append(record)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    )


def _context(*, rules: LeagueRules | None = None) -> UserRuntimeContext:
    state = LeagueState(
        league=League(
            league_id="sleeper:foundation4-test",
            name="Foundation 4 Test",
            season=2026,
            rules=rules or _rules(),
        ),
        as_of=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
        teams=(),
        team_states=(),
        players=(),
        player_states=(),
    )
    return UserRuntimeContext(user_id="local-beta-user", league_state=state)


def _current_intrinsic() -> ShapleyIntrinsicContract:
    terminal = provide_foundation4_terminal_features()
    provenance = ShapleyHorizonProvenance(
        authority="test-governed-current",
        source="test",
        model_version="test-current-v1",
    )
    uncertainty = ShapleyHorizonUncertainty(evidence_path="test")
    estimates = []
    for player_id in sorted(terminal):
        contributions = tuple(
            ShapleyIntrinsicHorizonContribution(
                year_index=year,
                target_season=2025 + year,
                raw_shapley_contribution=float(year),
                discount_factor=1.0,
                discounted_contribution=float(year),
                provenance=provenance,
                uncertainty=uncertainty,
            )
            for year in (1, 2, 3)
        )
        estimates.append(
            ShapleyIntrinsicPlayerEstimate(
                player_id=player_id,
                raw_intrinsic_value=6.0,
                contributions=contributions,
                diagnostic_h1=DiagnosticH1Evidence(
                    target_season=2026,
                    anticipated_points=0.0,
                    provenance=provenance.model_copy(
                        update={"diagnostic_only": True, "included_in_intrinsic": False}
                    ),
                    uncertainty=uncertainty,
                    included_in_intrinsic=False,
                ),
            )
        )
    return ShapleyIntrinsicContract(
        status=ShapleyIntrinsicAvailability.READY,
        evaluation_season=2026,
        completed_source_season=2025,
        target_years=(2026, 2027, 2028),
        completed_source_provenance=CompletedSourceFactProvenance(
            source_version="test"
        ),
        coverage=ShapleyIntrinsicCoverage(
            player_count=len(estimates),
            year_1_forecast_players=len(estimates),
            year_2_i1_players=len(estimates),
            year_3_i1_players=len(estimates),
            rich_path_players=len(estimates),
            reduced_or_fallback_players=0,
        ),
        estimates=tuple(estimates),
    )


def _loader(persistence, calls):
    current = _current_intrinsic()

    def current_loader(_context):
        calls.append("current")
        return current

    return Foundation4CareerForwardShadowLoader(
        current_intrinsic_loader=current_loader,
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=persistence,
    )


def test_live_sleeper_lineup_order_matches_frozen_terminal_capacity_signature() -> None:
    rules = _rules().model_copy(
        update={
            "lineup": tuple(sorted(_rules().lineup, key=lambda row: row.slot.value))
        }
    )
    persistence = MemoryPersistence()
    calls = []
    loader = _loader(persistence, calls)

    contract = loader(_context(rules=rules))

    assert contract.player_count == FOUNDATION4_CURRENT_COHORT_SIZE
    assert calls == ["current"]


@pytest.mark.parametrize(
    "scoring",
    (
        FROZEN_I1_STANDARD_SCORING,
        tuple(
            ScoringRule(
                stat=row.stat,
                points=6.0 if row.stat == "pass_td" else row.points,
            )
            for row in FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        ),
        FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING
        + (ScoringRule(stat="bonus_pass_yd_400", points=5.0),),
    ),
)
def test_runtime_fails_closed_before_aggregating_incompatible_scoring(scoring) -> None:
    persistence = MemoryPersistence()
    calls = []
    loader = _loader(persistence, calls)
    rules = _rules().model_copy(update={"scoring": scoring})

    with pytest.raises(
        ValueError,
        match="active player-offense scoring is incompatible",
    ):
        loader(_context(rules=rules))

    assert calls == []
    assert persistence.artifacts == []


@pytest.fixture(scope="module")
def materialized():
    persistence = MemoryPersistence()
    calls = []
    loader = _loader(persistence, calls)
    context = _context()
    contract = loader(context)
    return persistence, calls, loader, context, contract


def test_full_current_cohort_materializes_and_persists_both_shadow_artifacts(
    materialized,
) -> None:
    persistence, calls, _loader_instance, _context_instance, contract = materialized

    assert contract.player_count == FOUNDATION4_CURRENT_COHORT_SIZE == 335
    assert len(contract.estimates) == 335
    assert contract.current_intrinsic_replaced is False
    assert contract.display_scaling_applied is False
    assert contract.market_inputs_used is False
    assert contract.ignored_long_term_residual_rule_stats == (
        "fum_rec",
        "fum_rec_td",
        "st_ff",
        "st_fum_rec",
        "st_td",
    )
    assert "Standalone Current Intrinsic remains unchanged" in (
        contract.scoring_coordinate_limitation or ""
    )
    # Management refinement: do not subtract the rare residual lane from the
    # standalone Current Intrinsic contribution merely to align the Long-Term
    # frozen coordinate.
    assert {row.current_intrinsic_raw_y1_y3 for row in contract.estimates} == {6.0}
    assert calls == ["current"]
    kinds = {row.key.artifact_kind for row in persistence.artifacts}
    assert FOUNDATION4_Y4_Y7_ARTIFACT_KIND in kinds
    assert FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND in kinds


def test_restart_restore_is_semantically_identical_and_skips_rebuild(
    materialized,
) -> None:
    persistence, _calls, first_loader, context, built = materialized
    second_calls = []
    second_loader = _loader(persistence, second_calls)
    restored = second_loader.restore_compatible(context)

    assert restored is not None
    assert restored == built
    assert restored.input_fingerprint == built.input_fingerprint
    assert second_loader.intrinsic_input_fingerprint(context) == (
        first_loader.intrinsic_input_fingerprint(context)
    )
    assert second_calls == []
    component = second_loader.restore_component(context)
    assert component is not None
    assert len(component.estimates) == 335


def test_shadow_api_serves_completed_full_cohort_and_y4_y7_component(
    monkeypatch,
    materialized,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    persistence, _calls, _first_loader, context, _built = materialized
    api_calls = []
    loader = _loader(persistence, api_calls)
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    coordinator = ShapleyIntrinsicBackgroundCoordinator(loader, max_workers=1)
    app = FastAPI()
    install_foundation4_shadow_routes(
        app,
        runtime_store=store,
        loader=loader,
        coordinator=coordinator,
    )
    client = TestClient(app)

    deadline = monotonic() + 10.0
    response = client.get(FOUNDATION4_CAREER_FORWARD_ENDPOINT)
    while response.status_code == 202 and monotonic() < deadline:
        sleep(0.02)
        response = client.get(FOUNDATION4_CAREER_FORWARD_ENDPOINT)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "shadow_ready"
    assert payload["player_count"] == 335
    assert payload["current_intrinsic_replaced"] is False
    assert payload["display_scaling_applied"] is False
    assert payload["market_inputs_used"] is False

    component = client.get(FOUNDATION4_Y4_Y7_ENDPOINT)
    assert component.status_code == 200
    component_payload = component.json()
    assert component_payload["status"] == "shadow_ready"
    assert len(component_payload["estimates"]) == 335
    assert coordinator.current(store.get("local-beta-user")).status == (
        IntrinsicBuildStatus.COMPLETED
    )
    assert api_calls == []


def test_accepted_legacy_shadow_artifact_migrates_to_canonical_career_intrinsic_without_rebuild(materialized) -> None:
    persistence, _calls, first_loader, context, built = materialized
    fingerprint = first_loader.intrinsic_input_fingerprint(context)
    canonical = next(
        row for row in persistence.artifacts
        if row.key.artifact_kind == CAREER_INTRINSIC_ARTIFACT_KIND
    )
    legacy = ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
            scope_kind=LEGACY_FOUNDATION4_SCOPE_KIND,
            scope_id=canonical.key.scope_id,
            input_fingerprint=canonical.key.input_fingerprint,
            model_version=canonical.key.model_version,
        ),
        payload=canonical.payload,
        computed_at=canonical.computed_at,
    )
    legacy_only = MemoryPersistence()
    legacy_only.put_artifact(legacy)
    calls = []
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: calls.append("rebuild"),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=legacy_only,
    )

    restored = loader.restore_compatible(context)

    assert restored == built
    assert calls == []
    migrated = [
        row for row in legacy_only.artifacts
        if row.key.artifact_kind == CAREER_INTRINSIC_ARTIFACT_KIND
        and row.key.scope_kind == CAREER_INTRINSIC_SCOPE_KIND
        and row.key.input_fingerprint == fingerprint
    ]
    assert len(migrated) == 1


def test_canonical_career_intrinsic_endpoint_is_primary_and_not_shadow_labeled(monkeypatch, materialized) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    persistence, _calls, _first_loader, context, _built = materialized
    loader = _loader(persistence, [])
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    coordinator = ShapleyIntrinsicBackgroundCoordinator(loader, max_workers=1)
    app = FastAPI()
    install_foundation4_shadow_routes(app, runtime_store=store, loader=loader, coordinator=coordinator)
    client = TestClient(app)
    deadline = monotonic() + 10.0
    response = client.get("/api/value/career-intrinsic-v1")
    while response.status_code == 202 and monotonic() < deadline:
        sleep(0.02)
        response = client.get("/api/value/career-intrinsic-v1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["capability"] == "career_intrinsic"
    assert payload["value_label"] == "Career Intrinsic"
    assert payload["status"] == "ready"
    assert "shadow" not in payload


def test_dynasty_rooms_prefer_ready_canonical_career_intrinsic_over_stale_unavailable_presentation(monkeypatch, materialized) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    persistence, _calls, _first_loader, context, _built = materialized
    loader = _loader(persistence, [])
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    coordinator = ShapleyIntrinsicBackgroundCoordinator(loader, max_workers=1)
    record = coordinator.wait_for_terminal(context, timeout_seconds=10.0)
    assert record.status == IntrinsicBuildStatus.COMPLETED
    app = FastAPI()
    install_foundation4_shadow_routes(
        app,
        runtime_store=store,
        loader=loader,
        coordinator=coordinator,
        presentation_payload_loader=lambda *_args: {
            "status": "unavailable",
            "reason": "stale presentation placeholder",
        },
    )
    response = TestClient(app).get("/api/league/dynasty-position-rooms")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["capability"] == "career_intrinsic"
    assert len(payload["rooms"]) == 0  # synthetic unit State has no teams


def test_accepted_legacy_y4_y7_component_migrates_scope_without_rebuild(materialized) -> None:
    persistence, _calls, first_loader, context, _built = materialized
    canonical = next(
        row for row in persistence.artifacts
        if row.key.artifact_kind == FOUNDATION4_Y4_Y7_ARTIFACT_KIND
    )
    legacy = ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=canonical.key.artifact_kind,
            scope_kind=LEGACY_FOUNDATION4_SCOPE_KIND,
            scope_id=canonical.key.scope_id,
            input_fingerprint=canonical.key.input_fingerprint,
            model_version=canonical.key.model_version,
        ),
        payload=canonical.payload,
        computed_at=canonical.computed_at,
    )
    legacy_only = MemoryPersistence()
    legacy_only.put_artifact(legacy)
    loader = _loader(legacy_only, [])
    restored = loader.restore_component(context)
    assert restored is not None
    migrated = [
        row for row in legacy_only.artifacts
        if row.key.artifact_kind == FOUNDATION4_Y4_Y7_ARTIFACT_KIND
        and row.key.scope_kind == CAREER_INTRINSIC_SCOPE_KIND
    ]
    assert len(migrated) == 1


def test_dynasty_route_does_not_deserialize_career_artifact_on_foreground_request() -> None:
    source = __import__("pathlib").Path("src/fsffl/product/foundation4_shadow_routes.py").read_text(encoding="utf-8")
    route = source.split('@app.get("/api/league/dynasty-position-rooms")', 1)[1].split("@app.get(FOUNDATION4_Y4_Y7_ENDPOINT)", 1)[0]
    assert "restore_compatible(" not in route
    assert "coordinator.current(context)" in route
    assert "presentation_payload_loader" in route
    assert "coordinator.request(context)" in route
