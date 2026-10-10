# iPhone-only, private storage validation — Render Workflow

**Historical 2026-10-09 pre-run preparation snapshot; superseded by the 2026-10-10 NO-GO checkpoint below.** It described a runnable Workflow definition before the hosted test and is retained for audit, not current status. Keep PR #441 DRAFT / unmerged. It is deliberately separate from the LIVE main service and from draft #439.

## 2026-10-10 — real Forecast/Simulation storage comparison: NO-GO

The real-artifact task ran on the isolated Render Workflow from PR #441 head `c3bf666a5251ff9748abb2c3d4ddf1b8372e0b23`. Run `trn-0b14gdb4nmaa396pc73ec6sng` failed after 12.1 s (8.1 CPU s; $0.0004815 recorded task cost). These are nonproduction validation results only.

| Artifact | PG JSONB datum | PG text | Canonical bytes | zlib/S3 bytes | compressed / JSONB | Encode | PUT | S3 GET + rebuild p50 / p95 | PG get + decode p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Forecast | 161,373 B | 3,277,189 B | 3,073,225 B | 86,020 B | 0.533 (46.7% smaller) | 44.16 ms | 242.63 ms | 232.39 / 349.86 ms | 178.46 / 354.17 ms |
| Simulation | 118,887 B | 727,232 B | 689,400 B | 67,816 B | 0.570 (43.0% smaller) | 13.81 ms | 144.86 ms | 96.04 / 135.78 ms | 36.24 / 136.97 ms |

Each latency distribution used 9 samples. Both artifacts passed exact reconstruction, record/hash and deployed-decoder parity, restart, and corruption checks. Decoder CPU was Forecast 1,841.51 ms S3 / 1,738.49 ms PG; Simulation 315.34 / 313.32 ms. Combined case CPU was 3,758.78 ms and 684.62 ms respectively. Process peak RSS was 327,585,792 B (312.5 MiB), 101,910,928 B below the 429,496,720 B working budget.

**The final immutable-write gate failed.** The task raised at the conditional first-writer `PutObject` probe after collecting comparison metrics and before emitting GO. The exact exception was deliberately sanitized, so it is not known whether the endpoint rejected the condition, ignored it, or failed for another reason. Supabase's published S3 compatibility matrix documents conditional `If-None-Match` for reads, not `PutObject`; this is consistent with the failed gate but does not identify the exact exception: https://supabase.com/docs/guides/storage/s3/compatibility. Do not remove the condition or treat process-local check-then-put as immutable/atomic. Smallest sound correction: retain NO-GO for Supabase S3 immutable writes; use an object service with verified atomic conditional `PutObject If-None-Match: *`, or separately design and prove an atomic database-coordinated publication protocol before reconsidering this backend.

**Cleanup/evidence classification:** Task logs independently recorded zero remaining test objects. In the Dashboard, the S3 key list was independently observed empty after revocation; the Workflow environment was independently checked after secret removal and contained only `PYTHON_VERSION`. These UI checks occurred before the operator-reported Workflow deletion. Management confirms deletion through the Dashboard; deletion itself has not been independently rechecked from a service inventory. No credentials are retained here. The empty private test bucket was not reported deleted. Production app, database rows, and deployment were not changed.

**Disposition: NO-GO.** Compression and reconstruction results are promising but cannot override the failed immutable-write requirement. This does not authorize production integration, deployment, another run, credential creation, or spend. Prior read-only transaction safeguards did not make the broad production database URL a least-privilege credential; any separately authorized future test must use purpose-limited read-only DB access.

## Existing, independently verified state

- GitHub main: `26be30ccf9f6a3e184fe221456cb316451d60f2b`. Live Render web: service `srv-dae6k7vqj5pc73af7bt0`, 0.5 CPU/512 MB, deploy `dep-db4m539srm7s73881fg0`, **unchanged**.
- Supabase `gldxkbqcprzuffgmamxl` on Free; private test-only bucket `fsffl-private-storage-validation-20261009` (8 MiB/object, `application/octet-stream`, public=false), presently empty at last verified read.
- Exact DB rows `fsffl.derived_artifact.id IN (11540,11541)`, Forecast + Simulation. PostgreSQL original compressed JSONB datums 161,373 B + 118,887 B. These are baseline comparators, **not real zlib or S3 results**.
- Frozen nonproduction PR #439 `hybrid_adapter.py` has been copied **unchanged** (Git blob `dcb3cf0114a16602dd913e4937da21e9082443a5`) into this workflow directory. No second storage architecture has been designed.

