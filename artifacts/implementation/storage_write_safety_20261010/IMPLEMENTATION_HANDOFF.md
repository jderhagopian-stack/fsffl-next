# FSFFL NEXT — immutable object write-safety prototype

**Starting main:** `904cb0c523be9dd143788c90fc108671f3e1c423` (after the October 10 documentation-only acceptance checkpoint).  
**Scope:** bounded offline prototype only. No Supabase/Render connection, credentials, live experiment, schema mutation, production wiring, migration, or deployment.

## Decision from the contract review

Keep the failed S3 conditional `PutObject` implementation at strict **NO-GO**. Supabase's Standard Storage Upload API is a narrower existing Supabase path with a published no-overwrite contract: default upload to an existing path fails; for concurrent uploads to one path, the first completed upload wins and the others receive `Asset Already Exists`. The API exposes overwrite only through `upsert=true` / `x-upsert`. See [Standard Uploads](https://supabase.com/docs/guides/storage/uploads/standard-uploads#concurrency).

The pinned Supabase Storage implementation corroborates the contract: each upload is staged under a generated version, completion serializes on an object lock, and the non-upsert path does not replace a live object row. Its database uses a unique key index on bucket/name. See [`uploader.ts`](https://github.com/supabase/storage/blob/f31599e188d7c9c854b1daa76a11b41c6d179462/src/storage/uploader.ts), [`pg.ts`](https://github.com/supabase/storage/blob/f31599e188d7c9c854b1daa76a11b41c6d179462/src/storage/database/pg.ts), and [initial Storage schema](https://github.com/supabase/storage/blob/f31599e188d7c9c854b1daa76a11b41c6d179462/migrations/tenant/0002-storage-schema.sql). In contrast, the S3 matrix lists conditional operations for `HeadObject`/`GetObject`, not `PutObject` ([S3 compatibility](https://supabase.com/docs/guides/storage/s3/compatibility)).

The smallest sound protocol is:

1. Canonicalize the artifact and zlib-compress it. Use a tenant-namespaced, content-addressed object path containing the codec and SHA-256 of the exact stored bytes.
2. Upload through Supabase Standard Storage with `upsert=false`; never fall back to an overwrite. On `Asset Already Exists`, download the existing object and require exact bytes and expected SHA-256. Otherwise fail closed.
3. Only after the object is readable and hash-verified, open one authoritative PostgreSQL transaction through the existing bounded persistence path. First-writer-insert the immutable artifact identity → object/hash/size reference; compare all fields on conflict. Insert a complete immutable manifest/generation referencing the exact tenant, State, PIT State and artifact identities. Advance the active publication using compare-and-swap on the expected generation. Commit together.
4. If the process fails after object creation but before the database transaction commits, the object is an unreferenced orphan; no reader can discover it through FSFFL metadata and no publication pointer moves. Retry is safe because the object path is create-only and bytes are rechecked. Any future orphan collector must prove no registry, manifest, last-good, PIT or replay reference exists and wait past an upload grace period.
5. Readers resolve only the committed manifest/pointer, verify object length/hash before decompressing, then apply existing Pydantic decoders. Integrity or generation failure leaves the pointer unchanged and uses only the existing accepted last-good path. Object names are tenant-namespaced; no cross-tenant deduplication is introduced.

This deliberately prototypes the transaction boundary in SQLite and the object contract with an offline API model. It does not claim a live Supabase integration test. The Storage API's internal `storage.objects` registration and the FSFFL artifact/publish metadata transaction are separate transactions; ordering blob-first and publishing app metadata last makes a failed second phase leave an invisible orphan rather than a dangling published pointer.

## Prototype and focused evidence

`write_safety.py` provides the content-addressed codec, no-overwrite adapter, exact identity registry, complete-generation reference set, transaction/CAS publisher, integrity-checked reads and unchanged last-good fallback. The local directory backend uses write-to-temp + fsync + atomic hard-link create (never `replace`). The Supabase API port is injected and has no client credentials or network implementation.

Run offline:

```sh
python -m unittest -v tests.test_storage_write_safety_20261010
```

**Result: 12 tests passed** on Python 3.12.14. Coverage includes concurrent identical retry, concurrent conflicting first writers, no-overwrite and exact-object verification, identical-byte content addressing, write/transaction failure and safe orphan retry, stale CAS rejection, generation-ID collision, manifest/State/PIT/tenant fences, hash corruption with last-good service, preserving last-good after a corrupt current object, and atomic local create. `py_compile` passed. These are local prototype tests; GitHub focused CI should run the same 12 tests. No hosted provider test or production acceptance is claimed.

## Production gates that remain closed

- Pin and review the exact Supabase Storage SDK/API call and error mapping in the application; actual project/API test remains unrun by instruction.
- Add a constrained migration and read path inside the existing `PersistenceStore` and existing publication owner. Do not create a second lifecycle controller or move any State, manifest, PIT, last-good, history, replay or tenant authority.
- Test the real PostgreSQL transaction under concurrent writers, commit/rollback, idempotent retry, interrupted upload, ambiguous API response, corrupt/missing object, concurrent generation advance, restart, legacy fallback and rollback.
- Include precise object ownership/retention, orphan collection, signed server-side access and private bucket/RLS design; keep broad credentials out of clients/logs.
- Shadow-read exact existing rows and match raw hash, full `ReusableArtifactRecord`, Pydantic outputs, publication identity and restore/replay behavior before any separately authorized removal of PostgreSQL payloads.
- A copy/rewrite needed to return physical DB disk space has separate locking, temp-disk, rollback and current quota headroom gates; ordinary DELETE/VACUUM does not promise project disk shrink.

**Disposition: PROTOTYPE PASS / PRODUCTION NO-GO.** Existing Supabase Standard Uploads provide a documented create-only capability suitable for the candidate protocol. The actual application integration, database transaction, recovery behavior and data migration remain untested and unauthorized by this tranche.

