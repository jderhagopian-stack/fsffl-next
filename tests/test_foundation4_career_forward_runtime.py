from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import replace
from time import monotonic, sleep
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord, utc_now
from fsffl.product.foundation4_career_forward_runtime import (
    validate_foundation4_expanded_acceptance_cohort,
    CAREER_INTRINSIC_ARTIFACT_KIND,
    CAREER_INTRINSIC_SCOPE_KIND,
    LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
    LEGACY_FOUNDATION4_SCOPE_KIND,
    FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
    FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
    CareerIntrinsicLoader,
    ExpandedCareerContractResult,
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
    _carry_dynasty_last_good,
    _career_position_depth_rows,
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
    Player,
    Position,
    RosterSlot,
    RosterEntry,
    ScoringRule,
    Team,
    TeamState,
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


def test_expanded_acceptance_keeps_frozen_335_and_accepts_current_dynamic_rows():
    frozen = tuple(f"frozen-{index}" for index in range(335))
    current = (*frozen, "dynamic-ready", "dynamic-unresolved")
    career = (*frozen, "dynamic-ready")

    dynamic = validate_foundation4_expanded_acceptance_cohort(
        frozen_reference_ids=frozen,
        current_intrinsic_ids=current,
        career_estimate_ids=career,
        expected_frozen_count=335,
    )

    assert dynamic == frozenset({"dynamic-ready"})


def test_expanded_acceptance_rejects_dynamic_rows_outside_current_cohort():
    frozen = tuple(f"frozen-{index}" for index in range(335))
    with pytest.raises(ValueError, match="outside expanded Current"):
        validate_foundation4_expanded_acceptance_cohort(
            frozen_reference_ids=frozen,
            current_intrinsic_ids=frozen,
            career_estimate_ids=(*frozen, "untracked-dynamic"),
            expected_frozen_count=335,
        )


def test_promoted_last_good_dynasty_drops_prior_state_career_rows():
    carried = _carry_dynasty_last_good(
        {
            "status": "ready",
            "league_state_id": "old-state",
            "publication_generation_id": "old-generation",
            "career_position_depth": [{"player_id": "p1", "state_hash": "old-state"}],
            "rooms": [{"team_id": "team-a"}],
        },
        state_id="new-state",
    )

    assert carried["league_state_id"] == "new-state"
    assert carried["dynasty_evidence_state_id"] == "old-state"
    assert carried["rooms"] == [{"team_id": "team-a"}]
    assert "career_position_depth" not in carried
    assert "publication_generation_id" not in carried


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
    persistence, calls, loader_instance, context_instance, contract = materialized

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
    assert loader_instance._cached_component is None
    restored_component = loader_instance.current_component(context_instance)
    assert restored_component is not None
    assert len(restored_component.estimates) == FOUNDATION4_CURRENT_COHORT_SIZE


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


def test_restart_restores_complete_expanded_contract_without_acquisition(materialized):
    persistence, _calls, _base_loader, context, base = materialized
    calls = []
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: calls.append("current"),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=persistence,
        expanded_career_contract_loader=lambda *_args: calls.append("provider-and-fit"),
        expanded_career_contract_fingerprint_resolver=lambda _context: "dynamic-fp-v1",
    )
    dynamic_id = "sleeper:player:restored-dynamic"
    dynamic_row = base.estimates[0].model_copy(update={"player_id": dynamic_id})
    expanded = base.model_copy(update={
        "estimates": (*base.estimates, dynamic_row),
        "player_count": base.player_count + 1,
        "player_coverage_failures": {"sleeper:player:unsupported": "verified missing evidence"},
    })
    component = _base_loader.current_component(context)
    loader._persist(
        context,
        dependency_fingerprint=loader.intrinsic_input_fingerprint(context),
        component=component,
        contract=expanded,
        source_manifest=_fixture_source_manifest(context),
    )
    assert loader.restore_compatible(context) == expanded
    assert loader(context) == expanded
    assert calls == []


