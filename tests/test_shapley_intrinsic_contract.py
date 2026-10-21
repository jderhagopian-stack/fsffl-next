from __future__ import annotations

import gc
from types import SimpleNamespace
from typing import cast
from weakref import ref

import pytest
from fastapi import FastAPI

from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.shapley_intrinsic_routes import install_shapley_intrinsic_routes
from fsffl.state.models import Position
from fsffl.value.live_intrinsic_calendar import (
    CompletedSourceI1Coordinate,
    LiveCalendarShapleyResult,
    LiveIntrinsicCalendarResult,
    LiveThreeYearPlayerCoordinate,
    LiveYearOneCoordinate,
)
from fsffl.value.shapley_intrinsic import IntrinsicShapleyEstimate
from fsffl.value.shapley_intrinsic_contract import (
    CompletedSourceFactProvenance,
    ShapleyIntrinsicAvailability,
    build_shapley_intrinsic_contract,
    build_unavailable_shapley_intrinsic_contract,
)


def _i1_result(points: float, *, path: str = "reduced") -> I1ForecastResult:
    probabilities = {state: 0.0 for state in STATE_NAMES}
    probabilities["starter"] = 1.0
    state_means = {state: 0.0 for state in STATE_NAMES}
    state_means["starter"] = points
    return I1ForecastResult(
        probabilities=probabilities,
        persistence_probability=1.0,
        anticipated_points=points,
        state_means=state_means,
        evidence_path=path,
    )


def _result() -> LiveCalendarShapleyResult:
    coordinate = LiveThreeYearPlayerCoordinate(
        player_id="p1",
        position=Position.WR,
        evaluation_season=2026,
        year_1=LiveYearOneCoordinate(
            target_season=2026,
            anticipated_points=155.0,
            stddev=12.0,
            source="governed-live-ensemble",
            model_version="live-forecast-v1",
        ),
        diagnostic_h1=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=1,
            target_season=2026,
            result=_i1_result(999.0),
            diagnostic_only=True,
        ),
        year_2=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=2,
            target_season=2027,
            result=_i1_result(140.0),
            diagnostic_only=False,
        ),
        year_3=CompletedSourceI1Coordinate(
            source_season=2025,
            horizon=3,
            target_season=2028,
            result=_i1_result(120.0),
            diagnostic_only=False,
        ),
    )
    calendar = LiveIntrinsicCalendarResult(
        forecasts=(coordinate,),
        evaluation_season=2026,
        completed_source_season=2025,
    )
    year_1 = 10.0
    year_2 = 8.0
    year_3 = 6.0
    estimate = IntrinsicShapleyEstimate(
        player_id="p1",
        value=year_1 + 0.85 * year_2 + (0.85**2) * year_3,
        year_1_shapley=year_1,
        year_2_expected_shapley=year_2,
        year_3_expected_shapley=year_3,
    )
    return LiveCalendarShapleyResult(calendar=calendar, estimates=(estimate,))


def test_contract_exposes_raw_horizon_contributions_and_diagnostic_h1_without_double_counting() -> None:
    contract = build_shapley_intrinsic_contract(
        _result(),
        completed_source_provenance=CompletedSourceFactProvenance(
            source_version="canonical-facts-test-v1",
            schema_version="i1-current-source-facts-v2:direct-h3",
            providers=("provider-a",),
            fact_family_coverage={
                "roster_continuity": False,
                "injury_practice": False,
                "participation_snaps": False,
                "role_opportunity": True,
            },
        ),
        missing_required_fact_families=("roster_continuity",),
    )

    assert contract.status == ShapleyIntrinsicAvailability.DEGRADED
    assert contract.target_years == (2026, 2027, 2028)
    assert contract.display_scaling_applied is False
    assert contract.diagnostic_h1_included is False
    player = contract.estimates[0]
    assert player.diagnostic_h1.anticipated_points == 999.0
    assert player.diagnostic_h1.included_in_intrinsic is False
    assert player.diagnostic_h1.provenance.direct_i1_horizon == 1
    assert player.diagnostic_h1.provenance.diagnostic_only is True
    assert [item.provenance.direct_i1_horizon for item in player.contributions] == [None, 2, 3]
    assert [item.target_season for item in player.contributions] == [2026, 2027, 2028]
    assert sum(item.discounted_contribution for item in player.contributions) == pytest.approx(
        player.raw_intrinsic_value
    )
    assert player.raw_intrinsic_value != pytest.approx(999.0)


def test_unavailable_contract_is_explicit_and_has_no_estimates() -> None:
    contract = build_unavailable_shapley_intrinsic_contract(
        evaluation_season=2026,
        reason="missing canonical facts",
        missing_required_fact_families=("completed_source_i1_facts",),
    )
    assert contract.status == ShapleyIntrinsicAvailability.UNAVAILABLE
    assert contract.target_years == (2026, 2027, 2028)
    assert contract.estimates == ()
    assert contract.coverage.missing_required_fact_families == ("completed_source_i1_facts",)


