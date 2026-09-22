from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Callable

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .runtime import UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]
ForecastCoordinateResolver = Callable[[UserRuntimeContext], str]
DEFAULT_INTRINSIC_RESPONSE_BUDGET_SECONDS = 30.0
# The hard watchdog is deliberately a distinct operational guard, not a browser
# response timeout.  Ten minutes is 20x the response budget and comfortably above
# the observed hosted cold-build crossing at 31.396s while still bounding a truly
# wedged worker.
DEFAULT_INTRINSIC_HARD_WATCHDOG_SECONDS = 600.0
_logger = logging.getLogger("fsffl.product.performance")


class IntrinsicBuildStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class IntrinsicBuildRecord:
    user_id: str
    league_state_id: str
    forecast_coordinate: str
    status: IntrinsicBuildStatus
    created_at: datetime
    updated_at: datetime
    response_budget_exceeded: bool = False
    contract: ShapleyIntrinsicContract | None = None
    error: str | None = None


class ShapleyIntrinsicBackgroundCoordinator:
    """Coalesce cold Intrinsic work away from fragile browser requests.

    Model authority stays entirely in the supplied Shapley contract loader. This
    coordinator owns only execution lifecycle, coordinate-aware reuse and a
    separately named hard watchdog. Crossing the browser/API response budget does
    not mark valid background work failed.
    """

    def __init__(
        self,
        loader: IntrinsicContractLoader,
        *,
        max_workers: int = 1,
        response_budget_seconds: float = DEFAULT_INTRINSIC_RESPONSE_BUDGET_SECONDS,
        hard_watchdog_seconds: float = DEFAULT_INTRINSIC_HARD_WATCHDOG_SECONDS,
        forecast_coordinate_resolver: ForecastCoordinateResolver | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        # timeout_seconds is retained as a compatibility alias for older callers,
        # but its semantics are now the response budget only.
        if timeout_seconds is not None:
            response_budget_seconds = float(timeout_seconds)
        if response_budget_seconds <= 0:
            raise ValueError("Intrinsic response budget must be positive")
        if hard_watchdog_seconds <= response_budget_seconds:
            raise ValueError(
                "Intrinsic hard watchdog must exceed the response budget"
            )
        self._loader = loader
        self._response_budget_seconds = float(response_budget_seconds)
        self._hard_watchdog_seconds = float(hard_watchdog_seconds)
        self._forecast_coordinate_resolver = (
            forecast_coordinate_resolver or self._default_forecast_coordinate
        )
        self._lock = RLock()
        self._records: dict[tuple[str, str, str], IntrinsicBuildRecord] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fsffl-intrinsic",
        )

    def _default_forecast_coordinate(self, context: UserRuntimeContext) -> str:
        value = getattr(self._loader, "forecast_model_version", None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        # A stable fallback keeps generic/test loaders coalesced by authoritative
        # State without pretending to know a Forecast model coordinate.
        return "forecast-coordinate:unspecified"

    def _key(self, context: UserRuntimeContext) -> tuple[str, str, str]:
        if context.league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        coordinate = str(self._forecast_coordinate_resolver(context)).strip()
        if not coordinate:
            raise ValueError("Shapley Intrinsic Forecast coordinate cannot be empty")
        return context.user_id, context.league_state.state_id, coordinate

    def request(self, context: UserRuntimeContext) -> IntrinsicBuildRecord:
        key = self._key(context)
        now = datetime.now(UTC)
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                if existing.status in {
                    IntrinsicBuildStatus.QUEUED,
                    IntrinsicBuildStatus.RUNNING,
                }:
                    elapsed = (now - existing.created_at).total_seconds()
                    if elapsed >= self._hard_watchdog_seconds:
                        error = (
                            "HardWatchdogError: governed FSFFL Intrinsic preparation "
                            f"exceeded {self._hard_watchdog_seconds:.1f}s background "
                            "lifetime guard."
                        )
                        existing = replace(
                            existing,
                            status=IntrinsicBuildStatus.FAILED,
                            contract=None,
                            error=error,
                            updated_at=now,
                        )
                        self._records[key] = existing
                        _logger.error(
                            "FSFFL Intrinsic hard watchdog fired user=%s state=%s "
                            "forecast=%s elapsed=%.3fs watchdog=%.3fs",
                            existing.user_id,
                            existing.league_state_id,
                            existing.forecast_coordinate,
                            elapsed,
                            self._hard_watchdog_seconds,
                        )
                    elif (
                        elapsed >= self._response_budget_seconds
                        and not existing.response_budget_exceeded
                    ):
                        existing = replace(
                            existing,
                            response_budget_exceeded=True,
                            updated_at=now,
                        )
                        self._records[key] = existing
                        _logger.info(
                            "FSFFL Intrinsic response budget crossed; background "
                            "build remains active user=%s state=%s forecast=%s "
                            "elapsed=%.3fs response_budget=%.3fs",
                            existing.user_id,
                            existing.league_state_id,
                            existing.forecast_coordinate,
                            elapsed,
                            self._response_budget_seconds,
                        )
                return existing

            # Drop stale same-user records when authoritative State or Forecast
            # coordinate advances. The durable loader cache remains responsible
            # for exact completed-contract reuse.
            stale = [
                item
                for item in self._records
                if item[0] == context.user_id and item != key
            ]
            for item in stale:
                self._records.pop(item, None)

            record = IntrinsicBuildRecord(
                user_id=context.user_id,
                league_state_id=key[1],
                forecast_coordinate=key[2],
                status=IntrinsicBuildStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            self._records[key] = record
            self._executor.submit(self._run, key, context)
            return record

    def _set(
        self,
        key: tuple[str, str, str],
        *,
        status: IntrinsicBuildStatus,
        contract: ShapleyIntrinsicContract | None = None,
        error: str | None = None,
    ) -> IntrinsicBuildRecord | None:
        with self._lock:
            current = self._records.get(key)
            if current is None:
                return None
            updated = replace(
                current,
                status=status,
                contract=contract,
                error=error,
                updated_at=datetime.now(UTC),
            )
            self._records[key] = updated
            return updated

    def _run(
        self,
        key: tuple[str, str, str],
        context: UserRuntimeContext,
    ) -> None:
        running = self._set(key, status=IntrinsicBuildStatus.RUNNING)
        if running is None:
            return
        try:
            contract = self._loader(context)
        except Exception as exc:
            failed = self._set(
                key,
                status=IntrinsicBuildStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
            if failed is not None:
                _logger.warning(
                    "FSFFL Intrinsic background build failed user=%s state=%s "
                    "forecast=%s error=%s",
                    failed.user_id,
                    failed.league_state_id,
                    failed.forecast_coordinate,
                    failed.error,
                )
            return
        completed = self._set(
            key,
            status=IntrinsicBuildStatus.COMPLETED,
            contract=contract,
        )
        if completed is not None:
            elapsed = (completed.updated_at - completed.created_at).total_seconds()
            _logger.info(
                "FSFFL Intrinsic background build completed user=%s state=%s "
                "forecast=%s elapsed=%.3fs",
                completed.user_id,
                completed.league_state_id,
                completed.forecast_coordinate,
                elapsed,
            )

    def current(self, context: UserRuntimeContext) -> IntrinsicBuildRecord | None:
        key = self._key(context)
        with self._lock:
            return self._records.get(key)


def intrinsic_loading_payload(
    record: IntrinsicBuildRecord,
) -> dict[str, object]:
    return {
        "status": "loading",
        "message": (
            "Governed FSFFL Intrinsic is being prepared server-side. "
            "This page remains usable while the calculation completes."
        ),
        "league_state_id": record.league_state_id,
        "forecast_coordinate": record.forecast_coordinate,
        "build_status": record.status.value,
        "response_budget_exceeded": record.response_budget_exceeded,
        "retry_after_ms": 1500,
        "started_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def intrinsic_failure_payload(
    record: IntrinsicBuildRecord,
) -> dict[str, object]:
    return {
        "status": "unavailable",
        "message": (
            "Governed FSFFL Intrinsic could not be prepared for the current "
            f"league/Forecast coordinate: {record.error or 'unknown server-side build error'}"
        ),
        "league_state_id": record.league_state_id,
        "forecast_coordinate": record.forecast_coordinate,
        "build_status": record.status.value,
        "retry_after_ms": None,
        "started_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