def test_base_only_artifact_is_not_restored_as_completed_expanded_product(materialized):
    persistence, _calls, _base_loader, context, base = materialized
    calls = []
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: calls.append("current"),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=persistence,
        expanded_career_contract_loader=lambda *_args: calls.append("provider-and-fit"),
        expanded_career_contract_fingerprint_resolver=lambda _context: "dynamic-fp-v1",
    )
    fingerprint = loader.intrinsic_input_fingerprint(context)
    payload = base.model_dump(mode="json")
    payload["_foundation4_dependency_fingerprint"] = fingerprint
    persistence.put_artifact(ReusableArtifactRecord(
        key=loader._career_key(context, fingerprint), payload=payload, computed_at=utc_now(),
    ))
    assert loader.restore_compatible(context) is None
    assert calls == []


def test_component_reads_are_reused_and_disabled_persistence_keeps_only_copy(materialized):
    persistence, _calls, loader, context, _base = materialized
    first = loader.current_component(context)
    assert first is not None
    assert loader.current_component(context) is first
    transient = _loader(None, [])
    transient(context)
    assert transient.current_component(context) is not None
    transient.clear_user_cache(context.user_id)
    assert transient._cached_component is None


def test_unpinned_state_uses_evidence_cutoff_not_reader_clock(materialized, monkeypatch):
    _persistence, _calls, loader, context, _base = materialized
    first = loader.pin_build_context(context)
    monkeypatch.setattr("fsffl.product.foundation4_career_forward_runtime.utc_now",
                        lambda: datetime(2030, 1, 1, tzinfo=UTC))
    restarted = loader.pin_build_context(context)
    assert first.career_fingerprint_evaluation_as_of == context.league_state.as_of
    assert restarted == first


def test_freshness_epoch_replaces_one_durable_career_artifact_slot(materialized):
    _persistence, _calls, _base_loader, context, _base = materialized
    from fsffl.product.dynamic_career_composition import dynamic_career_fingerprint

    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: _current_intrinsic(),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        expanded_career_contract_loader=lambda _context, frozen: frozen,
        expanded_career_contract_fingerprint_resolver=lambda item: (
            dynamic_career_fingerprint(
                item, now=item.career_fingerprint_evaluation_as_of
            )
        ),
        career_artifact_key_fingerprint_resolver=lambda item: (
            dynamic_career_fingerprint(
                item,
                now=item.career_fingerprint_evaluation_as_of,
                include_freshness_epoch=False,
            )
        ),
    )
    first = UserRuntimeContext(
        user_id=context.user_id,
        league_state=context.league_state,
        career_fingerprint_evaluation_as_of=datetime(2026, 10, 15, 0, 0, tzinfo=UTC),
    )
    next_epoch = UserRuntimeContext(
        user_id=context.user_id,
        league_state=context.league_state,
        career_fingerprint_evaluation_as_of=datetime(2026, 10, 15, 6, 0, tzinfo=UTC),
    )
    first_fingerprint = loader.intrinsic_input_fingerprint(first)
    next_fingerprint = loader.intrinsic_input_fingerprint(next_epoch)

    assert first_fingerprint != next_fingerprint
    assert loader._career_key(first, first_fingerprint) == loader._career_key(
        next_epoch, next_fingerprint
    )


