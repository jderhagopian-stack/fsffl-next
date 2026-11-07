# Local reliability release candidate — 2026-11-07

## Subsequent authorization — controlled existing-service deployment

The user challenged withholding deployment because hosted testing is necessary. The execution direction is now to advance this candidate through exact-head CI/review and deploy it to the existing Render service, then observe one controlled authenticated refresh. The unavailable private replay package is no longer an absolute predeployment prerequisite. Preserve the existing 0.5 CPU/512 MiB service, hard guard, model/source rules, cohort coverage, atomic publication and last-good; stop and diagnose if the single run fails rather than repeating it. No plan/provider/storage migration or new worker is authorized.

PR #489 was returned to draft before updating its head. Its history is being reconciled by a normal merge (retaining the tested saved-roster correction) so the existing PR branch can advance without force-pushing or opening a competing memory PR. Historical statements below describe the preceding local-only checkpoint.

Current Render deploy/health documentation could not be fetched as either Markdown or HTML (network proxy HTTP 403). Use the connected deployment API and observe actual live state/health; do not infer unverified platform timeout thresholds from memory. No Blueprint or health-check configuration change is required for this existing-service deployment.

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
