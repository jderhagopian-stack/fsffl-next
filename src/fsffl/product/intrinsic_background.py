from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from time import monotonic, sleep
from typing import Callable

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .resource_coordinator import HeavyWorkCoordinator
from .runtime import UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]
ForecastCoordinateResolver = Callable[[UserRuntimeContext], str]
IntrinsicInputFingerprintResolver = Callable[[UserRuntimeContext], str]
IntrinsicOwnershipValidator = Callable[[UserRuntimeContext], bool]
DEFAULT_INTRINSIC_RESPONSE_BUDGET_SECONDS = 30.0
# The hard watchdog is deliberately a distinct operational guard, not a browser
# response timeout.  Ten minutes is 20x the response budget and comfortably above
# the observed hosted cold-build crossing at 31.396s while still bounding a truly
# wedged worker.
DEFAULT_INTRINSIC_HARD_WATCHDOG_SECONDS = 600.0
_logger = logging.getLogger("fsffl.product.performance")


class IntrinsicBuildSuperseded(RuntimeError):
    """An older State's Intrinsic waiter lost lifecycle ownership."""


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
    intrinsic_input_fingerprint: str
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
        intrinsic_input_fingerprint_resolver: IntrinsicInputFingerprintResolver | None = None,
        timeout_seconds: float | None = None,
        heavy_work_coordinator: HeavyWorkCoordinator | None = None,
        ownership_validator: IntrinsicOwnershipValidator | None = None,
        max_records: int = 8,
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
        self._intrinsic_input_fingerprint_resolver = (
            intrinsic_input_fingerprint_resolver
            or getattr(loader, "intrinsic_input_fingerprint", None)
            or self._default_intrinsic_input_fingerprint
        )
        if max_records < 2:
            raise ValueError("Intrinsic max_records must be at least 2")
        self._heavy_work_coordinator = heavy_work_coordinator
        self._ownership_validator = ownership_validator
        self._max_records = int(max_records)
        self._lock = RLock()
        self._records: dict[tuple[str, str, str], IntrinsicBuildRecord] = {}
        self._futures: dict[tuple[str, str, str], Future[None]] = {}
        self._user_epochs: dict[str, int] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fsffl-intrinsic",
        )

    def _default_forecast_coordinate(self, context: UserRuntimeContext) -> str:
        value = getattr(self._loader, "forecast_model_version", None)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "forecast-coordinate:unspecified"

    def _default_intrinsic_input_fingerprint(self, context: UserRuntimeContext) -> str:
        if context.league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        # Compatibility fallback for generic/test loaders. Production injects the
        # dependency-scoped resolver from PrivateBetaShapleyContractLoader.
        coordinate = str(self._forecast_coordinate_resolver(context)).strip()
        return f"state:{context.league_state.state_id}|forecast:{coordinate}"

    def _key(self, context: UserRuntimeContext) -> tuple[str, str, str]:
        if context.league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        fingerprint = str(
            self._intrinsic_input_fingerprint_resolver(context)
        ).strip()
        if not fingerprint:
            raise ValueError("Shapley Intrinsic input fingerprint cannot be empty")
        league = getattr(context.league_state, "league", None)
        league_id = str(
            getattr(league, "league_id", None)
            or getattr(context.league_state, "state_id", "unknown")
        )
        return (
            context.user_id,
            league_id,
            fingerprint,
        )

    def restore_compatible(
        self,
        context: UserRuntimeContext,
    ) -> IntrinsicBuildRecord | None:
        """Seed completed lifecycle state from a durable compatible contract."""

        restorer = getattr(self._loader, "restore_compatible", None)
        if not callable(restorer):
            return None
        if (
            self._ownership_validator is not None
            and not self._ownership_validator(context)
        ):
            return None
        with self._lock:
            expected_epoch = self._user_epochs.get(context.user_id, 0)
        key = self._key(context)
        with self._lock:
            if self._user_epochs.get(context.user_id, 0) != expected_epoch:
                return None
            if (
                self._ownership_validator is not None
                and not self._ownership_validator(context)
            ):
                return None
            existing = self._records.get(key)
            if (
                existing is not None
                and existing.status == IntrinsicBuildStatus.COMPLETED
                and existing.contract is not None
            ):
                if (
                    context.league_state is not None
                    and existing.league_state_id != context.league_state.state_id
                ):
                    existing = replace(
                        existing,
                        league_state_id=context.league_state.state_id,
                        updated_at=datetime.now(UTC),
                    )
                    self._records[key] = existing
                return existing
        contract = restorer(context)
        if contract is None:
            return None
        if context.league_state is None:
            return None
        now = datetime.now(UTC)
        record = IntrinsicBuildRecord(
            user_id=context.user_id,
            league_state_id=context.league_state.state_id,
            forecast_coordinate=str(
                self._forecast_coordinate_resolver(context)
            ).strip(),
            intrinsic_input_fingerprint=key[2],
            status=IntrinsicBuildStatus.COMPLETED,
            created_at=now,
            updated_at=now,
            contract=contract,
        )
        with self._lock:
            if self._user_epochs.get(context.user_id, 0) != expected_epoch:
                return None
            self._records[key] = record
        _logger.info(
            "FSFFL Intrinsic restored from compatible persisted contract user=%s state=%s forecast=%s fingerprint=%s estimates=%s",
            record.user_id,
            record.league_state_id,
            record.forecast_coordinate,
            record.intrinsic_input_fingerprint,
            len(contract.estimates),
        )
        return record


    def restore_compatible_staged(
        self,
        context: UserRuntimeContext,
    ) -> IntrinsicBuildRecord | None:
        """Restore durable Intrinsic only inside the process heavy-work lane.

        Foreground first-load/readiness calls must not deserialize a persisted
        Intrinsic contract while fresh Forecast acquisition is preparing. The
        background reconciliation/startup restore paths call this method instead,
        preserving exact reuse while staging its transient memory footprint.
        """

        if self._heavy_work_coordinator is None:
            return self.restore_compatible(context)
        if context.league_state is None:
            return None
        with self._heavy_work_coordinator.claim(
            kind="intrinsic_restore",
            key=f"{context.user_id}:{context.league_state.state_id}",
        ):
            return self.restore_compatible(context)

    def request(
        self,
        context: UserRuntimeContext,
        *,
        expected_epoch: int | None = None,
    ) -> IntrinsicBuildRecord:
        if (
            self._ownership_validator is not None
            and not self._ownership_validator(context)
        ):
            raise IntrinsicBuildSuperseded(
                "Intrinsic context no longer owns the active execution State"
            )
        with self._lock:
            request_epoch = (
                self._user_epochs.get(context.user_id, 0)
                if expected_epoch is None
                else expected_epoch
            )
        key = self._key(context)
        now = datetime.now(UTC)
        with self._lock:
            current_epoch = self._user_epochs.get(context.user_id, 0)
            if current_epoch != request_epoch:
                raise IntrinsicBuildSuperseded(
                    "Intrinsic lifecycle was superseded by a State transition"
                )
            if (
                self._ownership_validator is not None
                and not self._ownership_validator(context)
            ):
                raise IntrinsicBuildSuperseded(
                    "Intrinsic context no longer owns the active execution State"
                )
            existing = self._records.get(key)
            if existing is not None:
                if (
                    context.league_state is not None
                    and existing.league_state_id != context.league_state.state_id
                ):
                    existing = replace(
                        existing,
                        league_state_id=context.league_state.state_id,
                    )
                    self._records[key] = existing
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
                if item[0] == context.user_id
                and item[1] == key[1]
                and item != key
            ]
            for item in stale:
                self._records.pop(item, None)

            terminal = sorted(
                (
                    (record_key, item)
                    for record_key, item in self._records.items()
                    if record_key != key
                    and item.status in {
                        IntrinsicBuildStatus.COMPLETED,
                        IntrinsicBuildStatus.FAILED,
                    }
                ),
                key=lambda pair: pair[1].updated_at,
            )
            while len(self._records) >= self._max_records and terminal:
                stale_key, _ = terminal.pop(0)
                self._records.pop(stale_key, None)

            coordinate = str(self._forecast_coordinate_resolver(context)).strip()
            if not coordinate:
                raise ValueError("Shapley Intrinsic Forecast coordinate cannot be empty")
            record = IntrinsicBuildRecord(
                user_id=context.user_id,
                league_state_id=context.league_state.state_id,
                forecast_coordinate=coordinate,
                intrinsic_input_fingerprint=key[2],
                status=IntrinsicBuildStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            self._records[key] = record
            future = self._executor.submit(self._run, key, context)
            self._futures[key] = future
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
        completion_summary: tuple[str, str, str, float] | None = None

        def build_and_attach_owned() -> tuple[str, str, str, float] | None:
            contract = self._loader(context)
            # If clear_user invalidated this lifecycle while the loader was active,
            # _set returns None. The old contract is then released before the heavy
            # claim opens for replacement work.
            attached = self._set(
                key,
                status=IntrinsicBuildStatus.COMPLETED,
                contract=contract,
            )
            if attached is None:
                return None
            return (
                attached.user_id,
                attached.league_state_id,
                attached.forecast_coordinate,
                (attached.updated_at - attached.created_at).total_seconds(),
            )

        try:
            if self._heavy_work_coordinator is None:
                completion_summary = build_and_attach_owned()
            else:
                with self._heavy_work_coordinator.claim(
                    kind="intrinsic",
                    key=(
                        f"{running.user_id}:{running.intrinsic_input_fingerprint}:"
                        f"{running.forecast_coordinate}"
                    ),
                ):
                    completion_summary = build_and_attach_owned()
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
            with self._lock:
                self._futures.pop(key, None)
            return
        if completion_summary is not None:
            completed_user, completed_state, completed_forecast, elapsed = (
                completion_summary
            )
            _logger.info(
                "FSFFL Intrinsic background build completed user=%s state=%s "
                "forecast=%s elapsed=%.3fs",
                completed_user,
                completed_state,
                completed_forecast,
                elapsed,
            )
        with self._lock:
            self._futures.pop(key, None)

    def clear_user(self, user_id: str) -> int:
        """Invalidate old waiters and drop user-scoped process lifecycle records."""

        with self._lock:
            self._user_epochs[user_id] = self._user_epochs.get(user_id, 0) + 1
            keys = [key for key in self._records if key[0] == user_id]
            for key in keys:
                self._records.pop(key, None)
                future = self._futures.pop(key, None)
                if future is not None and not future.done():
                    future.cancel()
            return len(keys)

    def wait_for_terminal(
        self,
        context: UserRuntimeContext,
        *,
        timeout_seconds: float | None = None,
        poll_seconds: float = 0.05,
    ) -> IntrinsicBuildRecord:
        """Prepare/reuse one exact-coordinate contract and wait off-request-path.

        The intelligence coordinator calls this only from its background worker.
        Request handlers continue to use request()/current() and never block on
        the expensive Intrinsic build.
        """

        timeout = (
            self._hard_watchdog_seconds
            if timeout_seconds is None
            else max(0.1, float(timeout_seconds))
        )
        deadline = monotonic() + timeout
        with self._lock:
            expected_epoch = self._user_epochs.get(context.user_id, 0)
        record = self.request(context, expected_epoch=expected_epoch)
        while record.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }:
            if monotonic() >= deadline:
                return record
            sleep(max(0.01, poll_seconds))
            # request() applies both hard-watchdog policy and lifecycle epoch
            # validation, so a cleared older waiter cannot recreate its work.
            record = self.request(context, expected_epoch=expected_epoch)
        return record

    def current(self, context: UserRuntimeContext) -> IntrinsicBuildRecord | None:
        key = self._key(context)
        with self._lock:
            return self._records.get(key)

    def add_terminal_callback(
        self,
        context: UserRuntimeContext,
        callback,
    ) -> None:
        """Run callback after the owned background build actually finishes.

        This observes the worker Future rather than the response/hard-watchdog
        polling budget, so a late successful worker completion can still drive a
        lightweight presentation follow-up without restarting heavyweight work.
        """

        record = self.request(context)
        key = self._key(context)
        with self._lock:
            future = self._futures.get(key)
        if future is None or future.done():
            callback(self.current(context) or record)
            return

        def finished(_future) -> None:
            callback(self.current(context) or record)

        future.add_done_callback(finished)


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
        "intrinsic_input_fingerprint": record.intrinsic_input_fingerprint,
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
        "intrinsic_input_fingerprint": record.intrinsic_input_fingerprint,
        "build_status": record.status.value,
        "retry_after_ms": None,
        "started_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