def test_coordinator_pins_freshness_in_key_and_background_worker(materialized):
    _persistence, _calls, _base_loader, context, _base = materialized
    start = datetime(2026, 10, 15, 5, 59, 59, tzinfo=UTC)
    wall_clock = [start]
    built_fingerprints = []

    class TimeSensitiveLoader:
        def pin_build_context(self, value):
            return replace(value, career_fingerprint_evaluation_as_of=wall_clock[0])

        def fingerprint(self, value):
            evaluated_at = value.career_fingerprint_evaluation_as_of or wall_clock[0]
            return str(int(evaluated_at.timestamp() // (6 * 60 * 60)))

        def __call__(self, value):
            wall_clock[0] = start.replace(hour=6, minute=0, second=1)
            built_fingerprints.append(self.fingerprint(value))
            return _current_intrinsic()

    loader = TimeSensitiveLoader()
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        intrinsic_input_fingerprint_resolver=loader.fingerprint,
    )
    queued = coordinator.request(context)
    key = (
        queued.user_id,
        context.league_state.league.league_id,
        queued.intrinsic_input_fingerprint,
    )
    coordinator._futures[key].result(timeout=10)
    completed = coordinator._records[key]

    assert built_fingerprints == [queued.intrinsic_input_fingerprint]
    assert completed.status == IntrinsicBuildStatus.COMPLETED


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
    coordinator.restore_compatible_staged(store.get("local-beta-user"))
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
    assert payload["status"] == "ready"
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
    coordinator.restore_compatible_staged(store.get("local-beta-user"))
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
    store.bind_publication_generation_id(
        "local-beta-user", "dynasty-generation-ready"
    )
    coordinator = ShapleyIntrinsicBackgroundCoordinator(loader, max_workers=1)
    record = coordinator.wait_for_terminal(store.get("local-beta-user"), timeout_seconds=10.0)
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
    response = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": context.league_state.state_id, "publication_generation_id": "dynasty-generation-ready"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["capability"] == "career_intrinsic"
    assert payload["publication_generation_id"] == "dynasty-generation-ready"
    assert len(payload["rooms"]) == 0  # synthetic unit State has no teams


def test_career_position_depth_publishes_each_exact_state_roster_player_independently():
    state = SimpleNamespace(
        state_id="state-current",
        players=(
            SimpleNamespace(player_id="sleeper:player:frozen", position=SimpleNamespace(value="QB")),
            SimpleNamespace(player_id="sleeper:player:new-roster", position=SimpleNamespace(value="TE")),
            SimpleNamespace(player_id="sleeper:player:kicker", position=SimpleNamespace(value="K")),
        ),
        team_states=(
            SimpleNamespace(team_id="team-a", roster=(
                SimpleNamespace(player_id="sleeper:player:frozen", slot=SimpleNamespace(value="BENCH")),
                SimpleNamespace(player_id="sleeper:player:new-roster", slot=SimpleNamespace(value="TAXI")),
                SimpleNamespace(player_id="sleeper:player:kicker", slot=SimpleNamespace(value="K")),
            )),
        ),
    )
    career = SimpleNamespace(estimates=(SimpleNamespace(player_id="sleeper:player:frozen"),))

    rows = _career_position_depth_rows(state, career)

    assert len(rows) == 2
    assert {row["state_hash"] for row in rows} == {"state-current"}
    by_id = {row["player_id"]: row for row in rows}
    assert by_id["sleeper:player:frozen"]["career_coverage_status"] == "career_authority_available"
    assert by_id["sleeper:player:new-roster"]["career_coverage_status"] == "career_authority_failure"
    assert by_id["sleeper:player:new-roster"]["career_failure_reason"] == "career_estimate_missing_from_exact_state_contract"
    assert by_id["sleeper:player:new-roster"]["roster_slot"] == "TAXI"


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
    assert "coordinator.request(context)" not in route


@pytest.mark.parametrize(
    ("status", "expected_status"),
    (
        (IntrinsicBuildStatus.RUNNING, "preparing"),
        (IntrinsicBuildStatus.FAILED, "unavailable"),
    ),
)
def test_dynasty_nonready_responses_keep_published_generation(
    monkeypatch,
    status,
    expected_status,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    context = _context()
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    store.bind_publication_generation_id(
        "local-beta-user", "dynasty-generation-nonready"
    )
    record = SimpleNamespace(
        status=status,
        league_state_id=context.league_state.state_id,
        intrinsic_input_fingerprint="career-fp",
        contract=None,
        error="career evidence failed" if status == IntrinsicBuildStatus.FAILED else None,
    )

    class Coordinator:
        def current(self, _context):
            return record

        def request(self, _context):
            raise AssertionError("reader must not start a build")

    app = FastAPI()
    install_foundation4_shadow_routes(
        app,
        runtime_store=store,
        loader=SimpleNamespace(),
        coordinator=Coordinator(),
    )
    response = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": context.league_state.state_id, "publication_generation_id": "dynasty-generation-nonready"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == expected_status
    assert payload["publication_generation_id"] == "dynasty-generation-nonready"


def test_dynasty_last_good_requires_current_publication_generation(monkeypatch) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    context = _context()
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    store.bind_publication_generation_id(
        "local-beta-user", "replacement-runtime-generation"
    )
    pending = SimpleNamespace(
        status=IntrinsicBuildStatus.RUNNING,
        league_state_id=context.league_state.state_id,
        intrinsic_input_fingerprint="career-fp",
        contract=None,
        error=None,
    )
    request_calls = []

    class Coordinator:
        def current(self, _context):
            return pending

        def request(self, _context):
            request_calls.append(_context)
            return pending

    last_good = {
        "status": "ready",
        "capability": "career_intrinsic",
        "league_id": context.league_state.league.league_id,
        "league_state_id": context.league_state.state_id,
        "publication_generation_id": "served-last-good-generation",
        "dynasty_evidence_status": "last_good",
        "rooms": [],
    }
    app = FastAPI()
    install_foundation4_shadow_routes(
        app,
        runtime_store=store,
        loader=SimpleNamespace(),
        coordinator=Coordinator(),
        presentation_payload_loader=lambda *_args: dict(last_good),
    )
    payload = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": context.league_state.state_id, "publication_generation_id": "replacement-runtime-generation"},
    ).json()
    assert payload["status"] == "preparing"
    assert payload["league_state_id"] == context.league_state.state_id
    assert payload["publication_generation_id"] == "replacement-runtime-generation"
    assert payload.get("rooms") is None
    assert request_calls == []


def test_dynasty_rejects_unversioned_last_good_instead_of_guessing_generation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    context = _context()
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", context.league_state)
    store.bind_publication_generation_id(
        "local-beta-user", "current-runtime-generation"
    )
    failed = SimpleNamespace(
        status=IntrinsicBuildStatus.FAILED,
        league_state_id=context.league_state.state_id,
        intrinsic_input_fingerprint="career-fp",
        contract=None,
        error="current Career evidence unavailable",
    )

    class Coordinator:
        def current(self, _context):
            return failed

        def request(self, _context):
            return failed

    app = FastAPI()
    install_foundation4_shadow_routes(
        app,
        runtime_store=store,
        loader=SimpleNamespace(),
        coordinator=Coordinator(),
        presentation_payload_loader=lambda *_args: {
            "status": "ready",
            "dynasty_evidence_status": "last_good",
            "league_state_id": context.league_state.state_id,
            "rooms": [],
        },
    )
    payload = TestClient(app).get(
        "/api/league/dynasty-position-rooms",
        params={"state_id": context.league_state.state_id, "publication_generation_id": "current-runtime-generation"},
    ).json()
    assert payload["status"] == "unavailable"
    assert payload["publication_generation_id"] == "current-runtime-generation"


def test_runtime_appends_only_complete_expanded_candidates_from_exact_roster(materialized) -> None:
    _persistence, _calls, _base_loader, context, frozen = materialized
    candidate_id = "sleeper:player:outside-runtime-fixture"
    frozen_row = next(
        row for row in frozen.estimates if row.position.value == "QB"
    )
    frozen_tail = frozen_row.uncertainty.terminal_y8_plus
    candidate_tail = frozen_tail.model_copy(
        update={
            "player_id": candidate_id,
            "features": frozen_tail.features.model_copy(
                update={"player_id": candidate_id}
            ),
        }
    )
    candidate_uncertainty = frozen_row.uncertainty.model_copy(
        update={"terminal_y8_plus": candidate_tail}
    )
    candidate_row = frozen_row.model_copy(
        update={"player_id": candidate_id, "uncertainty": candidate_uncertainty}
    )
    expanded = frozen.model_copy(
        update={
            "input_fingerprint": "expanded-runtime-fixture",
            "estimates": frozen.estimates + (candidate_row,),
            "player_count": frozen.player_count + 1,
        }
    )
    state_player = Player(player_id=candidate_id, full_name="Expanded Fixture", position=Position.QB)
    roster_entry = RosterEntry(player_id=candidate_id, slot=RosterSlot.BENCH)
    team_state = TeamState(team_id="team-1", roster=(roster_entry,))
    league_state = context.league_state.model_copy(
        update={
            "players": context.league_state.players + (state_player,),
            "team_states": (team_state,),
        }
    )
    exact_context = UserRuntimeContext(
        user_id=context.user_id,
        league_state=league_state,
    )
    dynamic_loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: _current_intrinsic(),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        expanded_career_contract_loader=lambda _context, _frozen: expanded,
        expanded_career_contract_fingerprint_resolver=lambda _context: "regular-forecast-evidence-fixture-v1",
    )

    result = dynamic_loader(exact_context)
    frozen_result = {row.player_id: row for row in result.estimates}
    assert result.player_count == 336
    assert frozen_result[candidate_id] == candidate_row
    assert all(
        frozen_result[row.player_id] == row for row in frozen.estimates
    )
    assert result.current_intrinsic_replaced is False


