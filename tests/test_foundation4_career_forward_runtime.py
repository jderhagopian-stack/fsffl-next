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
    validate_foundation4_expanded_acceptance_cohort,
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


def test_restore_expanded_career_artifact_returns_only_frozen_reference_base(materialized):
    persistence, _calls, _base_loader, context, base = materialized
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: None,
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=persistence,
        expanded_career_contract_loader=lambda _context, frozen: frozen,
        expanded_career_contract_fingerprint_resolver=lambda _context: "dynamic-fp-v1",
    )
    dynamic_id = "sleeper:player:restored-dynamic"
    dynamic_row = base.estimates[0].model_copy(update={"player_id": dynamic_id})
    legacy_expanded = base.model_copy(update={
        "estimates": (*base.estimates, dynamic_row),
        "player_count": base.player_count + 1,
    })
    fingerprint = loader.intrinsic_input_fingerprint(context)
    payload = legacy_expanded.model_dump(mode="json")
    payload["_foundation4_dependency_fingerprint"] = fingerprint
    persistence.put_artifact(ReusableArtifactRecord(
        key=loader._career_key(context, fingerprint),
        payload=payload,
        computed_at=utc_now(),
    ))

    restored = loader.restore_compatible(context)

    assert restored is not None
    assert restored.player_count == base.player_count
    assert dynamic_id not in {row.player_id for row in restored.estimates}


def test_coordinator_restore_reexpands_exact_state_dynamic_roster(materialized):
    persistence, _calls, _base_loader, context, base = materialized
    candidate_id = "sleeper:player:restart-dynamic"
    frozen_row = next(row for row in base.estimates if row.position.value == "QB")
    frozen_tail = frozen_row.uncertainty.terminal_y8_plus
    candidate_tail = frozen_tail.model_copy(update={
        "player_id": candidate_id,
        "features": frozen_tail.features.model_copy(update={"player_id": candidate_id}),
    })
    candidate_row = frozen_row.model_copy(update={
        "player_id": candidate_id,
        "uncertainty": frozen_row.uncertainty.model_copy(
            update={"terminal_y8_plus": candidate_tail}
        ),
    })
    expanded = base.model_copy(update={
        "input_fingerprint": "restart-expanded-fixture",
        "estimates": (*base.estimates, candidate_row),
        "player_count": base.player_count + 1,
    })
    player = Player(
        player_id=candidate_id,
        full_name="Restart Fixture",
        position=Position.QB,
    )
    roster = RosterEntry(player_id=candidate_id, slot=RosterSlot.BENCH)
    exact_state = context.league_state.model_copy(update={
        "players": (*context.league_state.players, player),
        "team_states": (TeamState(team_id="team-1", roster=(roster,)),),
    })
    exact_context = UserRuntimeContext(user_id=context.user_id, league_state=exact_state)
    loader = CareerIntrinsicLoader(
        current_intrinsic_loader=lambda _context: _current_intrinsic(),
        current_intrinsic_fingerprint_resolver=lambda _context: "current-fp-v1",
        persistence_store=persistence,
        expanded_career_contract_loader=lambda _context, _frozen: expanded,
        expanded_career_contract_fingerprint_resolver=lambda _context: "restart-dynamic-v1",
    )
    fingerprint = loader.intrinsic_input_fingerprint(exact_context)
    payload = base.model_dump(mode="json")
    payload["_foundation4_dependency_fingerprint"] = fingerprint
    persistence.put_artifact(ReusableArtifactRecord(
        key=loader._career_key(exact_context, fingerprint),
        payload=payload,
        computed_at=utc_now(),
    ))
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        intrinsic_input_fingerprint_resolver=loader.intrinsic_input_fingerprint,
    )

    restored = coordinator.restore_compatible_staged(exact_context)

    assert restored is not None
    assert restored.status == IntrinsicBuildStatus.COMPLETED
    assert restored.contract is not None
    assert candidate_id in {row.player_id for row in restored.contract.estimates}


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
    assert "coordinator.request(context)" in route


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
            return None

        def request(self, _context):
            return record

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
    assert request_calls


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
    state_player = SimpleNamespace(
        player_id=candidate_id,
        position=SimpleNamespace(value="QB"),
    )
    roster_entry = SimpleNamespace(
        player_id=candidate_id,
        slot=SimpleNamespace(value="BENCH"),
    )
    team_state = SimpleNamespace(team_id="team-1", roster=(roster_entry,))
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
