from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import StrEnum
from threading import RLock
from time import monotonic
from typing import Callable
from uuid import uuid4

from .foreground_pressure import foreground_pressure
from .resource_coordinator import HeavyWorkCoordinator, release_unused_process_memory


class MarketEnrichmentStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass(frozen=True)
class MarketEnrichmentRecord:
    job_id: str
    user_id: str
    league_state_id: str
    focal_team_id: str
    request_key: str
    status: MarketEnrichmentStatus
    created_at_monotonic: float
    started_at_monotonic: float | None = None
    completed_at_monotonic: float | None = None
    result: dict[str, object] | None = None
    error: str | None = None

    def public_payload(self, *, include_result: bool = True) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "league_state_id": self.league_state_id,
            "focal_team_id": self.focal_team_id,
            "request_key": self.request_key,
            "status": self.status.value,
            "error": self.error,
            "result": self.result if include_result else None,
        }


EnrichmentWork = Callable[[], dict[str, object]]
IdentityValidator = Callable[[str, str, str], bool]


class MarketDecisionEnrichmentCoordinator:
    """Run bounded bilateral Decision enrichment off the foreground request path.

    Structural Search remains request-owned and returns immediately. This coordinator
    owns only the later Decision-enrichment phase. Work is serialized through the
    existing process-wide heavy-work gate and revalidates exact league/state/team
    identity before and after execution so stale results cannot attach.
    """

    def __init__(
        self,
        *,
        heavy_work_coordinator: HeavyWorkCoordinator | None,
        identity_validator: IdentityValidator,
        max_workers: int = 1,
    ) -> None:
        self._heavy = heavy_work_coordinator
        self._identity_validator = identity_validator
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="fsffl-market-enrichment",
        )
        self._lock = RLock()
        self._records: dict[str, MarketEnrichmentRecord] = {}
        self._active_by_scope: dict[tuple[str, str, str, str], str] = {}
        self._future_by_job: dict[str, Future[None]] = {}

    def start(
        self,
        *,
        user_id: str,
        league_state_id: str,
        focal_team_id: str,
        request_key: str,
        work: EnrichmentWork,
    ) -> MarketEnrichmentRecord:
        scope = (user_id, league_state_id, focal_team_id, request_key)
        with self._lock:
            existing_id = self._active_by_scope.get(scope)
            if existing_id is not None:
                existing = self._records.get(existing_id)
                if existing is not None and existing.status in {
                    MarketEnrichmentStatus.QUEUED,
                    MarketEnrichmentStatus.RUNNING,
                    MarketEnrichmentStatus.COMPLETED,
                }:
                    return existing

            job_id = uuid4().hex
            record = MarketEnrichmentRecord(
                job_id=job_id,
                user_id=user_id,
                league_state_id=league_state_id,
                focal_team_id=focal_team_id,
                request_key=request_key,
                status=MarketEnrichmentStatus.QUEUED,
                created_at_monotonic=monotonic(),
            )
            self._records[job_id] = record
            self._active_by_scope[scope] = job_id
            future = self._executor.submit(self._run, record, work)
            self._future_by_job[job_id] = future
            return record

    def _set(self, job_id: str, **changes) -> MarketEnrichmentRecord | None:
        with self._lock:
            current = self._records.get(job_id)
            if current is None:
                return None
            updated = replace(current, **changes)
            self._records[job_id] = updated
            return updated

    def _run(self, record: MarketEnrichmentRecord, work: EnrichmentWork) -> None:
        if not self._identity_validator(
            record.user_id,
            record.league_state_id,
            record.focal_team_id,
        ):
            self._set(
                record.job_id,
                status=MarketEnrichmentStatus.INTERRUPTED,
                completed_at_monotonic=monotonic(),
                error="market context changed before Decision enrichment began",
            )
            return

        self._set(
            record.job_id,
            status=MarketEnrichmentStatus.RUNNING,
            started_at_monotonic=monotonic(),
        )
        key = (
            f"{record.user_id}:{record.league_state_id}:"
            f"{record.focal_team_id}:{record.request_key}"
        )
        try:
            foreground_pressure.cooperative_yield()
            if self._heavy is None:
                result = work()
            else:
                with self._heavy.claim(
                    kind="market_decision_enrichment",
                    key=key,
                    timeout_seconds=300.0,
                ):
                    foreground_pressure.cooperative_yield()
                    result = work()
                    foreground_pressure.cooperative_yield()

            if not self._identity_validator(
                record.user_id,
                record.league_state_id,
                record.focal_team_id,
            ):
                self._set(
                    record.job_id,
                    status=MarketEnrichmentStatus.INTERRUPTED,
                    completed_at_monotonic=monotonic(),
                    result=None,
                    error="market context changed while Decision enrichment was running",
                )
                return

            self._set(
                record.job_id,
                status=MarketEnrichmentStatus.COMPLETED,
                completed_at_monotonic=monotonic(),
                result=result,
                error=None,
            )
        except Exception as exc:
            self._set(
                record.job_id,
                status=MarketEnrichmentStatus.FAILED,
                completed_at_monotonic=monotonic(),
                result=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            with self._lock:
                self._future_by_job.pop(record.job_id, None)
            release_unused_process_memory(label="market-decision-enrichment")

    def get(
        self,
        *,
        user_id: str,
        job_id: str,
    ) -> MarketEnrichmentRecord | None:
        with self._lock:
            record = self._records.get(job_id)
            if record is None or record.user_id != user_id:
                return None
            return record

    def clear_user(self, user_id: str) -> int:
        with self._lock:
            ids = [
                job_id
                for job_id, record in self._records.items()
                if record.user_id == user_id
            ]
            for job_id in ids:
                record = self._records.pop(job_id)
                scope = (
                    record.user_id,
                    record.league_state_id,
                    record.focal_team_id,
                    record.request_key,
                )
                if self._active_by_scope.get(scope) == job_id:
                    self._active_by_scope.pop(scope, None)
                future = self._future_by_job.pop(job_id, None)
                if future is not None and not future.done():
                    future.cancel()
            return len(ids)