def test_runtime_rejects_expanded_candidates_outside_exact_roster(materialized) -> None:
    _persistence, _calls, _base_loader, context, frozen = materialized
    candidate_id = "sleeper:player:outside-unrostered-fixture"
    candidate_row = frozen.estimates[0].model_copy(update={"player_id": candidate_id})
    expanded = frozen.model_copy(
        update={
            "input_fingerprint": "unrostered-runtime-fixture",
            "estimates": frozen.estimates + (candidate_row,),
            "player_count": frozen.player_count + 1,
        }
    )
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: _current_intrinsic(),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        expanded_career_contract_loader=lambda _context, _frozen: expanded,
        expanded_career_contract_fingerprint_resolver=lambda _context: "unrostered-evidence-fixture-v1",
    )
    with pytest.raises(ValueError, match="outside exact-State roster"):
        loader(context)


def test_expanded_roster_failure_is_visible_without_blocking_frozen_career(materialized) -> None:
    _persistence, _calls, _base_loader, context, frozen = materialized
    candidate_id = "sleeper:player:fringe-explicit-failure"
    state_player = Player(
        player_id=candidate_id,
        full_name="Fringe Fixture",
        position=Position.WR,
    )
    roster_entry = RosterEntry(player_id=candidate_id, slot=RosterSlot.TAXI)
    team = Team(
        team_id="team-1",
        league_id="sleeper:foundation4-test",
        display_name="Team 1",
    )
    team_state = TeamState(team_id="team-1", roster=(roster_entry,))
    exact_state = context.league_state.model_copy(
        update={
            "teams": (team,),
            "players": context.league_state.players + (state_player,),
            "team_states": (team_state,),
        }
    )
    exact_context = UserRuntimeContext(user_id=context.user_id, league_state=exact_state)
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: _current_intrinsic(),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        expanded_career_contract_loader=lambda _context, _frozen: (
            ExpandedCareerContractResult(
                contract=None,
                failures={candidate_id: "year_one_ros_fantasy_points_missing"},
            )
        ),
        expanded_career_contract_fingerprint_resolver=lambda _context: "per-player-failure-fixture-v1",
    )

    result = loader(exact_context)
    assert result.player_count == frozen.player_count
    assert result.player_coverage_failures == {
        candidate_id: "year_one_ros_fantasy_points_missing"
    }
    rows = _career_position_depth_rows(exact_state, result)
    by_id = {row["player_id"]: row for row in rows}
    assert by_id[candidate_id]["state_hash"] == exact_state.state_id
    assert by_id[candidate_id]["career_coverage_status"] == "career_authority_failure"
    assert (
        by_id[candidate_id]["career_failure_reason"]
        == "year_one_ros_fantasy_points_missing"
    )