## Exact iPhone Safari execution route (not CLI)

1. **Permission / additional charges gate before creation.** Render Workflows Flex is separate pay-per-use compute: **$0.20 per active CPU-hour + $0.05 per GB-hour of occupied RAM**, up to 1 CPU / 4GB; worst allowed sustained rate $0.40/hour. There is NO second required fixed subscription, but task usage, outbound bandwidth, and task state retention ($0.25/GB, retained 30 days) can be billed. Workflow builds use pipeline minutes. Task runs start isolated from your paid web service and require no computer or terminal. [Render pricing](https://render.com/docs/workflows-limits), [Hobby allowance](https://render.com/pricing). **Operator must approve creating this extra billable service/task before proceeding.**
2. Open [Render Dashboard](https://dashboard.render.com/), choose existing **My Workspace**, tap **+ New → Workflow**. If controls are hidden on narrow Safari display, use Safari's *Request Desktop Website*.
3. Link the EXISTING public GitHub repo `jderhagopian-stack/fsffl-next`; select the **draft #441 branch** `docs/private-storage-validation-access-gate-20261009` (**not** `main`). Fill exactly:
   - **Name:** `fsffl-private-storage-validation`
   - **Language/runtime:** Python 3
   - **Region:** Virginia
   - **Root Directory:** leave blank (repo root)
   - **Build Command:**

     ```bash
     bash artifacts/implementation/private_storage_validation_20261009/build_workflow.sh
     ```

   - **Start Command:**

     ```bash
     python artifacts/implementation/private_storage_validation_20261009/workflow_entry.py
     ```

   - **Auto-deploy:** OFF (avoid release from later unrelated draft pushes); Workflow always has isolated task instances. **Do not alter** any settings on the production web service.
   - **Build-time environment:** `PYTHON_VERSION=3.12.10` (new Render Python services otherwise default to Python 3.14, which violates this repo's `<3.13` requirement). Set this **before initial Deploy Workflow**.
4. Tap **Deploy Workflow**, which registers the tasks. Its initial build must PASS the focused, credential-free `pytest` test and compilation before tasks become available. In the Workflow's **Tasks** page, open **preflight**, tap **Start Task**, put exactly `[]` (no arguments), and tap Start task. It should return `{"status":"PASS","scope":"synthetic_preflight_no_production_access"}`. This is NOT the real validation.
5. In Safari, visit [production service Environment](https://dashboard.render.com/web/srv-dae6k7vqj5pc73af7bt0), *view/copy* its existing `FSFFL_DATABASE_URL` value **without changing or deploying production**. If this secret cannot be viewed/copied, use the existing Supabase database connection UI to obtain the working database URL in Safari rather than altering any production env. **Never paste the connection string into chat or GitHub.**
6. Open [Supabase S3 settings](https://supabase.com/dashboard/project/gldxkbqcprzuffgmamxl/storage/s3). Create a **temporary server-side S3 access-key ID/secret pair**, if Management approves full-project-scope temporary credentials. Supabase S3 access keys bypass bucket RLS and can access **all** buckets. No key can be restricted to just the validation bucket using that key class. Alternative short-lived Auth JWT/RLS would require additional separate design/operator policy work. Keep keys in Safari only; **do not put them in the task's `[]` inputs** or public code/logs.
7. In the **new Workflow service's Environment screen only**, configure:
   - `FSFFL_DATABASE_URL` = existing DB connection string from step 5
   - `FSFFL_TEST_S3_ACCESS_KEY_ID` = temporary Supabase S3 access key ID
   - `FSFFL_TEST_S3_SECRET_ACCESS_KEY` = corresponding temporary secret
   - `PYTHON_VERSION` already set to `3.12.10`

   Save/deploy **only the new Workflow** so its task instances receive the variables. No credential value belongs in public GitHub or task input/output. Do not link production and test services to a new shared environment group.
8. Inside the new Workflow's **Tasks**, choose **validate_real_artifacts**, press **Start Task**, supply **`[]`**, start exactly **one** run. Auto retries are explicitly zero. Inspect its Runs page and only share **sanitized aggregate figures**, such as `pg_jsonb`, `canonical`, `zlib_s3`, `get_rehydrate_p50_ms`, `get_rehydrate_p95_ms`, `pg_get_model_p50_ms`, `pg_get_model_p95_ms`, `s3_read_decoder_cpu_ms`, `pg_read_decoder_cpu_ms`, `total_case_cpu_ms`, `process_peak_rss_bytes`, decoder/hash/restart/corruption status, and `test_objects_cleanup_remaining_count`.
9. Verify **zero objects remaining** for the test bucket after run; if not zero, remove only test-created objects through the bucket UI. **Revoke temporary S3 keys** from Supabase settings. Remove `FSFFL_TEST_S3_*` and the copied database string from the new Workflow environment, then suspend/delete the temporary Workflow service after recording aggregate results. This affects no serving process.

## Scope and safety properties

- **Zero task arguments**, so Render's 30-day retained task input state cannot contain secrets or original data. Task output is an aggregate-only PASS dictionary. Full raw production data is only streamed into the task's ephemeral memory from two exact READ ONLY PostgreSQL transactions. No raw artifact payload, State IDs, secrets, object digests or private filenames are printed or returned. No paid Supabase upgrade, changes to existing published generations, publisher, last-good, PIT, models, team, or replay.
- The runner reads exactly ids 11540/11541 and checks their artifact kind, scope and current non-invalidation; real Pydantic decoder equality is against each DB row. It verifies exact `ReusableArtifactRecord` payload/key/time, canonical JSON SHA256, zlib storage size, real S3 PUT/HEAD/GET, nine repeated S3 vs SQL reads, local metadata process restart, synthetic corruption fail-closed and a conditional-write canary. Original PostgreSQL remains untouched and authoritative. **Atomic production pointer cutover is not tested and never authorized by a PASS.**
- Client uses the named new private bucket only and random test keys. It registers each attempted key for cleanup even if the remote PUT response fails. S3 errors are sanitized at the workflow boundary; no automatic retry. A conditional-put mismatch or decoder difference is NO-GO.
- The chosen S3 credential form is broad access, even though the Python restricts its bucket. Use only for this single approved short-lived test and revoke promptly. A read-only transaction does not narrow underlying database account permissions; strict least-privilege DB role would require separate approved security administration and is not created here.
- The build/test and registered preflight can be completed without S3 secrets. No real test is reported as complete until operator provisions credentials and explicitly presses Start Task.

## Links and authorization

- [Render Dashboard – create a Workflow via New → Workflow](https://dashboard.render.com/) (exact new Workflow service URL assigned AFTER creation; never invent the URL)
- [Existing production Render service, READ ONLY for DB URL](https://dashboard.render.com/web/srv-dae6k7vqj5pc73af7bt0)
- [Supabase Storage S3 credential management](https://supabase.com/dashboard/project/gldxkbqcprzuffgmamxl/storage/s3)
- [Supabase Storage project](https://supabase.com/dashboard/project/gldxkbqcprzuffgmamxl/storage/buckets)
- [Render Workflows Dashboard guide](https://render.com/docs/workflows-tutorial)
- [Render Workflow Flex billing](https://render.com/docs/workflows-limits)
- [Render service environment vars](https://render.com/docs/configure-environment-variables)
- [S3 all-bucket permissions warning](https://supabase.com/docs/guides/storage/s3/authentication)

**Required operator permission:** Render workspace Admin or Developer with create-service/edit-environment/start-task rights (Developer must be in non-protected environment). Supabase project Owner/Admin or another member explicitly authorized to generate server-side S3 keys. No Pro workspace or Supabase plan upgrade is needed.

**Go/No-Go:** A successful task is only a PRIVATE Phase 2 two-artifact backend-comparison GO, not a production storage architecture selection. Actual acceptance must compare object bytes with PostgreSQL, S3/DB p95, peak RSS vs the 429.5MB current working budget, CPU, decoder and corruption; evaluate conditional-write support and the dedicated test's observed economics. If any fail, do not weaken numerical tolerances or modify the serving application.
