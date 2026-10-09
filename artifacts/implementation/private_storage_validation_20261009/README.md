# Render isolated real-artifact S3 validation — operator runbook (2026-10-09)

**Status:** PREPARED, **NOT EXECUTED**. Do not present results as measured until the secure run completes. This nonproduction tool lives only in draft PR #441; no deployed app, publish path, schema, retained production payload, or application contract is changed.

## Verified prerequisites

- GitHub deployed main `26be30ccf9f6a3e184fe221456cb316451d60f2b` live on Render `dep-db4m539srm7s73881fg0` after paid 0.5c/512MB upgrade, one production instance, auto deploy OFF.
- Render service `srv-dae6k7vqj5pc73af7bt0` supports **ephemeral isolated SSH** with latest build and service environment, separate from traffic-serving instance. It is billed for the seconds connected; avoid the ordinary shared-memory Dashboard Shell.
- Supabase organization is **Free**; test-only bucket `fsffl-private-storage-validation-20261009` was created and verified in project `gldxkbqcprzuffgmamxl`. `public=false`, allowed MIME `application/octet-stream`, 8MiB per-object limit. Storage Free includes 1 GB; no Pro upgrade.
- PostgreSQL records are **id 11540** current Forecast and **id 11541** current Simulation in `fsffl.derived_artifact`. Both are read by exact ID only, with `SET TRANSACTION READ ONLY`. No table/data mutations.
- #439 prototype remains a **draft**. Its exact adapter source is loaded transiently from frozen commit `fccb9e0f147fce6aae6e6360d66d3e4aff12a050`.

## Exact remaining operator access step

1. In Supabase Dashboard for project `gldxkbqcprzuffgmamxl`, go to **Storage > Settings > S3 access keys** and generate one **temporary server-only S3 access key pair**. This credential **bypasses RLS and can access all buckets**, even though the *test code* only targets this dedicated bucket. It MUST NOT be added to Render production environment, public GitHub/CI, chat, or logs. Revoke immediately after the test. If full-scope temporary credentials are unacceptable, STOP and separately design a bucket-scoped JWT/RLS S3 session with explicit permission and no production Auth changes.
2. From an operator-controlled terminal with Render CLI v2.20+ installed/authenticated and SSH key registered, execute **`render ssh srv-dae6k7vqj5pc73af7bt0 --ephemeral`**. This creates a separate temporary 0.5c/512MB instance with the latest successful build and existing `FSFFL_DATABASE_URL` inherited for read-only SQL. No web start command or production restart.
3. Inside **that ephemeral shell**, run exactly the following. The only interactive inputs are *masked prompts* for the two temporary S3 credentials:

```bash
set +x
python -m pip install --no-cache-dir --quiet 'boto3>=1.39,<2'
curl -fLsS -o /tmp/hybrid_adapter.py 'https://raw.githubusercontent.com/jderhagopian-stack/fsffl-next/fccb9e0f147fce6aae6e6360d66d3e4aff12a050/artifacts/implementation/storage_foundation_poc_20261008/hybrid_adapter.py'
curl -fLsS -o /tmp/render_s3_real_artifact_gate.py 'https://raw.githubusercontent.com/jderhagopian-stack/fsffl-next/c627fdccfd5a7c626cdbbffbcaeda6ed2f090d82/artifacts/implementation/private_storage_validation_20261009/render_s3_real_artifact_gate.py'
PYTHONPATH=/tmp python /tmp/render_s3_real_artifact_gate.py
```

**Pin check:** the second URL references the current validated script commit in the draft PR at the time of this runbook; reconcile with latest PR #441 head and *update the pinned URL if the script changed*. Never fetch unreviewed moving-head code into a credentialed shell.

4. Preserve only **aggregate** console metrics: PostgreSQL JSONB/canonical bytes, zlib object bytes, bounded nine-sample PostgreSQL vs S3+model p50/p95, encode/PUT time, process CPU/peak RSS, decoder/hash/restart/corruption pass or sanitized exception class, and cleanup count. Do not share raw artifacts, original State/tenant IDs, digests, stack traces, SQL values or credentials. If `cleanup_remaining_count != 0`, use the Supabase private bucket UI to inspect/delete only test-created keys before revoking credentials. Close the ephemeral shell with `exit` promptly. Revoke the temporary S3 access key pair.

## Acceptance boundaries

The runner imports the existing #439 canonical zlib/identity/SQLite prototype, substitutes a real boto3 S3 object interface, fails closed if Supabase S3 ignores immutable conditional writes, uses original `ArtifactKey` and `computed_at` when rehydrating `ReusableArtifactRecord`, and passes both full objects through existing `decode_forecast_evidence`/`decode_simulation` functions. It does not imply a *tenant authenticated on S3* (the proof uses an explicitly synthetic isolated test namespace) and does not exercise production pointer or manifest publication. It verifies no production write, but production integration/fencing, backward-compatible reader and PIT history must be separately proven before any production GO.

The test is intentionally bounded to two existing rows, 9 read measurements per family per backend, one random object prefix, and always-attempted cleanup. A transient isolated instance incurs **extra prorated compute charges** while connected; no plan change is requested. A private Supabase bucket does not imply S3 access keys are bucket-scoped. For any failure, report NO-GO/blocked with the smallest next action; never silently relax hashes, decoder contracts or authorization.

Full durable status is the canonical `docs/operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md` checkpoint. Tranche 1 #440 remains accepted/live; #439 remains draft; #441 is a separate checkpoint/test-runner draft and must not be deployed.
