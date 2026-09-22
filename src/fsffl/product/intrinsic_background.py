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
DEFAULT_INTRINSIC_BACKGROUND_TIMEOUT_SECONDS = 30.0
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
    status: IntrinsicBuildStatus
    created_at: datetime
    updated_at: datetime
    contract: ShapleyIntrinsicContract | None = None
    error: str | None = None


class ShapleyIntrinsicBackgroundCoordinator:
    """Coalesce cold Intrinsic work away from fragile browser requests.

    Model authority stays entirely in the supplied Shapley contract loader. This
    coordinator only owns execution lifecycle and in-process job reuse.
    """

    def __init__(
        self,
        loader: IntrinsicContractLoader,
        *,
        max_workers: int = 1,
        timeout_seconds: float = DEFAULT_INTRINSIC_BACKGROUND_TIMEOUT_SECONDS,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Intrinsic background timeout must be positive")
        self._loader = loader
        self._timeout_seconds = float(timeout_seconds)
        self._lock = RLock()
        self._records: dict[tuple[str, str], IntrinsicBuildRecord] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fsffl-intrinsic",
        )

    @staticmethod
    def _key(context: UserRuntimeContext) -> tuple[str, str]:
        if context.league_state is None:
            raise ValueError("Shapley Intrinsic requires canonical league state")
        return context.user_id, context.league_state.state_id

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
                    elapsed = (now - existing.updated_at).total_seconds()
                    if elapsed >= self._timeout_seconds:
                        error = (
                            "TimeoutError: governed FSFFL Intrinsic preparation exceeded "
                            f"{self._timeout_seconds:.1f}s response budget; the background "
                            "build may still finish and become reusable."
                        )
                        existing = replace(
                            existing,
                            status=IntrinsicBuildStatus.FAILED,
                            contract=None,
                            error=error,
                            updated_at=now,
                        )
                        self._records[key] = existing
                        _logger.warning(
                            "FSFFL Intrinsic background build timed out user=%s state=%s "
                            "elapsed=%.3fs budget=%.3fs",
                            existing.user_id,
                            existing.league_state_id,
                            elapsed,
                            self._timeout_seconds,
                        )
                return existing

            # Drop stale same-user records when authoritative State advances.
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
                status=IntrinsicBuildStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            self._records[key] = record
            self._executor.submit(self._run, key, context)
            return record

    def _set(
        self,
        key: tuple[str, str],
        *,
        status: IntrinsicBuildStatus,
        contract: ShapleyIntrinsicContract | None = None,
        error: str | None = None,
    ) -> IntrinsicBuildRecord | None:
        with self._lock:
            current = self._records.get(key)
            if current is None:
                return None
            if (
                current.status == IntrinsicBuildStatus.FAILED
                and (current.error or "").startswith("TimeoutError:")
                and status == IntrinsicBuildStatus.RUNNING
            ):
                return current
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
        key: tuple[str, str],
        context: UserRuntimeContext,
    ) -> None:
        running = self._set(key, status=IntrinsicBuildStatus.RUNNING)
        if running is None or running.status != IntrinsicBuildStatus.RUNNING:
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
                    "FSFFL Intrinsic background build failed user=%s state=%s error=%s",
                    failed.user_id,
                    failed.league_state_id,
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
                "FSFFL Intrinsic background build completed user=%s state=%s elapsed=%.3fs",
                completed.user_id,
                completed.league_state_id,
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
        "build_status": record.status.value,
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
            f"league state: {record.error or 'unknown server-side build error'}"
        ),
        "league_state_id": record.league_state_id,
        "build_status": record.status.value,
        "retry_after_ms": None,
        "started_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
