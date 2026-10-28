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


## 2026-10-28 — Three private archived full Y4–Y8 route repetitions
The pre-existing PRIVATE archived October 13 Week-5 frozen-model inputs were run locally for every accepted historical `hard_candidate` position × horizon combination: **20 of 20 completed**, 43,919 history rows, 2,908 evaluation rows in the latest supported historical origin. Three fresh Python 3.13.5 processes each produced identical 20-cell numerical output checksums (not published). Peaks 449,396,736 B / 446,730,240 B / 450,928,640 B; elapsed 29.317 / 27.957 / 33.149 seconds respectively. Every isolated run exceeded the 429,496,720-byte operating target yet stayed below the 536,870,900-byte hard cap. This is archived code / nonproduction historic F4 only, **not** the current Career refresh, app+worker workload, production runtime or pricing gate. See #490 evidence comment; raw replay data never left the private local container.

The current-code sanitized research runner has been added on PR #491 under `scripts/run_architecture_current_code_probe.py`. It runs actual repo numeric frozen-335, 335 persistence, restart restore, dynamic roster bridge and last-good assertions in independent processes; it cannot by itself validate complete hosted operations. First CI attempt failed before any tests because Ubuntu 26.04 lacks the required exact Python 3.12.10 toolcache. Research workflow pinned ONLY the current-code job to Ubuntu 24.04 and is rerunning on PR #491. Do not interpret runner provisioning failures as model failures.


## 2026-10-28 — Stage 2 private exact-State current-code topology comparison complete (nonproduction)

**Saved sanitized evidence:** `docs/operations/evidence/architecture_viability_stage2_private_replay_summary_20261028.json` at research branch PR #491. All private raw inputs/results stayed in the isolated local container; the public record contains only aggregate metrics and historical test counts. No credentials, raw player identities, State identifiers, forecasts or private artifact payloads were published. No Render/Supabase changes, production refresh, recurring service or paid spend.

**Inputs/authority:** public source snapshot from research PR head `ec0d9b0582ddc165a45edc2d120d6be5256166e0`, archived private October 13 Week-5 real-State/current-Y1/ROS input evidence, and full 12-file frozen accepted Foundation 4 bundle whose pinned checksums validated against code. Direct provider/network acquisition disabled. Historic callback adapted only to current Python signature (accept `projection_history_as_of` keyword). This is exact preserved State, NOT October 28 live league State.

**Environment caveat:** local isolated Linux Python 3.13.5 with NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.8.0, not governed hosted Python 3.12.10/NumPy 2.5.3; 4 GiB container, not the Render 512 MiB cgroup. Real authenticated production web-restore, database publication, last-good across worker crashes, source provider access and game-day traffic were not executed. HTTP health GET is not representative of all foreground routes.

**Result:** same 353 estimate IDs as original archive, same 19 appended dynamic Career candidates and nine prior explicit coverage failures; exact raw numerical match (max abs delta 0.0) for Y1–Y3, Y4–Y7, Y8+ and total Career for all 353 accepted estimates. Exact State identity preserved. Previously mismatched 334-only attempt was from obsolete *harness* callback and was corrected without production-model changes. Position/Depth 252 rows built.

**Performance, all current research-branch code and same preserved input:** 
- Standalone full Career path: peak process RSS 324,083,712 B (~309.1 MiB), elapsed 198.511 s.
- Shared web-module-loaded process running same Career: peak RSS 343,666,688 B (~327.7 MiB), elapsed 203.096 s; 670 health GETs, 0 failures, p95 187.84 ms, max 434.96 ms.
- Web parent plus separate child worker: parent peak sampled RSS 216,887,296 B; worker peak sampled RSS 326,184,960 B; sampled max **sum** RSS 538,386,432 B (NOT actual container cgroup peak; shared pages double-counted), elapsed 202.044 s total; 989 health GETs, 0 failures, p95 6.05 ms, max 183.21 ms. Worker finished with exit 0, identical 353-row numerical outputs.
- A supplemental proportional-memory (PSS) sampler returned zero valid samples and is **invalid**; do not cite it as a passing resource measurement.
- The earlier 3× historical frozen Foundation 4 research route reproducibility is separate, not three executions of this complete current-code topology gate.

**Meaning:** historical accepted analytical math remains executable with strict parity and apparently materially lower process memory in this particular offline replay than the 2026-10-13 archived baseline. Isolating compute sharply improves this *health-read* responsiveness and prevents the web process from retaining the model worker's large RSS, but increases aggregate process RSS. At 512 MiB, a same-container split has no demonstrated safety margin; **independently bounded work capacity** should be the design candidate. The success does not invalidate recurring observed live Render OOM/blank charts on the current full web+DB restore workload.

**Preliminary decision:** prefer **B — retain accepted model/State/publication contracts, restructure heavy compute into independently budgeted worker/job ownership**, with a production-runtime and cost/last-good gate before approval. Reject both indiscriminate platform reboot and further endless memory-only patches as default paths. Do not mark Stage 2 production gate complete. The next bounded task is a no-production-change design/prototype of durable job handoff and worker recovery contract using accepted immutable State/manifest/publication keys, plus an exact Python 3.12.10 resource/cost proof in a permitted private environment. Review expected ongoing price before any service purchase.
