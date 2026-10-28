# P0 Architecture Viability Gate — execution checkpoint (2026-10-28)

**Authority:** Management approval in conversation, tracked in [GitHub #490](https://github.com/jderhagopian-stack/fsffl-next/issues/490); related unresolved [#481](https://github.com/jderhagopian-stack/fsffl-next/issues/481), [#405](https://github.com/jderhagopian-stack/fsffl-next/issues/405), [#479](https://github.com/jderhagopian-stack/fsffl-next/issues/479). Continue under root `AGENTS.md`, `docs/operations/OPERATING_PROTOCOL.md`, `docs/operations/CURRENT_OPERATIONS.md`. This workstream is independent of the active Career memory-correction PR #489. Do not redeploy or retune that branch under this gate.

## Primary question
Are the verified model methods economically and operationally viable if disentangled from the web host, or is continued work on the application architecture less rational than selective rebuilding?

**Hypothesis (unproven):** retain accepted simulation, Career/Shapley numeric and canonical State/publication contracts, but decouple resource-intensive computation from read-only web serving. Test rather than assume.

## Evidence and identities at gate open
- Repo `jderhagopian-stack/fsffl-next`; main commit `271a8a8be8dc7611f9fc6df1a8f5f9182b5a747c` (documentation merge following accepted `6d1259e1f5f55078398814a6c2383f7a0d544b84`).
- Live Render `dep-dbgm32rvvlss73b2gs2g` at `6d1259e...`; 0.5 CPU, 512 MiB instance; production changed **zero** times by this viability workstream.
- Production Career model has repeatedly exceeded the `536,870,900`-byte guard. Existing browser and 335-row composer tests are synthetic/proxy, not an integrated hosted reproduction.
- [#481](https://github.com/jderhagopian-stack/fsffl-next/issues/481) already identifies late memory admission in the shared process. Any conclusion must account for the CPU/memory/storage cost of BOTH web and worker.

## Stage 1 — offline process-boundary screening (the research draft PR)
- Reuse the **unchanged** 335-row Career composition test `tests/test_career_forward_intrinsic.py::test_career_composer_materializer_peak_rss_below_budget`.
- Execute in fresh CI processes for both arms: `shared` imports the persistent FastAPI module and executes composer in the same process; `isolated` imports the same application module but runs the same composer in a child process.
- Record initial web module RSS, post-composer/process high-water RSS, independent worker high-water and time, sampled sum of RSS, and a health read before/after worker termination.
- Deliberately terminate a separate worker (exit 47) to show parent survival as a narrow boundary assertion. This is NOT evidence of crash-safe persistence, last-good recovery or actual cgroup OOM behavior.
- Write a self-labeled JSON report, no credentials, private league/roster data, provider requests, or database operations.
- CI uses Python 3.11 and `[dev,web]` dependencies; one dedicated research workflow uploads the sanitized JSON as an artifact. Avoid asserting that this matches Render's Python 3.12.10 or hosted operating limits.

**Limitations:** the fixture clones a single Career sample into 335 rows. Neither arm exercises true exact-State Y1 acquisition, dynamic roster P0, Y4–Y7, Y8 tail, provider cutoffs, actual web startup restoration, concurrent requests, cgroup accounting, job persistence or publication. Sum of process RSS can double-count shared pages. Shared app module import does not equal live serving. No A/B/C decision from Stage 1 alone.

Run from a checkout:
```sh
python -m pip install -e '.[dev,web]'
PYTHONPATH=. python scripts/run_architecture_viability_probe.py --repeats 2 --output /tmp/architecture-viability-proxy.json
```

## Stage 2 — decision-grade real full-State experiments (NOT STARTED)
1. Choose one previously accepted preserved full State and freeze input/model signatures, provider cutoffs, roster identity, source evidence and reference numerical checksums. Handle only in an authorized PRIVATE runner; never public GitHub artifact.
2. Run isolated same-input real model: full Year1, future, P0, F4, Shapley, Career and 3-Year, with process-phase RSS, CPU, time, numeric parity and full-cohort reconciliation. No source rule changes.
3. Measure saved-session web reads/restore separately without computation; record State/generation, useful render/p95 latency, DB/artifact bytes and memory.
4. Execute a combined-process reference with the exact same real workload on an appropriately bounded nonproduction runner, then a genuinely isolated worker/job experiment. Distinguish subprocess-inside-one-container from independent resource envelopes.
5. Inject worker crash/OOM, interrupted checkpoint, State supersession and no-op replay. Assert unchanged published pointer/last-good, no partial publication, exact-State safety, idempotent retry and continued web readiness.
6. Execute >=3 representative full runs after restart; monitor normal/peak memory, throughput and operating margin; budget and account for total worker/web CPU, RAM, provider and data costs.
7. Demonstrate modularity with one bounded new Explore product slice after the P0 is stable; count touched components, unrelated regressions and total delivery effort.

## Decision standards
- **A RETAIN:** all semantic, hosted-reliability, memory-headroom, repeatability and modularity gates pass for the current design.
- **B RESTRUCTURE:** numerical and data contracts remain correct, but shared-execution architecture fails while separately budgeted worker + stable web succeed. Preserve validated code and data; rebuild worker/job boundary and rollback mechanics.
- **C SELECTIVE REBOOT:** foundational semantics or authority/publication contracts remain unsound after isolation, or cost/complexity is demonstrably worse than a bounded replacement. Do NOT discard valid research/models/history just to rebuild orchestration.
- Target >=20% real operational memory margin, not merely sub-512 MiB success; budget foreground responsiveness and refresh runtime *before* Stage 2. No 100k-league viability assertion without measured unit costs and a scale sensitivity model.
- Any failed run stops repetition until evidence is adjudicated. One named bounded follow-up measurement or a management A/B/C decision, never recurring open-ended memory patches.

## Checkpoint status
- GitHub #490 created as cross-workstream management gate.
- Branch `research/architecture-viability-gate-20261028` based on main `271a8a8...`; script/workflow staged.
- **NOT YET RUN** when this checkpoint was written. No PR CI result, full-State workload, design acceptance or production change claimed.
- Next step: open **draft** research PR, inspect its CI and sanitized JSON, correct only screening-harness faults, then formally decide and execute Stage 2 in a private approved nonproduction environment. Do not confuse an offline screening success with architecture acceptance.

## Safety
No live refresh, service provisioning, secrets, schema, production writes, publication, storage migration, pricing changes, new paid resources or merge/deploy is approved by this stage. Do not put preserved private league State in the public repository or CI logs.


## 2026-10-28 — Stage 1 green and archived private Foundation4 replay executed

**Stage 1 exact head:** `d976a9bb0f4e36a024fc8312a83e53b139bfe96d`; [GitHub Actions run 40685798816](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/40685798816) **PASSED** with two repetitions per process topology. Parent stays healthy after intentional worker exit 47. Synthetic 335-player composer proxy: shared-process RSS peaks 251,846,656 / 250,204,160 B; parent-only sampled peaks 232,296,448 / 232,411,136 B; isolated worker peaks 232,062,976 / 232,247,296 B; summed sampled RSS proxies 444,243,968 / 446,406,656 B. This does NOT capture actual cgroup memory, full live workload, or private-State publication. The benchmark indicates parent fault/memory separation but NOT reduction in aggregate system memory.

**Private preserved data availability:** user's Library contains `CAREER_405_WEEK5_EXECUTED_CHECKPOINT_20261013.zip` (~30,142,129 bytes). It was privately materialized into a local analysis container, NOT added to GitHub, CI, or any service. Archive includes exact historical State, baseline, cached provider evidence, original complete Career outputs/logs, frozen model policies and standalone Foundation4 source/data. Historical 2026-10-13 checkpoint (old code) reported 353 Career estimates/19 dynamic inputs and full-path peak RSS 436,731,904 B (~416.5 MiB), above the 429,496,720-byte operating target but below the 536,870,900-byte hard cap. Historical run is NOT today's production acceptance.

**Actual archived F4 local components exercised** with unchanged bundled research `dev.py`/`route.py` on local Python 3.13.5 (not supported production 3.12): full historical model feature matrix 43,919 rows × 167 columns, horizons Y4–Y8, standalone process peak 356,872,192 B / 1.892 s; one policy-listed WR/Y4 specialist fit consumed 2,735 train and 239 evaluation rows, peak 356,167,680 B / 3.234 s including feature assembly. No current-code numerical parity claim due different runtime/dependencies. Private raw files remain local and unshared.

**Next**: Run *complete* frozen exact-State replay on a private matching current checkout and governed Python 3.12 runtime (not provided in the present local container, which cannot reach GitHub remotely), comparing combined-hosted-like and isolated-worker configurations, with active read path, cgroup peak, exact-State identity, original numerical fingerprint, publication survival on failure, and measured total cost. Preserve no-new-spend/no-live-deploy. Stage 2 A/B/C decision remains open. See #490 comment for full caveats. Do not publish the archive to the public GitHub repository, CI, or issue attachments.