def test_api_route_is_versioned_and_fail_closed_without_completed_source_loader() -> None:
    class _Store:
        def get(self, user_id: str):
            return SimpleNamespace(
                user_id=user_id,
                league_state=SimpleNamespace(league=SimpleNamespace(season=2026)),
            )

    app = FastAPI()
    install_shapley_intrinsic_routes(
        app,
        runtime_store=cast(PrivateBetaRuntimeStore, _Store()),
    )
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/value/intrinsic-shapley-v1"
    )
    payload = route.endpoint(user_id="beta-user")
    assert payload["status"] == "unavailable"
    assert payload["display_scaling_applied"] is False
    assert payload["diagnostic_h1_included"] is False
    assert payload["coverage"]["missing_required_fact_families"] == ["completed_source_i1_facts"]



def test_reduced_future_evidence_path_is_provenance_not_availability_gate() -> None:
    contract = build_shapley_intrinsic_contract(
        _result(),
        completed_source_provenance=CompletedSourceFactProvenance(
            source_version="canonical-facts-test-v1",
            providers=("provider-a", "provider-b"),
            fact_family_coverage={
                "roster_continuity": False,
                "injury_practice": False,
                "participation_snaps": False,
                "role_opportunity": True,
            },
        ),
        missing_required_fact_families=(),
        forecast_model_version="forecast-vnext-fixture",
    )

    assert contract.status == ShapleyIntrinsicAvailability.READY
    assert contract.coverage.player_count == 1
    assert contract.coverage.reduced_or_fallback_players == 1
    assert contract.coverage.missing_required_fact_families == ()
    assert contract.completed_source_provenance is not None
    assert (
        contract.completed_source_provenance.fact_family_coverage["injury_practice"]
        is False
    )


def test_released_current_owner_restores_only_the_durable_contract():
    from fsffl.product.intrinsic_background import ShapleyIntrinsicBackgroundCoordinator
    from fsffl.product.resource_coordinator import HeavyWorkCoordinator

    class Loader:
        forecast_model_version = "fixture-forecast-v1"

        def __init__(self):
            self.cached = None
            self.restore_calls = 0

        def restore_compatible(self, _context):
            self.restore_calls += 1
            if self.cached is None:
                self.cached = build_shapley_intrinsic_contract(_result())
            return self.cached

        def clear_user_cache(self, _user_id):
            self.cached = None

    context = SimpleNamespace(
        user_id="test-user",
        league_state=SimpleNamespace(
            state_id="state-1",
            league=SimpleNamespace(league_id="league-1", season=2026),
        ),
    )
    loader = Loader()
    heavy_work = HeavyWorkCoordinator()
    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        intrinsic_input_fingerprint_resolver=lambda _context: "current-fp",
        forecast_coordinate_resolver=lambda _context: "fixture-forecast-v1",
        heavy_work_coordinator=heavy_work,
    )
    try:
        owned = coordinator.restore_compatible(context)
        assert owned is not None and owned.contract is not None
        current = owned.contract
        current_ref = ref(current)

        assert coordinator.release_completed_contract(context, current)
        loader.clear_user_cache(context.user_id)
        with heavy_work.claim(kind="career", key="career-build"):
            released_record = coordinator.current(context)
            assert released_record is not None and released_record.contract is None
        del released_record, current, owned
        gc.collect()
        assert current_ref() is None

        # Direct request() callers must also restore released completed
        # contracts; several product routes do not use current().
        with heavy_work.claim(kind="career", key="career-build"):
            waiting = coordinator.request(context)
            assert waiting.status.value == "completed"
            assert waiting.contract is None
            assert loader.restore_calls == 1

            class RuntimeStore:
                def get(self, _user_id):
                    return context

            app = FastAPI()
            install_shapley_intrinsic_routes(
                app,
                runtime_store=cast(PrivateBetaRuntimeStore, RuntimeStore()),
                contract_loader=lambda _context: None,
                background_coordinator=coordinator,
            )
            route = next(
                route for route in app.routes
                if getattr(route, "path", None) == "/api/value/intrinsic-shapley-v1"
            )
            response = route.endpoint(user_id="test-user")
            assert response.status_code == 202

        restored = coordinator.request(context)
        assert restored is not None and restored.status.value == "completed"
        assert restored.contract is not None
        assert restored.contract.estimates[0].raw_intrinsic_value == pytest.approx(
            10.0 + 0.85 * 8.0 + (0.85**2) * 6.0
        )
        assert coordinator.request(context).contract is restored.contract
        assert loader.restore_calls == 2
    finally:
        coordinator._executor.shutdown(wait=True)