def test_product_career_read_is_small_exact_publication_and_never_launches_work(materialized):
    import json
    _persistence, _calls, loader, context, built = materialized
    context = replace(context, publication_generation_id="served-generation")
    record = SimpleNamespace(status=IntrinsicBuildStatus.COMPLETED, contract=built,
                             league_state_id=context.league_state.state_id)
    coordinator = SimpleNamespace(current=lambda _context: record,
        request=lambda *_args: pytest.fail("GET must not launch fitting or acquisition"))
    app = FastAPI()
    install_foundation4_shadow_routes(app, runtime_store=SimpleNamespace(get=lambda _: context),
                                      loader=loader, coordinator=coordinator)
    endpoint = next(route.endpoint for route in app.routes if route.path == FOUNDATION4_CAREER_FORWARD_ENDPOINT)
    response = endpoint(SimpleNamespace(url=SimpleNamespace(path=FOUNDATION4_CAREER_FORWARD_ENDPOINT)),
                        state_id=context.league_state.state_id,
                        publication_generation_id="served-generation", user_id=context.user_id)
    assert response["publication_generation_id"] == "served-generation"
    assert response["status"] == "ready"
    assert response["career_presentation"]["presentation"]["market_inputs_used"] is False
    assert response["career_presentation"]["presentation"]["reference_count"] == 335
    assert all("uncertainty" not in row for row in response["estimates"])
    assert [row["raw_career_forward_reference"] for row in response["estimates"]] == [row.raw_career_forward_reference for row in built.estimates]
    assert len(json.dumps(response)) < len(built.model_dump_json()) / 3
    stale = endpoint(SimpleNamespace(url=SimpleNamespace(path=FOUNDATION4_CAREER_FORWARD_ENDPOINT)),
                     state_id="other-served-state", user_id=context.user_id)
    assert stale.status_code == 409
    coordinator.current = lambda _: None
    missing = endpoint(SimpleNamespace(url=SimpleNamespace(path=FOUNDATION4_CAREER_FORWARD_ENDPOINT)),
                       user_id=context.user_id)
    assert missing.status_code == 503
    assert json.loads(missing.body)["status"] == "refresh_required"


