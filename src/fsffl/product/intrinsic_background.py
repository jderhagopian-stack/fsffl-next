from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import Callable

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .runtime import UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]


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
    ) -> None:
        self._loader = loader
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
    ) -> IntrinsicBuildRecord:
        with self._lock:
            current = self._records[key]
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
        self._set(key, status=IntrinsicBuildStatus.RUNNING)
        try:
            contract = self._loader(context)
        except Exception as exc:
            self._set(
                key,
                status=IntrinsicBuildStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        self._set(
            key,
            status=IntrinsicBuildStatus.COMPLETED,
            contract=contract,
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
