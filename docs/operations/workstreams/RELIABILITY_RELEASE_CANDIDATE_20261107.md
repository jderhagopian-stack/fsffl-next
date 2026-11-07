# Local reliability release candidate — 2026-11-07

## Deployed release — hosted refresh acceptance pending

PR [#489](https://github.com/jderhagopian-stack/fsffl-next/pull/489) merged as squash `02ffb963218d2a1408ecb58b1c07a563e9845054` from exact tested head `3da7891be3489a1fcc5a2f4a62659cac47b20704`. Both commits have identical Git tree `a5dec5f04379f6c01be6a55b9e983109d16c4501`. Exact-head CI [42410646529](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42410646529), Intrinsic diagnostics `42410646636`, Forecast trace `42410646627` and PR164 `42410646540` passed. Stable full suite [42410655322](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/42410655322) passed **2,660 tests, 5 skipped**, 677.20s, with before/after head checks successful. Automated review returned a clean +1 on the corrected head at 20:23:27Z; both earlier findings are resolved. No full suite was repeated on the merge push.

Existing Render service `srv-dae6k7vqj5pc73af7bt0` deployed that exact merge SHA as `dep-dbnoncu7bikc73d4oc3g`, **live at 2026-11-07T20:37:35.958383Z**. The deployment-ended event reports succeeded. One instance, 0.5 CPU/512 MiB, branch main, auto-deploy off; no plan/configuration, provider, worker or schema change. Build logs confirm NumPy 2.5.3, pandas 2.3.3, scikit-learn 1.9.1, SciPy 1.18.1, Pydantic 2.14.3, FastAPI 0.162.2 and Starlette 1.10.0. Build success and live status do not prove a completed full refresh.

Startup at 20:37:39Z reported RSS **281,247,744 B**, process peak **295,448,576 B**, working budget **429,496,720 B**, active heavy work none, waiters zero. **Readiness is partial**, not fully accepted: the restored State is `ab0607e3339f7810b2b93b40b63e1b5246165640e4fd6c6b3b490aa6b19bec6d`, dated October 28; Forecast/Simulation are unavailable, Value is present, Current Intrinsic unavailable. Seven startup fallback error records report `Sleeper current-input cutoff does not match canonical State`. Preserve that cutoff guard; do not combine current-week provider facts with the older saved State or describe startup as full/healthy intelligence.

The required next test is one authenticated Refresh Intelligence action to synchronize State and source cutoffs, then observe the complete calculation/persistence/presentation path. The assistant has asked the user to start it once from their signed-in browser; no authenticated session is available in this execution workspace. No agent-initiated production refresh has run. Keep the refresh memory, complete current-roster Career/3-Year/Position & Depth, exact-State/publication and physical acceptance gates open. Do not automatically repeat a failed run or infer refresh safety from startup RSS.

Previous known deployment is `dep-dbk1lni9lscs73fk2khg` on `6d1259e1f5f55078398814a6c2383f7a0d544b84`. Keep this identity for incident/rollback comparison. This record and subsequent checkpoint changes are documentation-only and require no second full-suite run under AGENTS.md.

## Subsequent authorization — controlled existing-service deployment

The user challenged withholding deployment because hosted testing is necessary. The execution direction is now to advance this candidate through exact-head CI/review and deploy it to the existing Render service, then observe one controlled authenticated refresh. The unavailable private replay package is no longer an absolute predeployment prerequisite. Preserve the existing 0.5 CPU/512 MiB service, hard guard, model/source rules, cohort coverage, atomic publication and last-good; stop and diagnose if the single run fails rather than repeating it. No plan/provider/storage migration or new worker is authorized.

PR #489 was returned to draft before updating its head. Its history is being reconciled by a normal merge (retaining the tested saved-roster correction) so the existing PR branch can advance without force-pushing or opening a competing memory PR. Historical statements below describe the preceding local-only checkpoint.

Current Render deploy/health documentation could not be fetched as either Markdown or HTML (network proxy HTTP 403). Use the connected deployment API and observe actual live state/health; do not infer unverified platform timeout thresholds from memory. No Blueprint or health-check configuration change is required for this existing-service deployment.

### Exact-head automated review correction

PR #489 head `b005fa6e48e87097ef95efc265c089cf31c72c3a` passed its focused checks, but automated review found that candidate-only weekly stats could erase full-feed passing/sack schema evidence needed by the unchanged fumbles supplement. The PR was returned to draft before correction. Keep candidate-only ordinary actuals and a separate supplement input containing candidates plus real schema-witness rows, bounded by at most four extra rows per acquired week under the accepted model's required-field set. Full-response fingerprints and chronology checks remain unchanged; no field is synthesized, and a genuinely incomplete feed still fails closed. Release the extra references with the other acquisition inputs before subsequent model phases.

Regressions compare the real supplement's complete candidate observations/evidence against the full feed, cover non-QB and cold-start inputs, enforce bounded retention and actual-source rows, and prove that the production P0 builder passes the witnesses to its cached supplement source. The focused CI now includes these tests. The earlier full-suite run is not acceptance for the corrected head; exact-head checks and review must run again.

### Corrected remote candidate — verification in progress

Corrected PR #489 head: `3da7891be3489a1fcc5a2f4a62659cac47b20704`; the 62-test fumbles/P0/normalizer/reader selection passes locally. New remote CI `42410646529`, Stable `42410655322`, Intrinsic diagnostics `42410646636`, Forecast trace `42410646627` and PR164 `42410646540` run against that head. The superseded head's review threads have been addressed and resolved; fresh automated review is pending. No deployment at this checkpoint. Do not merge using an older run. Before deployment, prior live commit is `6d1259e1f5f55078398814a6c2383f7a0d544b84`, deployment `dep-dbk1lni9lscs73fk2khg`. Predeployment 30-second samples from 20:00–20:14:30Z showed memory at most 291,717,120 B and CPU at most 0.0018769 against the unchanged limits; these are idle samples, not refresh peaks.

## Status and authority

User authorized finishing the local saved-roster correction, correcting GET-triggered Intrinsic computation, focused validation and preparation of a reviewable candidate. No deployment, provider/plan change, production mutation, migration or remote publication is included.

Repository: `jderhagopian-stack/fsffl-next`. Main fetched and verified unchanged at `1c757c99d4a54a59d36991f5121d2c949b555f42` before implementation. Local branch: `codex/reliability-candidate-20261107`, checkout `/workspace/fsffl-review`.

Executable commits:

- `6d6ca76b6a469ed672c4e270cc35416eb905b14a`: memory candidate from PR #489 head `d50c84e6cb176da6c4b703bd5300d10cfea4e1ed`, plus the saved-roster identity correction and regression.
- `aed01a60b8ae4f6f5463909a3cc2f12fa870c9eb`: Intrinsic reader scheduling correction and lifecycle regressions.

These local commits have not been pushed, merged into main, deployed, or validated by remote CI. Existing green PR #489 checks do not cover this candidate. The earlier `/workspace/fsffl-memory-review` correction remains preserved; this combined branch is the forward candidate.

## Changes and expected resource effect

### Bounded Career input preparation

The candidate carries PR #489's changes: avoid the unused full frozen-reference feature rebuild, avoid normalizing the entire waiver identity universe during roster-only P0 work, fingerprint full weekly/prior responses before retaining candidate rows, and preserve source chronology checks.

The added correction distinguishes identity validation from scoring candidates. Fresh catalog identity/status rows are retained for **all** saved-roster IDs, including frozen-reference players subsequently dropped from live rosters. P0 scoring/stat work remains restricted to out-of-reference candidates. This retains at most the additional saved-roster identity set; it does not reintroduce the waiver universe. No player is removed from canonical State or final coverage accounting.

The real-normalizer builder-boundary regression fails against original PR #489 and passes with the correction. Model/source/fallback policies are unchanged. The full historical fitting and dynamic numerical path still requires accepted private-input replay; frozen-reference parity alone does not prove every dynamic result.

### Intrinsic GET scheduling

Three readers now use the existing coordinator's `current()` path:

- `/api/value/intrinsic-shapley-v1`
- `/api/player-intelligence/{player_id}` — Current/3-Year Intrinsic lookup
- `/api/opportunities/value-disagreements`

They no longer call `request()` to start model work. Shapley and Value Disagreements also refuse the former synchronous-loader fallback when installed without a coordinator; they return refresh-required instead of executing a callable that may compute/acquire.

Cold Shapley/disagreement reads return HTTP 503 with `status=refresh_required`. Player Intelligence retains its useful overview and returns an explicit refresh-required Intrinsic component, with no indefinite poll. Existing queued/running jobs remain loading; failed jobs remain failed without a GET-driven retry. Startup-restored completed contracts retain identical response data.

When Career temporarily weakens Current ownership, reads preserve the existing guarded restore behavior. While the memory lane is occupied, Shapley/disagreement return 202. Player Intelligence uses the existing polling-compatible `running` component status plus `intrinsic_build_status=waiting_for_retained_contract`, while keeping the actual lifecycle status `completed`. After the lane is free, the completed durable contract is restored without a new calculation.

No new executor, queue, database adapter, persistence key, publication controller, unbounded cache, fit worker, or numerical formula is introduced. Expected resource benefit is removal of read-triggered Intrinsic submissions, not a measured full-refresh RSS reduction. Explicit connect/refresh remains the build owner.

**Scope limitation:** this does not make every Player Intelligence operation compute-free. Its separate Future Forecast cache resolution and on-demand history acquisition remain unchanged. These need their own ownership review before claiming globally read-only product GETs. This slice specifically removes Current Intrinsic/Shapley scheduling from the three readers.

## Validation

All runs used isolated fixtures/local persistence; no production refresh or data write occurred.

1. Targeted Intrinsic lifecycle, Player Intelligence, Career memory, materializer, normalizer and P0 selection: **127 passed**, 9.59s.
2. Browser/resource, Player Intelligence, presentation/continuity, client lifecycle and value-lens selection: **130 passed**, 16.83s. The browser child passed separately in 5.28s and reported **186,388,480 B (177.75 MiB)** peak RSS. It uses mocked model outputs and is not full Career memory acceptance.
3. After adding the third reader, Shapley/read-route and Intrinsic discovery selections: **20 passed**, 3.95s. Includes all three readers' cold, active, failed, startup-restored and released-contract behavior.
4. Sanitized accepted frozen-335 reference, bounded history/matrix and selected private-beta restart/epoch regressions: **16 passed, 45 deselected**, 94.29s. Shapley maximum absolute delta **0**; Career numeric maximum absolute delta **9.09e-13**, within the existing 1e-9 regression tolerance. This recomposes accepted retained numbers; it is not a fresh full research materializer replay.
5. The two new cold/synchronous-reader regressions were run with the original route sources restored temporarily: **both fail**; corrected sources were restored afterward. The dropped-frozen-reference regression was likewise demonstrated failing before/passing after the roster correction in the preceding review.
6. Changed Python sources parse successfully; `git diff --check` passes.

Test groups overlap; do not sum them into a distinct-test count. Existing Starlette/httpx deprecation and pandas downcasting warnings remain. Restricted sandbox execution hangs even a trivial FastAPI TestClient request; network permission was granted for local HTTP-dependent tests, which then passed. This is not a production latency finding.

Local runtime: Python 3.12.14, NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.8.0, SciPy 1.17.0, Pydantic 2.13.4, FastAPI 0.141.1, Starlette 1.6.0. This differs from the governed hosted NumPy/interpreter identity. Results are local regression evidence, not exact hosted-runtime acceptance. No full-suite run was repeated; remote exact-head focused and Stable gates remain before promotion.

## Remaining release work

1. Review the two local executable commits and their combined diff against current main. If updating existing PR #489, return it to draft before pushing changed code; do not treat its old CI as new-head acceptance. Keep route scheduling review separately understandable.
2. Provide the retained accepted private State, cutoff, provider responses and artifact/source manifest in a private replay environment. Current `/workspace/library-files`, `/workspace/shared` and `/workspace/scratch` contain no such package; no Library connector or credentials are available here. Do not substitute production refresh, fresh provider acquisition or invented inputs.
3. Replay the complete exact-input Current/P0/Foundation4/Career/3-Year/Position & Depth path with production writes redirected to isolated persistence and provider acquisition disabled. Measure per-stage CPU, elapsed time, current/peak RSS and serialization/presentation allocation; reconcile every player, exception, source fingerprint and output component. Preserve last-good on failure.
4. Resolve the previously documented deployment recipe/dependency inconsistencies in a separate bounded change. This candidate deliberately does not apply Blueprint settings or modify historic accepted dependency evidence.
5. Run exact-head CI/Stable and independent review when ready. A full-refresh memory result and targeted authenticated hosted acceptance remain required before declaring the beta incident resolved. Any worker/service/cost choice follows measured evidence and a concrete separately reviewed proposal.

## Handoff

Local code preparation and focused validation are complete. Continue from `aed01a60b8ae4f6f5463909a3cc2f12fa870c9eb` and this record. Do not restart the audit, discard the local branch, infer production acceptance from the synthetic browser peak, or start another uncontrolled phone refresh. The immediate full-replay blocker is unavailable private accepted input bytes.