def test_concurrent_explicit_component_readers_deserialize_once(materialized, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    persistence, _calls, _first, context, _built = materialized
    loader = _loader(persistence, [])
    assert loader.restore_compatible(context) is not None
    calls = []
    original = persistence.get_reusable_artifact
    def read(key):
        calls.append(key.artifact_kind)
        return original(key)
    monkeypatch.setattr(persistence, 'get_reusable_artifact', read)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = tuple(pool.map(lambda _: loader.current_component(context), range(8)))
    assert results[0] is not None
    assert all(row is results[0] for row in results)
    assert calls.count(FOUNDATION4_Y4_Y7_ARTIFACT_KIND) == 1
    loader.clear_user_cache(context.user_id)


def test_default_career_cutoff_preserves_later_governed_forecast_publication():
    context = _context()
    from datetime import timedelta
    published_as_of = context.league_state.as_of + timedelta(hours=3)
    context = replace(context, forecast_evidence=SimpleNamespace(
        runtime_result=SimpleNamespace(evaluation_as_of=published_as_of)))
    loader = _loader(None, [])
    assert loader.pin_build_context(context).career_fingerprint_evaluation_as_of == published_as_of
    # A preserved older baseline must not move the current roster boundary back.
    context = replace(context, forecast_evidence=SimpleNamespace(
        runtime_result=SimpleNamespace(evaluation_as_of=published_as_of - timedelta(days=7))))
    assert loader.pin_build_context(context).career_fingerprint_evaluation_as_of == context.league_state.as_of


def test_component_idle_timer_releases_matrix_even_if_callback_is_retained(materialized, monkeypatch):
    import gc
    from weakref import ref
    from fsffl.product import foundation4_career_forward_runtime as runtime

    timers = []
    class RetainedTimer:
        def __init__(self, interval, callback):
            self.callback = callback
            self.daemon = False
            timers.append(self)
        def start(self):
            pass
        def cancel(self):
            pass
    monkeypatch.setattr(runtime, "Timer", RetainedTimer)
    persistence, _calls, _first, context, _contract = materialized
    loader = _loader(persistence, [])
    assert loader.restore_compatible(context) is not None
    component = loader.current_component(context)
    assert component is not None
    matrix = ref(component)
    del component
    # Keep the timer/callback alive deliberately: a real Timer also retains
    # its function after its thread exits. Neither may own the evicted matrix.
    timers[-1].callback()
    gc.collect()
    assert loader._cached_component is None
    assert loader._component_timer is None
    assert matrix() is None


def test_obsolete_component_timer_cannot_evict_replacement(materialized, monkeypatch):
    from fsffl.product import foundation4_career_forward_runtime as runtime
    timers = []
    class RetainedTimer:
        def __init__(self, interval, callback):
            self.callback = callback
            timers.append(self)
        def start(self):
            pass
        def cancel(self):
            pass
    monkeypatch.setattr(runtime, "Timer", RetainedTimer)
    persistence, _calls, _first, context, _contract = materialized
    loader = _loader(persistence, [])
    loader.restore_compatible(context)
    old = loader.current_component(context)
    loader._cached_component = None
    replacement = loader.current_component(context)
    assert replacement is not old
    timers[0].callback()
    assert loader._cached_component is replacement
    assert loader._component_timer is timers[-1]
    timers[-1].callback()
    assert loader._cached_component is None


def test_repeated_publication_restore_releases_superseded_contract_graphs():
    import gc
    from weakref import ref
    from fsffl.product.intrinsic_background import ShapleyIntrinsicBackgroundCoordinator

    class Contract:
        estimates = ()
        def __init__(self):
            self.matrix = bytearray(1024 * 1024)
    class Restorer:
        forecast_model_version = "fixture"
        def restore_compatible(self, context):
            return Contract()
        def __call__(self, context):
            raise AssertionError("restore must not build")
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader=Restorer(), max_records=2,
        intrinsic_input_fingerprint_resolver=lambda ctx: ctx.publication_generation_id,
    )
    retained = []
    for publication in range(12):
        context = replace(_context(), publication_generation_id=f"publication-{publication}")
        record = coordinator.restore_compatible(context)
        assert record is not None
        retained.append(ref(record.contract))
        assert len(coordinator._records) <= 2
    del record
    gc.collect()
    assert all(item() is None for item in retained[:-1])
    assert retained[-1]() is coordinator.current(context).contract
    assert not coordinator._futures
    # Different tenant scopes also obey the configured process retention cap.
    for user in range(8):
        context = replace(_context(), user_id=f"fixture-user-{user}",
                          publication_generation_id=f"publication-{user}")
        assert coordinator.restore_compatible(context) is not None
        assert len(coordinator._records) <= 2
    coordinator._executor.shutdown(wait=True)


