# Career #405 roster runner access checkpoint — 2026-10-12

## Verified state

PR #455 is open on `career/405-roster-runner-20261012` at runner head `308b767698ceeb3f1e73d7e6c35f34c829c26150`. Focused test CI previously passed (run `38250705248`; five runner tests). No provider acquisition was run in this checkpoint.

The current workflow does **not** use the durable private store:
- Input is still bound to repository secret `CAREER_ROSTER_P0_ZIP_B64`.
- Output is still an AES-GCM encrypted GitHub Actions artifact with 90-day retention.
- It references `FSFFL_DATABASE_URL` and `CAREER_RUN_OUTPUT_KEY`, but no storage URL, object path, or storage credential.
- The workflow's live roster job is `workflow_dispatch` only. GitHub requires that workflow to be on the default branch before manual dispatch is available.

Read-only storage metadata inspection found one private Supabase bucket, `fsffl-private-storage-validation-20261009`, with an 8 MiB object limit and zero objects. This does not contain the roster checkpoint and is not proof that Actions can access it. The Supabase SQL integration exposed only metadata; no file was read or written.

The GitHub connector explicitly rejects the repository Actions secrets endpoint as a sensitive endpoint. Consequently, configured secret names/presence cannot be inventoried through this chat, and no secret values were requested or exposed.

## Gate and minimum unblock

The runner cannot safely read its current input or durably save outputs to the private store. The existing implementation offers neither connection, and the inspected bucket is empty. Do not launch it or repeat provider acquisition.

Minimum required setup is one authorized private-store handoff: make the accepted roster input available at a fixed object path in the existing private bucket and grant the runner a least-privilege, nonproduction read/write binding for that input and a run-specific output prefix. The binding must not be the production database credential or a bucket-wide service-role key. Once that exists, update the workflow to consume the object path and write encrypted per-player output plus a readable summary to the same private store.

A separate launch gate remains: under the current workflow trigger, dispatch is unavailable until the workflow is present on the repository default branch. Keep #455 unmerged as instructed; do not attempt provider work from this PR event.

## Next code gate after access

Replace the Base64 secret and 90-day artifact with private object-store input/output, add tests for bounded object paths, exact-State rejection, authenticated encrypted persistence and readable summary redaction, then run only the exact current roster. Continue complete Career composition and matching-State publication only after durable per-player run records exist. No production writes, merge, deployment, broad acquisition, or waiver processing.
