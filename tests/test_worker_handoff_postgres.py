"""Live transaction/lease proof against throwaway CI PostgreSQL only.

Never point FSFFL_TEST_WORKER_DB at production: fixture resets its own schema.
"""
from __future__ import annotations

import multiprocessing as mp
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactMetadataRecord
from fsffl.persistence.postgres import PostgresPersistenceStore
from fsffl.product.worker_handoff import (
    PostgresWorkerDispatch, WorkerDispatchBusy, WorkerJobSpec, WorkerResultReceipt,
    require_current_worker_result,
)


URL = os.getenv("FSFFL_TEST_WORKER_DB", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires isolated CI PostgreSQL service")


class FixtureStore(PostgresPersistenceStore):
    """Simulate an already-saved governed artifact; only the queue uses SQL."""

    def get_reusable_artifact_metadata(self, key):
        return ReusableArtifactMetadataRecord(key=key, computed_at=datetime.now(UTC))


def spec(user="tenant-1", state="state-1"):
    return WorkerJobSpec(
        user_id=user, league_id="league-1", league_state_id=state,
        publication_generation_id="generation-1", source_manifest_fingerprint="manifest-fp-1",
        model_version="accepted-career-v1", capability="career_intrinsic",
    )


def receipt(job):
    key = ArtifactKey(
        artifact_kind="career_intrinsic_v1", scope_kind="league_intrinsic",
        scope_id=job.league_id, input_fingerprint="artifact-fp-1",
        model_version=job.model_version,
    )
    return WorkerResultReceipt(spec=job, artifact_key=key,
                               output_fingerprint=key.input_fingerprint)


def worker_crash(url: str) -> None:
    # A separate OS process owns a new independent pooled database connection.
    q = PostgresWorkerDispatch(FixtureStore(url))
    claim = q.claim(lease_seconds=10)
    if not claim:
        os._exit(46)
    os._exit(47)  # no cleanup and no completion receipt


def _setup(url):
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    info = conninfo_to_dict(url)
    if (info.get("host") not in ("localhost", "127.0.0.1")
            or info.get("dbname") != "fsffl_worker_test"
            or os.getenv("FSFFL_WORKER_DESTRUCTIVE_TEST_ALLOWED") != "1"):
        raise RuntimeError("refusing schema reset outside explicit local disposable PostgreSQL")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("drop schema if exists fsffl cascade")
            cur.execute("create schema fsffl")
            cur.execute(Path("db/migrations/20261028_012_intelligence_worker_job_handoff.sql").read_text())


def test_real_postgres_atomic_claim_crash_retry_and_stale_publication_safety():
    _setup(URL)
    store = FixtureStore(URL)
    q = PostgresWorkerDispatch(store)
    old = spec()
    assert q.enqueue(old) == old.job_id
    assert q.enqueue(old) == old.job_id  # durable deterministic dedupe
    with pytest.raises(WorkerDispatchBusy):
        q.enqueue(spec(state="different-unpublished-state"))

    ctx = mp.get_context("spawn")
    proc = ctx.Process(target=worker_crash, args=(URL,))
    proc.start()
    proc.join(timeout=15)
    assert proc.exitcode == 47  # real worker OS process died mid-lease

    # A second concurrent web/worker instance cannot claim the same live lease.
    assert q.claim(lease_seconds=10) is None
    with store.connection() as conn, conn.cursor() as cur:
        cur.execute("update fsffl.intelligence_worker_job set lease_expires_at=now()-interval '1 second' where job_id=%s", (old.job_id,))
    recovered = q.claim(lease_seconds=10)
    assert recovered is not None and recovered.attempts == 2
    assert q.heartbeat(recovered, lease_seconds=10)
    assert q.finish(recovered, receipt(old))
    assert q.completed_receipt(old) == receipt(old)
    assert q.enqueue(old) == old.job_id  # completed request also deduplicated
    assert q.claim(lease_seconds=10) is None

    # Receipt cannot become a cross-State, cross-generation, or wrong-tenant
    # publication; only the existing State owner can ever commit.
    for override in (
        {"current_state_id": "state-superseded"},
        {"current_user_id": "other-tenant"},
        {"current_publication_generation_id": "other-generation"},
    ):
        params = dict(current_user_id=old.user_id, current_state_id=old.league_state_id,
                      current_publication_generation_id=old.publication_generation_id,
                      current_source_manifest_fingerprint=old.source_manifest_fingerprint,
                      persistence_store=store, verify_completed_contract=lambda _: True)
        params.update(override)
        with pytest.raises(ValueError, match="active publication"):
            require_current_worker_result(receipt(old), **params)
    store.close()


def test_real_postgres_exhausted_lease_cannot_stall_later_state_and_no_raw_payload():
    _setup(URL)
    store = FixtureStore(URL)
    q = PostgresWorkerDispatch(store)
    initial = spec()
    q.enqueue(initial)
    claim = q.claim(lease_seconds=10, max_attempts=1)
    assert claim is not None
    with store.connection() as conn, conn.cursor() as cur:
        cur.execute("update fsffl.intelligence_worker_job set lease_expires_at=now()-interval '1 second' where job_id=%s", (initial.job_id,))
    # The claim reaper frees the per-user admission slot after exhausted lease.
    assert q.claim(lease_seconds=10, max_attempts=1) is None
    with store.connection() as conn, conn.cursor() as cur:
        cur.execute("select status, failure_code, lease_token from fsffl.intelligence_worker_job where job_id=%s", (initial.job_id,))
        row = cur.fetchone()
        status, failure, token = row["status"], row["failure_code"], row["lease_token"]
    assert status == "failed" and failure == "lease_attempts_exhausted" and token is None
    assert q.enqueue(spec(state="next-state")) == spec(state="next-state").job_id
    assert q.claim(lease_seconds=10, max_attempts=1).spec.league_state_id == "next-state"
    store.close()


def worker_complete(url: str, output) -> None:
    from fsffl.product.worker_handoff import execute_one_worker_job
    store = FixtureStore(url)
    try:
        result = execute_one_worker_job(
            PostgresWorkerDispatch(store), compute_and_persist=lambda job: receipt(job),
            lease_seconds=10, heartbeat_seconds=1,
        )
        output.put(result)
    finally:
        store.close()


def test_two_independent_processes_only_one_can_claim_and_return_receipt():
    _setup(URL)
    store = FixtureStore(URL)
    queue = PostgresWorkerDispatch(store)
    work = spec(user="tenant-process-race")
    queue.enqueue(work)
    ctx = mp.get_context("spawn")
    output = ctx.Queue()
    workers = [ctx.Process(target=worker_complete, args=(URL, output)) for _ in range(2)]
    for process in workers:
        process.start()
    for process in workers:
        process.join(timeout=20)
        assert process.exitcode == 0
    statuses = sorted(output.get(timeout=5) for _ in workers)
    assert statuses == ["computed_not_published", "idle"]
    assert queue.completed_receipt(work) == receipt(work)
    assert queue.claim(lease_seconds=10) is None
    store.close()