def _fixture_source_manifest(context):
    from fsffl.product.p0_live_candidate_runtime import LIVE_INPUT_SOURCE_NAMES, live_source_manifest
    return live_source_manifest(captured_at=context.league_state.as_of,
        fingerprints={name: "a" * 64 for name in LIVE_INPUT_SOURCE_NAMES})


@pytest.mark.parametrize('has_component,samples,writes', [
    (False, [513], 0), (True, [513], 0), (True, [455, 513], 1),
])
def test_checkpoint_and_final_persistence_guard_each_serialization(monkeypatch, has_component, samples, writes):
    from fsffl.product import resource_coordinator as resource
    store = MemoryPersistence()
    loader = CareerIntrinsicLoader(current_intrinsic_loader=lambda _: None,
        current_intrinsic_fingerprint_resolver=lambda _: 'fixture', persistence_store=store)
    monkeypatch.delenv('FSFFL_MEMORY_LIMIT_BYTES', raising=False)
    levels = iter(samples)
    monkeypatch.setattr(resource, 'release_unused_process_memory', lambda **kw: None)
    monkeypatch.setattr(resource, 'current_rss_bytes', lambda: next(levels) * 1024 * 1024)
    monkeypatch.setattr(loader, '_component_key', lambda *args: ArtifactKey(
        artifact_kind='fixture-component', scope_kind='fixture', scope_id='fixture',
        input_fingerprint='fixture', model_version='fixture'))
    calls = []
    component = SimpleNamespace(model_dump=lambda **kw: (calls.append('component') or {}))
    def forbidden(**kwargs):
        pytest.fail('Career serialization must not allocate above the hard cap')
    contract = SimpleNamespace(model_dump=forbidden)
    with pytest.raises(MemoryError, match='hard memory limit reached before career-before-'):
        loader._persist(_context(), dependency_fingerprint='fixture',
            component=component if has_component else None, contract=contract)
    assert len(store.artifacts) == writes
    assert calls == (['component'] if writes else [])


def test_reference_checkpoint_resumes_interrupted_expansion_without_refitting(materialized, monkeypatch):
    from fsffl.product import foundation4_career_forward_runtime as runtime
    old_store, _calls, old_loader, context, accepted = materialized
    component = old_loader.current_component(context)
    assert component is not None
    monkeypatch.setattr(runtime, 'build_long_term_intrinsic_shadow', lambda *a, **k: component)
    store = MemoryPersistence()
    calls = []
    def interrupted(ctx, frozen):
        saved = store.get_reusable_artifact(loader._career_key(ctx, loader.intrinsic_input_fingerprint(ctx)))
        assert saved is not None
        assert saved.payload['_career_expansion_complete'] is False
        assert store.get_reusable_artifact(loader._component_key(ctx, component)) is not None
        assert loader.restore_compatible(ctx) is None
        calls.append('interrupted')
        raise RuntimeError('fixture interrupted expansion')
    def make(expander, current):
        return CareerIntrinsicLoader(current_intrinsic_loader=current,
            current_intrinsic_fingerprint_resolver=lambda _: 'current-fp-v1',
            persistence_store=store, expanded_career_contract_loader=expander,
            expanded_career_contract_fingerprint_resolver=lambda _: 'fixture-dynamic')
    loader = make(interrupted, lambda _: _current_intrinsic())
    with pytest.raises(RuntimeError, match='fixture interrupted expansion'):
        loader(context)
    def forbidden(*args, **kwargs):
        raise AssertionError('checkpoint resume must not recalculate frozen reference')
    monkeypatch.setattr(runtime, 'build_long_term_intrinsic_shadow', forbidden)
    def finish(ctx, frozen):
        assert frozen.model_dump() == accepted.model_dump()
        calls.append('resumed')
        return ExpandedCareerContractResult(contract=None, failures={},
            source_manifest=_fixture_source_manifest(ctx))
    resumed = make(finish, forbidden)
    result = resumed(context)
    restored = make(forbidden, forbidden).restore_compatible(context)
    assert restored == result == accepted
    assert calls == ['interrupted', 'resumed']
    assert sum(r.key.artifact_kind == FOUNDATION4_Y4_Y7_ARTIFACT_KIND for r in store.artifacts) == 1
    assert sum(r.key.artifact_kind == CAREER_INTRINSIC_ARTIFACT_KIND for r in store.artifacts) == 2


