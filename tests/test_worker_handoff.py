"""Worker separation tests: no hosted routes, paid resources or private State."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactMetadataRecord
from fsffl.product.worker_handoff import (
    PostgresWorkerDispatch, WorkerDispatchBusy, WorkerClaim, WorkerJobSpec,
    WorkerResultReceipt, require_current_worker_result,
)


def spec(**updates):
    values = dict(user_id="tenant-a", league_id="league-1", league_state_id="state-1",
                  publication_generation_id="generation-1",
                  source_manifest_fingerprint="evidence-fingerprint-1",
                  model_version="career-contract-v1", capability="career_intrinsic")
    values.update(updates)
    return WorkerJobSpec(**values)


def receipt(s=None):
    s = s or spec()
    k = ArtifactKey(artifact_kind="career_intrinsic_v1", scope_kind="league_intrinsic",
                    scope_id=s.league_id, input_fingerprint="result-fp-1",
                    model_version="career-contract-v1")
    return WorkerResultReceipt(spec=s, artifact_key=k, output_fingerprint=k.input_fingerprint)


class Store:
    def __init__(self, exists=True, reusable=True):
        self.exists = exists
        self.reusable = reusable
        self.reads = []

    def get_reusable_artifact_metadata(self, key):
        self.reads.append(key)
        if not self.exists:
            return None
        return ReusableArtifactMetadataRecord(key=key, computed_at=datetime.now(UTC),
                                              invalidated_at=None if self.reusable else datetime.now(UTC))


def accept(r, **updates):
    x = dict(current_user_id=r.spec.user_id, current_state_id=r.spec.league_state_id,
             current_publication_generation_id=r.spec.publication_generation_id,
             current_source_manifest_fingerprint=r.spec.source_manifest_fingerprint,
             persistence_store=Store())
    x.update(updates)
    x.setdefault("verify_completed_contract", lambda r: True)
    return require_current_worker_result(r, **x)


def test_deterministic_job_identity_avoids_duplicate_compute_and_scopes_tenants():
    a = spec()
    assert a.job_id == spec().job_id and len(a.job_id) == 64
    for change in (
        dict(user_id="tenant-b"), dict(league_id="league-2"), dict(league_state_id="state-2"),
        dict(publication_generation_id="generation-2"),
        dict(source_manifest_fingerprint="revision-2"),
        dict(model_version="career-contract-v2"),
    ):
        assert a.job_id != spec(**change).job_id
    with pytest.raises(ValueError):
        spec(capability="made_up").job_id
    with pytest.raises(ValueError):
        spec(user_id=" tenant-a ")


@pytest.mark.parametrize('change', [
    dict(current_user_id="tenant-b"),
    dict(current_state_id="state-new"),
    dict(current_publication_generation_id="generation-new"),
    dict(current_source_manifest_fingerprint="revision-new"),
])
def test_stale_or_cross_tenant_receipt_fails_before_persistence_read(change):
    store = Store()
    with pytest.raises(ValueError, match="active publication"):
        accept(receipt(), persistence_store=store, **change)
    assert store.reads == []


def test_missing_or_invalidated_artifact_fails_closed_and_good_receipt_only_returns_key():
    r = receipt()
    with pytest.raises(ValueError, match="durably"):
        accept(r, persistence_store=Store(exists=False))
    with pytest.raises(ValueError, match="durably"):
        accept(r, persistence_store=Store(reusable=False))
    with pytest.raises(ValueError, match="canonical"):
        accept(r, verify_completed_contract=lambda _r: False)
    assert accept(r) == r.artifact_key


def test_worker_cannot_substitute_another_artifact_or_output_fingerprint():
    r = receipt()
    for key in [replace(r.artifact_key, scope_id="league-2"),
                replace(r.artifact_key, artifact_kind="forecast"),
                replace(r.artifact_key, scope_kind="user")]:
        with pytest.raises(ValueError):
            WorkerResultReceipt(spec=r.spec, artifact_key=key, output_fingerprint=r.output_fingerprint)
    with pytest.raises(ValueError):
        WorkerResultReceipt(spec=r.spec, artifact_key=r.artifact_key, output_fingerprint="other")
    with pytest.raises(ValueError, match="model version"):
        WorkerResultReceipt(spec=r.spec, artifact_key=replace(r.artifact_key, model_version="rogue"), output_fingerprint="result-fp-1")


class FakeCursor:
    def __init__(self, *, row=None, count=1):
        self.row = row
        self.rowcount = count
        self.executed = []

    def execute(self, sql, values):
        self.executed.append((sql, values))

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self.cur = cursor

    def cursor(self):
        return self.cur

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass


class PooledStore:
    def __init__(self, cursor):
        self.cursor = cursor
        self.checkouts = 0

    def get_reusable_artifact_metadata(self, key):
        return ReusableArtifactMetadataRecord(key=key, computed_at=datetime.now(UTC))

    def connection(self):
        self.checkouts += 1
        return FakeConnection(self.cursor)


def test_enqueue_claim_fencing_and_retry_paths_use_one_bounded_store():
    c = FakeCursor(row=dict(user_id="tenant-a", league_id="league-1", league_state_id="state-1",
                            publication_generation_id="generation-1",
                            source_manifest_fingerprint="evidence-fingerprint-1",
                            model_version="career-contract-v1", capability="career_intrinsic",
                            attempts=2, lease_expires_at=datetime.now(UTC)+timedelta(minutes=5)))
    store = PooledStore(c)
    queue = PostgresWorkerDispatch(store)
    expected = spec()
    assert queue.enqueue(expected) == expected.job_id
    assert "on conflict do nothing" in c.executed[-1][0]
    claim = queue.claim(lease_seconds=30, max_attempts=3)
    assert claim and claim.spec == expected and claim.attempts == 2
    assert "for update skip locked" in c.executed[-1][0]
    assert "lease_attempts_exhausted" in c.executed[-2][0]
    assert queue.heartbeat(claim, lease_seconds=30)
    assert "lease_token=%s" in c.executed[-1][0]
    # Finished result must exist durably before marking the lease computed.
    assert queue.finish(claim, receipt())
    assert c.executed[-1][1][-1] == claim.lease_token
    assert "lease_expires_at > now()" in c.executed[-1][0]
    assert queue.fail(claim, error_code="worker_out_of_memory")
    c.row = dict(result_artifact_kind="career_intrinsic_v1", result_artifact_model_version="career-contract-v1", result_input_fingerprint="result-fp-1")
    assert queue.completed_receipt(expected) == receipt()
    assert store.checkouts == 6
    with pytest.raises(ValueError):
        queue.fail(claim, error_code="raw secret data; never persist")
    with pytest.raises(ValueError):
        queue.finish(claim, receipt(spec(user_id="tenant-b")))


def test_lost_lease_cannot_heartbeat_finish_or_fail():
    c = FakeCursor(count=0)
    pool = PooledStore(c)
    pool.get_reusable_artifact_metadata = lambda key: ReusableArtifactMetadataRecord(key=key, computed_at=datetime.now(UTC))
    queue = PostgresWorkerDispatch(pool)
    claim = WorkerClaim(spec(), "expired-token", 1, datetime.now(UTC)+timedelta(seconds=5))
    assert not queue.heartbeat(claim)
    assert not queue.finish(claim, receipt())
    assert not queue.fail(claim, error_code="worker_crash")


def test_queue_has_bounded_admission_and_no_secondary_pool():
    with pytest.raises(TypeError, match="pooled"):
        PostgresWorkerDispatch(Store())
    queue = PostgresWorkerDispatch(PooledStore(FakeCursor()))
    with pytest.raises(ValueError):
        queue.claim(lease_seconds=3)
    with pytest.raises(ValueError):
        queue.claim(max_attempts=99)
    with pytest.raises(ValueError):
        queue.heartbeat(WorkerClaim(spec(), "tok", 1, datetime.now(UTC)), lease_seconds=9999)


def test_migration_does_not_grant_public_access_or_trigger_live_work():
    migration = Path("db/migrations/20261028_012_intelligence_worker_job_handoff.sql").read_text()
    assert "enable row level security" in migration
    assert "unique index" in migration and "status in ('queued', 'running')" in migration
    assert "grant " not in migration.lower()
    assert "trigger" not in migration.lower()


def test_worker_execution_stages_result_without_any_publication():
    from fsffl.product.worker_handoff import execute_one_worker_job
    c = FakeCursor(row=dict(user_id="tenant-a", league_id="league-1",
                            league_state_id="state-1", publication_generation_id="generation-1",
                            source_manifest_fingerprint="evidence-fingerprint-1",
                            model_version="career-contract-v1", capability="career_intrinsic",
                            attempts=1, lease_expires_at=datetime.now(UTC) + timedelta(minutes=2)))
    q = PostgresWorkerDispatch(PooledStore(c))
    invoked = []
    def calc(item):
        invoked.append(item)
        return receipt(item)
    assert execute_one_worker_job(q, compute_and_persist=calc, heartbeat_seconds=0.01) == "computed_not_published"
    assert invoked == [spec()]
    assert "status='computed'" in c.executed[-1][0]
    # Existing publication owner is never invoked by the worker itself.


def test_worker_execution_failure_does_not_expose_exception_text_or_publish():
    from fsffl.product.worker_handoff import execute_one_worker_job
    c = FakeCursor(row=dict(user_id="tenant-a", league_id="league-1",
                            league_state_id="state-1", publication_generation_id="generation-1",
                            source_manifest_fingerprint="evidence-fingerprint-1",
                            model_version="career-contract-v1", capability="career_intrinsic",
                            attempts=1, lease_expires_at=datetime.now(UTC) + timedelta(minutes=2)))
    q = PostgresWorkerDispatch(PooledStore(c))
    def failing(_):
        raise RuntimeError("private user data and source credentials")
    assert execute_one_worker_job(q, compute_and_persist=failing, heartbeat_seconds=0.01) == "failed_not_published"
    assert c.executed[-1][1][0] == "worker_execution_failed"
    assert "private" not in repr(c.executed)


def test_worker_execution_lost_lease_refuses_result_completion():
    from fsffl.product.worker_handoff import execute_one_worker_job
    c = FakeCursor(row=dict(user_id="tenant-a", league_id="league-1",
                            league_state_id="state-1", publication_generation_id="generation-1",
                            source_manifest_fingerprint="evidence-fingerprint-1",
                            model_version="career-contract-v1", capability="career_intrinsic",
                            attempts=1, lease_expires_at=datetime.now(UTC) + timedelta(minutes=2)))
    pool = PooledStore(c)
    queue = PostgresWorkerDispatch(pool)
    def calc(item):
        c.rowcount = 0  # lease revoked before final completion; fenced update
        return receipt(item)
    assert execute_one_worker_job(queue, compute_and_persist=calc, heartbeat_seconds=0.01) == "lease_lost_not_published"
    assert "status='computed'" in c.executed[-1][0]  # attempted but updated zero rows


def test_worker_execution_idle_does_no_calculation():
    from fsffl.product.worker_handoff import execute_one_worker_job
    q = PostgresWorkerDispatch(PooledStore(FakeCursor(row=None)))
    assert execute_one_worker_job(q, compute_and_persist=lambda _: pytest.fail("should not compute")) == "idle"