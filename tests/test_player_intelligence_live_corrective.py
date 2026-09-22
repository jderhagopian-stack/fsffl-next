from __future__ import annotations

from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException

from fsffl.product.intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
    intrinsic_failure_payload,
    intrinsic_loading_payload,
)
from fsffl.product.player_intelligence_routes import _validated_player_id
from fsffl.product.runtime import UserRuntimeContext


def _context() -> UserRuntimeContext:
    return UserRuntimeContext(
        user_id="u",
        league_state=cast(Any, SimpleNamespace(state_id="state")),
    )


def _wait_for(
    coordinator: ShapleyIntrinsicBackgroundCoordinator,
    context: UserRuntimeContext,
    status: IntrinsicBuildStatus,
    *,
    timeout: float = 1.0,
):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        current = coordinator.current(context)
        if current is not None and current.status == status:
            return current
        sleep(0.005)
    pytest.fail(f"Intrinsic build did not reach {status.value}")


def test_intrinsic_response_budget_crossing_stays_loading_and_late_build_completes() -> None:
    started = Event()
    release = Event()
    calls = 0

    def loader(_context: UserRuntimeContext):
        nonlocal calls
        calls += 1
        started.set()
        if not release.wait(timeout=2.0):
            raise RuntimeError("fixture loader release timed out")
        return cast(Any, SimpleNamespace(forecast_model_version="forecast-v1"))

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        response_budget_seconds=0.02,
        hard_watchdog_seconds=1.0,
    )
    context = _context()
    first = coordinator.request(context)
    assert first.status in {
        IntrinsicBuildStatus.QUEUED,
        IntrinsicBuildStatus.RUNNING,
    }
    assert started.wait(timeout=1.0)
    sleep(0.04)

    after_budget = coordinator.request(context)
    assert after_budget.status == IntrinsicBuildStatus.RUNNING
    assert after_budget.response_budget_exceeded is True
    assert calls == 1
    loading = intrinsic_loading_payload(after_budget)
    assert loading["status"] == "loading"
    assert loading["response_budget_exceeded"] is True

    release.set()
    completed = _wait_for(
        coordinator,
        context,
        IntrinsicBuildStatus.COMPLETED,
    )
    assert completed.contract is not None
    assert calls == 1


def test_repeated_intrinsic_polls_coalesce_duplicate_work() -> None:
    started = Event()
    release = Event()
    calls = 0

    def loader(_context: UserRuntimeContext):
        nonlocal calls
        calls += 1
        started.set()
        release.wait(timeout=1.0)
        return cast(Any, SimpleNamespace())

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        response_budget_seconds=0.02,
        hard_watchdog_seconds=1.0,
    )
    context = _context()
    coordinator.request(context)
    assert started.wait(timeout=1.0)
    for _ in range(20):
        record = coordinator.request(context)
        assert record.status in {
            IntrinsicBuildStatus.RUNNING,
            IntrinsicBuildStatus.QUEUED,
        }
    assert calls == 1
    release.set()
    _wait_for(coordinator, context, IntrinsicBuildStatus.COMPLETED)
    assert calls == 1


def test_forecast_coordinate_change_invalidates_once_and_builds_once() -> None:
    coordinate = {"value": "forecast-v1"}
    calls: list[str] = []

    def loader(_context: UserRuntimeContext):
        calls.append(coordinate["value"])
        return cast(Any, SimpleNamespace(forecast_model_version=coordinate["value"]))

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        response_budget_seconds=0.05,
        hard_watchdog_seconds=1.0,
        forecast_coordinate_resolver=lambda _context: coordinate["value"],
    )
    context = _context()
    coordinator.request(context)
    first = _wait_for(coordinator, context, IntrinsicBuildStatus.COMPLETED)
    assert first.forecast_coordinate == "forecast-v1"
    assert calls == ["forecast-v1"]

    assert coordinator.request(context) is first
    assert calls == ["forecast-v1"]

    coordinate["value"] = "forecast-v2"
    second_start = coordinator.request(context)
    assert second_start.forecast_coordinate == "forecast-v2"
    second = _wait_for(coordinator, context, IntrinsicBuildStatus.COMPLETED)
    assert second.forecast_coordinate == "forecast-v2"
    assert calls == ["forecast-v1", "forecast-v2"]
    assert coordinator.request(context) is second
    assert calls == ["forecast-v1", "forecast-v2"]


def test_hard_watchdog_is_distinct_from_response_budget_and_can_fail_closed() -> None:
    started = Event()
    release = Event()

    def loader(_context: UserRuntimeContext):
        started.set()
        release.wait(timeout=1.0)
        return cast(Any, SimpleNamespace())

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        response_budget_seconds=0.01,
        hard_watchdog_seconds=0.05,
    )
    context = _context()
    coordinator.request(context)
    assert started.wait(timeout=1.0)
    sleep(0.02)
    after_response_budget = coordinator.request(context)
    assert after_response_budget.status == IntrinsicBuildStatus.RUNNING
    assert after_response_budget.response_budget_exceeded is True

    sleep(0.05)
    watched = coordinator.request(context)
    assert watched.status == IntrinsicBuildStatus.FAILED
    assert (watched.error or "").startswith("HardWatchdogError:")
    payload = intrinsic_failure_payload(watched)
    assert payload["status"] == "unavailable"
    assert payload["retry_after_ms"] is None
    release.set()


def test_true_intrinsic_loader_exception_still_fails_closed() -> None:
    def loader(_context: UserRuntimeContext):
        raise RuntimeError("fixture model/data failure")

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        response_budget_seconds=0.05,
        hard_watchdog_seconds=1.0,
    )
    context = _context()
    coordinator.request(context)
    failed = _wait_for(coordinator, context, IntrinsicBuildStatus.FAILED)
    assert failed.error == "RuntimeError: fixture model/data failure"
    assert intrinsic_failure_payload(failed)["status"] == "unavailable"


def test_intrinsic_lifecycle_budgets_must_be_ordered_and_positive() -> None:
    with pytest.raises(ValueError, match="response budget"):
        ShapleyIntrinsicBackgroundCoordinator(
            lambda _context: cast(Any, SimpleNamespace()),
            response_budget_seconds=0,
        )
    with pytest.raises(ValueError, match="hard watchdog"):
        ShapleyIntrinsicBackgroundCoordinator(
            lambda _context: cast(Any, SimpleNamespace()),
            response_budget_seconds=1.0,
            hard_watchdog_seconds=1.0,
        )


@pytest.mark.parametrize("player_id", ("", " ", "null", "NULL", "undefined", "none"))
def test_player_intelligence_rejects_invalid_player_ids(player_id: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validated_player_id(player_id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Player Intelligence requires a valid player id"


def test_player_intelligence_accepts_real_player_id() -> None:
    assert _validated_player_id(" sleeper:player:123 ") == "sleeper:player:123"