def test_completed_expansion_requires_valid_bound_live_input_manifest(materialized):
    import copy
    persistence, _calls, _base_loader, context, base = materialized
    def forbidden(*args):
        raise AssertionError("restore must not acquire or fit")
    loader = CareerIntrinsicLoader(current_intrinsic_loader=forbidden,
        current_intrinsic_fingerprint_resolver=lambda ctx: "fixture-current",
        persistence_store=persistence, expanded_career_contract_loader=forbidden,
        expanded_career_contract_fingerprint_resolver=lambda ctx: "fixture-dynamic")
    fingerprint = loader.intrinsic_input_fingerprint(context)
    key = loader._career_key(context,fingerprint)
    loader._persist(context,dependency_fingerprint=fingerprint,component=None,contract=base)
    assert loader.restore_compatible(context) is None  # missing source identities
    manifest = _fixture_source_manifest(context)
    loader._persist(context,dependency_fingerprint=fingerprint,component=None,contract=base,source_manifest=manifest)
    assert loader.restore_compatible(context) == base
    loader.clear_user_cache(context.user_id)
    payload = copy.deepcopy(persistence.get_reusable_artifact(key).payload)
    payload['_career_source_manifest']['fingerprints']['current_catalog'] = 'b' * 64
    persistence.put_artifact(ReusableArtifactRecord(key=key,payload=payload,computed_at=utc_now()))
    assert loader.restore_compatible(context) is None


def test_bound_base_only_failure_remains_retryable_and_clears_old_dynamic_errors(materialized):
    persistence, _calls, _base_loader, context, base = materialized
    loader = CareerIntrinsicLoader(current_intrinsic_loader=lambda ctx:None,
        current_intrinsic_fingerprint_resolver=lambda ctx:'current-fp-v1',
        persistence_store=persistence,expanded_career_contract_loader=lambda *args:None,
        expanded_career_contract_fingerprint_resolver=lambda ctx:'dynamic-fp-v1')
    failed = base.model_copy(update={'player_coverage_failures':{
        'sleeper:player:unsupported':'dynamic P0 acquisition failed: fixture'}})
    assert loader.retryable_incomplete_contract(failed)
    loader._persist(context,dependency_fingerprint=loader.intrinsic_input_fingerprint(context),
        component=None,contract=failed,source_manifest=_fixture_source_manifest(context))
    assert loader.restore_compatible(context) is None
    frozen = loader._restore_frozen_compatible(context)
    assert frozen.estimates == base.estimates
    assert frozen.player_coverage_failures == {}
    expanded = failed.model_copy(update={'estimates':(*failed.estimates,
        failed.estimates[0].model_copy(update={'player_id':'sleeper:player:dynamic-success'})),
        'player_count':failed.player_count+1})
    assert loader.retryable_incomplete_contract(expanded)  # batch status, not membership
    for completed in (failed, expanded):
        completed = completed.model_copy(update={'player_coverage_failures':{
            'sleeper:player:unsupported':'verified missing player-specific evidence'}})
        assert not loader.retryable_incomplete_contract(completed)
        loader.clear_user_cache(context.user_id)
        loader._persist(context,dependency_fingerprint=loader.intrinsic_input_fingerprint(context),
            component=None,contract=completed,source_manifest=_fixture_source_manifest(context))
        assert loader.restore_compatible(context) == completed
