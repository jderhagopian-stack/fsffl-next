"""Offline concurrency/failure tests for the bounded storage-write POC.

The fake follows Supabase's documented Standard Upload contract. It does not
contact a Supabase project and cannot be mistaken for hosted acceptance.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
import tempfile
from threading import Barrier
import unittest

from artifacts.implementation.storage_write_safety_20261010.write_safety import (
    AlreadyExists,
    ArtifactIdentity,
    ArtifactInput,
    AtomicDirectoryStore,
    IdentityConflict,
    IntegrityError,
    ImmutablePublisher,
    MetadataDatabase,
    PublicationCandidate,
    PublicationConflict,
    SupabaseStandardUploadStore,
)


class FakeSupabaseStandardUploads:
    """Atomic API model: each attempt owns bytes until no-upsert metadata win."""
    def __init__(self):
        from threading import Lock
        self.lock = Lock()
        self.objects = {}
        self.versions = {}
        self.upsert_flags = []

    def upload(self, key, body, *, upsert):
        self.upsert_flags.append(upsert)
        if upsert is not False:
            raise AssertionError("prototype must never upload with upsert enabled")
        with self.lock:
            if key in self.objects:
                raise AlreadyExists(key)
            # Supabase Storage internally stores an attempt's bytes under its
            # own version and only publishes the logical path after its DB win.
            self.objects[key] = bytes(body)
            self.versions[key] = "isolated-version-" + str(len(self.versions) + 1)

    def download(self, key):
        with self.lock:
            if key not in self.objects:
                raise FileNotFoundError(key)
            return bytes(self.objects[key])


def identity(tenant="tenant-a", state="state-1", pit="pit-1",
             fingerprint="fp-1", kind="forecast"):
    return ArtifactIdentity(tenant, kind, "league_state", "league-a", state,
                            pit, fingerprint, "model-v1")


def payload(marker="original"):
    return {"marker": marker, "values": [1, 2, 3], "known_at": "2026-10-10T00:00:00Z"}


def candidate(gen="generation-1", *, item_identity=None, value=None,
              tenant="tenant-a", state="state-1", pit="pit-1", surface="forecast"):
    i = item_identity or identity(tenant=tenant, state=state, pit=pit)
    return PublicationCandidate(tenant, surface, gen, state, pit, "manifest-" + gen,
                               (ArtifactInput(i, value or payload()),))


class StorageWriteSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.api = FakeSupabaseStandardUploads()
        self.objects = SupabaseStandardUploadStore(self.api)
        self.db = MetadataDatabase(self.root / "metadata.sqlite")
        self.publisher = ImmutablePublisher(self.objects, self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_supabase_standard_upload_path_is_create_only_and_verifies_retry(self):
        data = b"immutable bytes"
        digest = sha256(data).hexdigest()
        self.assertTrue(self.objects.put_if_absent("t/key", data, digest))
        self.assertFalse(self.objects.put_if_absent("t/key", data, digest))
        self.assertEqual(self.api.objects["t/key"], data)
        self.assertEqual(self.api.upsert_flags, [False, False])
        with self.assertRaises(AlreadyExists):
            self.api.upload("t/key", b"replacement", upsert=False)
        self.assertEqual(self.api.objects["t/key"], data)
        with self.assertRaises(IntegrityError):
            self.objects.put_if_absent("t/key", b"replacement", digest)

    def test_same_payload_concurrent_publication_is_idempotent(self):
        candidate_value = candidate()
        barrier = Barrier(12)
        publisher = ImmutablePublisher(self.objects, self.db,
                                       after_upload=lambda _: barrier.wait(timeout=5))
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(
                lambda _: publisher.publish(candidate_value, None), range(12)))
        self.assertEqual(results.count("published"), 1)
        self.assertEqual(results.count("already_published"), 11)
        restored = publisher.read_current_or_last_good("tenant-a", "forecast")
        self.assertEqual(restored["payloads"][identity().fields()], payload())
        self.assertEqual(restored["state_id"], "state-1")
        self.assertEqual(restored["pit_state_id"], "pit-1")

    def test_conflicting_same_identity_race_has_one_winner_no_overwrite(self):
        barrier = Barrier(2)
        publisher = ImmutablePublisher(self.objects, self.db,
                                       after_upload=lambda _: barrier.wait(timeout=5))
        items = [candidate(value=payload("A")), candidate(value=payload("B"))]
        def write(item):
            try:
                return publisher.publish(item, None)
            except (IdentityConflict, PublicationConflict):
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, items))
        self.assertEqual(results.count("published"), 1)
        self.assertEqual(results.count("rejected"), 1)
        observed = publisher.read_current_or_last_good("tenant-a", "forecast")
        self.assertIn(observed["payloads"][identity().fields()], [payload("A"), payload("B")])
        with self.db.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM publication_generation").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM artifact_blob_registry").fetchone()[0], 1)

    def test_object_orphan_on_db_failure_is_invisible_and_retryable(self):
        item = candidate()
        with self.assertRaises(OSError):
            self.publisher.publish(item, None, failpoint="after_upload")
        self.assertIsNone(self.publisher.pointer("tenant-a", "forecast"))
        with self.db.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM artifact_blob_registry").fetchone()[0], 0)
        self.assertEqual(len(self.api.objects), 1)  # unreferenced bytes are safe to reap later
        self.assertEqual(self.publisher.publish(item, None), "published")

    def test_transaction_failure_preserves_registry_visibility_and_pointer(self):
        first = candidate()
        self.publisher.publish(first, None)
        before = self.publisher.pointer("tenant-a", "forecast")
        second = candidate("generation-2", item_identity=identity(state="state-2", pit="pit-2"),
                           state="state-2", pit="pit-2")
        with self.assertRaises(OSError):
            self.publisher.publish(second, "generation-1", failpoint="before_pointer")
        self.assertEqual(self.publisher.pointer("tenant-a", "forecast"), before)
        with self.db.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM publication_generation").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM publication_artifact_ref").fetchone()[0], 1)
        self.assertEqual(self.publisher.publish(second, "generation-1"), "published")
        after = self.publisher.pointer("tenant-a", "forecast")
        self.assertEqual(after["current_generation_id"], "generation-2")
        self.assertEqual(after["last_good_generation_id"], "generation-1")

    def test_stale_pointer_compare_and_swap_is_rejected(self):
        self.publisher.publish(candidate(), None)
        before = self.publisher.pointer("tenant-a", "forecast")
        next_gen = candidate("generation-2", item_identity=identity(state="state-2", pit="pit-2"),
                             state="state-2", pit="pit-2")
        with self.assertRaises(PublicationConflict):
            self.publisher.publish(next_gen, expected_current_generation=None)
        self.assertEqual(self.publisher.pointer("tenant-a", "forecast"), before)

    def test_content_address_shares_exact_bytes_only_inside_tenant(self):
        first = candidate()
        self.publisher.publish(first, None)
        second = candidate("generation-2", item_identity=identity(state="state-2", pit="pit-2"),
                           state="state-2", pit="pit-2")
        self.publisher.publish(second, "generation-1")
        with self.db.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM artifact_blob_registry").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(DISTINCT object_key) FROM artifact_blob_registry").fetchone()[0], 1)
        self.assertEqual(len(self.api.objects), 1)

    def test_corrupt_current_does_not_replace_last_good_on_later_publish(self):
        self.publisher.publish(candidate(), None)
        second = candidate("generation-2", item_identity=identity(state="state-2", pit="pit-2"),
                           state="state-2", pit="pit-2", value=payload("new"))
        self.publisher.publish(second, "generation-1")
        with self.db.connection() as db:
            key = db.execute("SELECT object_key FROM artifact_blob_registry WHERE state_id='state-2'").fetchone()[0]
        self.api.objects[key] = b"corrupted"
        third = candidate("generation-3", item_identity=identity(state="state-3", pit="pit-3"),
                          state="state-3", pit="pit-3", value=payload("newer"))
        self.publisher.publish(third, "generation-2")
        pointer = self.publisher.pointer("tenant-a", "forecast")
        self.assertEqual(pointer["current_generation_id"], "generation-3")
        self.assertEqual(pointer["last_good_generation_id"], "generation-1")

    def test_existing_generation_id_cannot_be_rebound_to_new_manifest(self):
        self.publisher.publish(candidate(), None)
        conflicting = candidate(value=payload("different"))
        with self.assertRaises(PublicationConflict):
            self.publisher.publish(conflicting, "generation-1")
        pointer = self.publisher.pointer("tenant-a", "forecast")
        self.assertEqual(pointer["current_generation_id"], "generation-1")

    def test_corrupt_current_serves_last_good_without_pointer_mutation(self):
        self.publisher.publish(candidate(), None)
        next_gen = candidate("generation-2", item_identity=identity(state="state-2", pit="pit-2"),
                             state="state-2", pit="pit-2", value=payload("new"))
        self.publisher.publish(next_gen, "generation-1")
        before = self.publisher.pointer("tenant-a", "forecast")
        with self.db.connection() as db:
            key = db.execute("SELECT object_key FROM artifact_blob_registry WHERE state_id='state-2'").fetchone()[0]
        self.api.objects[key] = b"corrupted"
        served = self.publisher.read_current_or_last_good("tenant-a", "forecast")
        self.assertTrue(served["served_as_last_good"])
        self.assertEqual(served["generation_id"], "generation-1")
        self.assertEqual(self.publisher.pointer("tenant-a", "forecast"), before)

    def test_tenant_state_pit_and_model_fences(self):
        first = candidate()
        self.publisher.publish(first, None)
        other_tenant = candidate("other-tenant-gen", tenant="tenant-b")
        self.publisher.publish(other_tenant, None)
        with self.db.connection() as db:
            keys = db.execute("SELECT object_key FROM artifact_blob_registry ORDER BY tenant_id").fetchall()
            self.assertEqual(len(keys), 2)
            self.assertNotEqual(keys[0][0], keys[1][0])
            self.assertNotIn("tenant-a", keys[0][0] + keys[1][0])
        with self.assertRaises(ValueError):
            candidate(item_identity=identity(state="different"))
        with self.assertRaises(ValueError):
            candidate(item_identity=identity(pit="different"))
        with self.assertRaises(ValueError):
            candidate(item_identity=identity(tenant="tenant-b"))

    def test_atomic_directory_backend_never_replaces_existing_key(self):
        local = AtomicDirectoryStore(self.root / "objects")
        first = b"stable"
        h1 = sha256(first).hexdigest()
        self.assertTrue(local.put_if_absent("immutable/object", first, h1))
        self.assertFalse(local.put_if_absent("immutable/object", first, h1))
        second = b"replacement"
        self.assertFalse(local.put_if_absent("immutable/object", second, sha256(second).hexdigest()))
        self.assertEqual(local.get("immutable/object"), first)


if __name__ == "__main__":
    unittest.main()
