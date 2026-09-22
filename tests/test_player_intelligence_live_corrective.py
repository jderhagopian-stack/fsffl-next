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
)
from fsffl.product.player_intelligence_routes import _validated_player_id
from fsffl.product.runtime import UserRuntimeContext


def _context() -> UserRuntimeContext:
    return UserRuntimeContext(
        user_id="u",
        league_state=cast(Any, SimpleNamespace(state_id="state")),
    )


def test_intrinsic_background_timeout_fails_closed_but_late_build_can_complete() -> None:
    started = Event()
    release = Event()

    def loader(_context: UserRuntimeContext):
        started.set()
        if not release.wait(timeout=2.0):
            raise RuntimeError("fixture loader release timed out")
        return cast(Any, SimpleNamespace())

    coordinator = ShapleyIntrinsicBackgroundCoordinator(
        loader,
        max_workers=1,
        timeout_seconds=0.03,
    )
    context = _context()
    try:
        first = coordinator.request(context)
        assert first.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }
        assert started.wait(timeout=1.0)
        sleep(0.05)

        timed_out = coordinator.request(context)
        assert timed_out.status == IntrinsicBuildStatus.FAILED
        assert (timed_out.error or "").startswith("TimeoutError:")
        payload = intrinsic_failure_payload(timed_out)
        assert payload["status"] == "unavailable"
        assert payload["retry_after_ms"] is None
    finally:
        release.set()

    deadline = monotonic() + 1.0
    while monotonic() < deadline:
        current = coordinator.current(context)
        if current is not None and current.status == IntrinsicBuildStatus.COMPLETED:
            break
        sleep(0.01)
    else:
        pytest.fail("late Intrinsic build did not become reusable after bounded response timeout")


def test_intrinsic_background_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        ShapleyIntrinsicBackgroundCoordinator(
            lambda _context: cast(Any, SimpleNamespace()),
            timeout_seconds=0,
        )


@pytest.mark.parametrize("player_id", ("", " ", "null", "NULL", "undefined", "none"))
def test_player_intelligence_rejects_invalid_player_ids(player_id: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _validated_player_id(player_id)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Player Intelligence requires a valid player id"


def test_player_intelligence_accepts_real_player_id() -> None:
    assert _validated_player_id(" sleeper:player:123 ") == "sleeper:player:123"
