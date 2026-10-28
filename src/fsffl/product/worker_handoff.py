"""Disabled-by-default heavy-work dispatch seam, without a second model owner.

The web process submits exact-input *references*, not private model payloads. A
separate worker can lease one request and persist its governed artifact using
existing model and persistence code. A receipt is NOT a publication: the existing
State/generation publication owner must still perform its guarded commit.

No production route imports or enables this module. In particular the existing
in-process IntelligenceJobCoordinator remains the active beta lifecycle.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from uuid import uuid4

from fsffl.persistence.contracts import ArtifactKey, PersistenceStore, canonical_fingerprint


WORKER_JOB_VERSION = "intelligence-worker-handoff-v1"


@dataclass(frozen=True)
class WorkerJobSpec:
    user_id: str
    league_id: str
    league_state_id: str
    publication_generation_id: str
    source_manifest_fingerprint: str
    model_version: str
    capability: str
    # A correlation ID is explicitly not part of job identity. One exact
    # computation for a given state/generation/input has exactly one job ID.

    def __post_init__(self) -> None:
        for field in (
            "user_id", "league_id", "league_state_id", "publication_generation_id",
            "source_manifest_fingerprint", "model_version", "capability",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"worker job requires a normalized {field}")
        if self.capability not in {"career_intrinsic"}:
            raise ValueError("worker dispatch capability is not accepted")

    @property
    def job_id(self) -> str:
        return canonical_fingerprint(
            WORKER_JOB_VERSION,
            self.capability,
            self.user_id,
            self.league_id,
            self.league_state_id,
            self.publication_generation_id,
            self.source_manifest_fingerprint,
            self.model_version,
        )


@dataclass(frozen=True)
class WorkerClaim:
    spec: WorkerJobSpec
    lease_token: str
    attempts: int
    lease_expires_at: datetime

    def __post_init__(self) -> None:
        if not self.lease_token or self.attempts < 1:
            raise ValueError("invalid worker lease")
        if self.lease_expires_at.tzinfo is None:
            raise ValueError("worker lease must be timezone-aware")


@dataclass(frozen=True)
class WorkerResultReceipt:
    spec: WorkerJobSpec
    artifact_key: ArtifactKey
    # This is the bound fingerprint, not a second calculation or publication.
    output_fingerprint: str

    def __post_init__(self) -> None:
        if not self.output_fingerprint.strip():
            raise ValueError("missing completed-result fingerprint")
        if (
            self.artifact_key.artifact_kind != "career_intrinsic_v1"
            or self.artifact_key.scope_kind != "league_intrinsic"
            or self.artifact_key.scope_id != self.spec.league_id
        ):
            raise ValueError("worker result must be Career for the exact league State")
        if self.artifact_key.model_version != self.spec.model_version:
            raise ValueError("worker result model version does not match request")
        if self.artifact_key.input_fingerprint != self.output_fingerprint:
            raise ValueError("worker output and artifact fingerprint differ")


def require_current_worker_result(
    receipt: WorkerResultReceipt,
    *,
    current_user_id: str,
    current_state_id: str,
    current_publication_generation_id: str,
    current_source_manifest_fingerprint: str,
    persistence_store: PersistenceStore,
    verify_completed_contract: Callable[[WorkerResultReceipt], bool],
) -> ArtifactKey:
    """Reject stale/cross-tenant/unpublished receipts before existing commit.

    This preflight is not a distributed compare-and-swap. The real publication
    owner MUST revalidate State and generation inside its own lifecycle lock and
    publication transaction after this method returns. We intentionally do not
    offer a worker-side `publish` operation.
    """
    spec = receipt.spec
    if (
        spec.user_id != current_user_id
        or spec.league_state_id != current_state_id
        or spec.publication_generation_id != current_publication_generation_id
        or spec.source_manifest_fingerprint != current_source_manifest_fingerprint
    ):
        raise ValueError("worker receipt is not for the active publication/State")
    metadata = persistence_store.get_reusable_artifact_metadata(receipt.artifact_key)
    if metadata is None or not metadata.reusable:
        raise ValueError("worker result is not durably available")
    # Metadata alone cannot verify State-bound Career payload completeness: the
    # canonical loader must resolve and check the embedded exact dependency
    # fingerprint and cohort. This callback MUST invoke that existing owner.
    if not verify_completed_contract(receipt):
        raise ValueError("worker artifact failed canonical exact-State Career validation")
    return receipt.artifact_key


class WorkerDispatchBusy(RuntimeError):
    """One tenant already owns a queued or active calculation."""


class PostgresWorkerDispatch:
    """Bounded DB-backed lease ownership using an existing pooled store.

    No secondary connection pool, no in-process job cache, no provider/model
    computation. SQL migration is a separate (NOT APPLIED) approval gate.
    This adapter is deliberately not invoked by any hosted route or scheduler.
    """

    def __init__(self, persistence_store: PersistenceStore) -> None:
        connection = getattr(persistence_store, "connection", None)
        if not callable(connection):
            raise TypeError("worker dispatch requires the existing pooled PostgreSQL connection owner")
        self._connection: Callable = connection
        self._persistence = persistence_store

    def enqueue(self, spec: WorkerJobSpec) -> str:
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """insert into fsffl.intelligence_worker_job
                   (job_id, user_id, league_id, league_state_id, publication_generation_id,
                    source_manifest_fingerprint, model_version, capability)
                   values (%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict do nothing""",
                (
                    spec.job_id, spec.user_id, spec.league_id, spec.league_state_id,
                    spec.publication_generation_id, spec.source_manifest_fingerprint,
                    spec.model_version, spec.capability,
                ),
            )
            if cursor.rowcount == 0:
                # Already completed requests are idempotent and return the
                # existing receipt identity; only a *different* active request
                # receives backpressure.
                cursor.execute(
                    """select job_id from fsffl.intelligence_worker_job
                       where job_id=%s""", (spec.job_id,),
                )
                if cursor.fetchone() is None:
                    raise WorkerDispatchBusy("one queued/running job per user; retry after completion")
        return spec.job_id

    def claim(self, *, lease_seconds: int = 300, max_attempts: int = 3) -> WorkerClaim | None:
        if not 10 <= lease_seconds <= 3600 or not 1 <= max_attempts <= 10:
            raise ValueError("invalid bounded worker lease policy")
        token = uuid4().hex
        with self._connection() as connection, connection.cursor() as cursor:
            # Exhausted expired leases must release their per-user slot; a
            # worker that died on the final permitted attempt cannot stall
            # this tenant forever. Old tokens remain fenced by status.
            cursor.execute(
                """update fsffl.intelligence_worker_job
                   set status='failed', failure_code='lease_attempts_exhausted',
                       lease_token=null, lease_expires_at=null, updated_at=now()
                   where status='running' and lease_expires_at < now()
                     and attempts >= %s""",
                (max_attempts,),
            )
            # Only one winner per row; the partial queued/running unique index
            # prevents parallel jobs for one tenant, including different States.
            # An expired lease is retryable; the superseded token is fenced.
            cursor.execute(
                """with next_job as (
                    select job_id from fsffl.intelligence_worker_job
                    where (status='queued' or
                           (status='running' and lease_expires_at < now()))
                      and attempts < %s
                    order by case when status='running' then 0 else 1 end,
                             created_at, job_id
                    for update skip locked
                    limit 1
                   )
                   update fsffl.intelligence_worker_job as j
                   set status='running', lease_token=%s,
                       lease_expires_at=now()+(%s * interval '1 second'),
                       attempts=j.attempts+1, updated_at=now()
                   from next_job where j.job_id=next_job.job_id
                   returning j.user_id,j.league_id,j.league_state_id,
                             j.publication_generation_id,j.source_manifest_fingerprint,
                             j.model_version,j.capability,j.attempts,j.lease_expires_at""",
                (max_attempts, token, lease_seconds),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return WorkerClaim(
            spec=WorkerJobSpec(
                user_id=row["user_id"], league_id=row["league_id"],
                league_state_id=row["league_state_id"],
                publication_generation_id=row["publication_generation_id"],
                source_manifest_fingerprint=row["source_manifest_fingerprint"],
                model_version=row["model_version"], capability=row["capability"],
            ),
            lease_token=token, attempts=int(row["attempts"]),
            lease_expires_at=row["lease_expires_at"],
        )

    def heartbeat(self, claim: WorkerClaim, *, lease_seconds: int = 300) -> bool:
        if not 10 <= lease_seconds <= 3600:
            raise ValueError("invalid bounded worker lease")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """update fsffl.intelligence_worker_job
                   set lease_expires_at=now()+(%s * interval '1 second'), updated_at=now()
                   where job_id=%s and status='running' and lease_token=%s
                     and lease_expires_at > now()""",
                (lease_seconds, claim.spec.job_id, claim.lease_token),
            )
            return cursor.rowcount == 1

    def finish(self, claim: WorkerClaim, receipt: WorkerResultReceipt) -> bool:
        if receipt.spec != claim.spec:
            raise ValueError("result receipt does not match worker claim")
        # A result is not complete unless the accepted artifact was durably
        # written first. It still must undergo canonical semantic validation
        # before the publication owner chooses to promote it.
        metadata = self._persistence.get_reusable_artifact_metadata(receipt.artifact_key)
        if metadata is None or not metadata.reusable:
            raise ValueError("cannot finish work without a durable output artifact")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """update fsffl.intelligence_worker_job
                   set status='computed', result_artifact_kind=%s,
                       result_artifact_model_version=%s,
                       result_input_fingerprint=%s, lease_token=null,
                       lease_expires_at=null, updated_at=now()
                   where job_id=%s and status='running' and lease_token=%s
                     and lease_expires_at > now()""",
                (
                    receipt.artifact_key.artifact_kind,
                    receipt.artifact_key.model_version,
                    receipt.artifact_key.input_fingerprint,
                    claim.spec.job_id, claim.lease_token,
                ),
            )
            return cursor.rowcount == 1

    def completed_receipt(self, spec: WorkerJobSpec) -> WorkerResultReceipt | None:
        """Read only a completed result reference, not a private payload."""
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """select result_artifact_kind, result_artifact_model_version,
                          result_input_fingerprint
                   from fsffl.intelligence_worker_job
                   where job_id=%s and user_id=%s and status='computed'""",
                (spec.job_id, spec.user_id),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        key = ArtifactKey(
            artifact_kind=row["result_artifact_kind"],
            scope_kind="league_intrinsic", scope_id=spec.league_id,
            model_version=row["result_artifact_model_version"],
            input_fingerprint=row["result_input_fingerprint"],
        )
        return WorkerResultReceipt(spec=spec, artifact_key=key,
                                   output_fingerprint=key.input_fingerprint)

    def fail(self, claim: WorkerClaim, *, error_code: str) -> bool:
        if not error_code or len(error_code) > 80 or not error_code.replace("_", "").isalnum():
            raise ValueError("worker failure must use a bounded non-sensitive code")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """update fsffl.intelligence_worker_job
                   set status='failed', failure_code=%s, lease_token=null,
                       lease_expires_at=null, updated_at=now()
                   where job_id=%s and status='running' and lease_token=%s
                     and lease_expires_at > now()""",
                (error_code, claim.spec.job_id, claim.lease_token),
            )
            return cursor.rowcount == 1