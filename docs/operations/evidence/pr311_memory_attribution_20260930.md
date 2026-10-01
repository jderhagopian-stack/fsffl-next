# PR #311 — hosted memory attribution and bounded history fix

Date: 2026-09-30 (UTC)

## Attribution result

The hosted 50,000-trial Simulation itself was not the source of the large transient high-water allocation in the diagnostic journey. On Render instance `dr292`, the first clean 50k build completed publication with process high-water RSS of 361,902,080 bytes. Simulation attachment, lineup compilation, weekly scoring, and the 50k kernel/result aggregation did not increase that high-water mark. Their sampled peaks were at most 349,007,872 bytes. The selected Forecast-to-Simulation object graph was 1,262,216 shallow bytes / 10,035 nodes.

A later repeated state transition entered `forecast.raw_replay_history_discovery` at 18:27:32 EDT (22:27:32Z). This phase lasted 83.494 seconds. RSS increased from 330,878,976 to a sampled 572,669,952 bytes; process high-water grew from 340,566,016 to 571,768,832 bytes (+231,202,816). RSS after the phase was 481,435,648 bytes. Render then reported the instance exceeded its 512 MB guard and terminated it. The adjacent compatibility check and later provider / ensemble / Simulation phases did not add to the recorded high-water.

The implicated path was the persisted PIT State fallback used when no exact State-bound raw Forecast artifact was found. The production Postgres `recent_at_or_before()` query fetched up to 32 complete JSONB State payloads with `fetchall()`, decoded every payload into a `LeagueState`, retained the States in a tuple, and only then did replay discovery inspect candidate raw Forecast artifacts one at a time. Historical States carry player and player-week object graphs; the payload mappings and validated model graphs therefore overlapped even though the consumer needs candidates sequentially.

This is a Forecast/history persistence-materialization owner, not a Forecast-to-Simulation or NumPy-kernel owner. The 231.2 MB high-water increment is phase-attributed; a per-State byte breakdown was not collected, so the precise contribution of JSON decoding versus Pydantic graph construction is not separately quantified.

## Corrective

`PostgresStateSnapshotStore.iter_recent_at_or_before()` first reads the bounded ordered list of State hashes, then fetches and validates one full payload at a time. Replay discovery consumes this iterator and drops each scan-local State after comparison. Candidate order, limit (32), PIT checks, identity validation, compatibility/fingerprint selection, first-incompatible fallback, and raw Forecast artifact validation remain unchanged. `recent_at_or_before()` and `latest_at_or_before()` retain their tuple/one-State contracts by consuming the same iterator. No State authority or Forecast, Simulation, Value, RNG, or downstream semantics changed.

Regression `test_postgres_state_history_streams_payloads_one_candidate_at_a_time` asserts that iterator creation reads no full State payload and each `next()` materializes exactly one payload, in the preexisting newest-first order. Existing Postgres history ordering/PIT tests and replay/restore suite remain green.

## Validation and hosted status

- Focused history + restore/replay tests after the corrective: 61 passed.
- Full repository suite before the final scan-local `del` cleanup: 1,902 passed, one existing Starlette deprecation warning. Focused tests were rerun after that cleanup and passed; full suite must be rerun at exact PR head.
- The 2026-09-30 diagnostic Render run reproduced the prior free-instance OOM guard. It is attribution evidence only, not an acceptance pass.
- No hosted validation of the corrective has run yet.
- Render service `fsffl-next-private-beta` is restored to branch `main`, commit `878a2a32d5826ff990eed76c4985ae9e8f39bba3`. The main deploy `dep-dauoq6c0ugqs738j1180` became live at 22:31:23Z. A follow-up main deploy `dep-dauouj49v7es73adle10` is applying temporary diagnostic/acceptance flags set to `0`; status must be confirmed before leaving the service.
- No merge or experimental RNG production adoption is authorized. The expected-wins ±0.001 study remains inconclusive as previously recorded.

## Exact handoff

- Base: current `main` `878a2a32d5826ff990eed76c4985ae9e8f39bba3`.
- PR #311 remote head at start of this corrective: `4408848e970c21093e54804d0cb40f7abb49fd3b`.
- Local diagnostic head before this corrective: `65d8e1d32d7aa5d6a5d5d5da111076853711ab0f`.
- Corrective source/tests are currently uncommitted in the isolated worktree `/tmp/fsffl-pr311-active` on `work/pr311-memory-attribution`; they must be committed on top of exact PR head, pushed to `work/simulation-modernization`, and receive exact-head CI plus fresh review.

Next executable action: rebase/apply the uncommitted four-file change onto `4408848e970c21093e54804d0cb40f7abb49fd3b`, run full CI and fresh review, then deploy that exact PR head to private beta for a reversible batch-500 50k run with genuinely concurrent Home, My Team, and Product Context reads, full Forecast/Simulation/Value/Intrinsic publication/readiness, exact RSS and high-water telemetry, and restart restoration. Roll back to current main after the hosted measurement. If memory still crosses 536,870,900 bytes, stop for a Management capacity decision.

## 2026-10-01 — Fresh review P2 and runtime-key corrective

The fresh review on `e5268054f49fd8743bc952a35b528a73d1462b2c` found that newly generated legacy Python Simulation artifacts retained a shared base model-version key across Python patch/runtime changes. Since checkpoint persistence precedes the publication manifest, a crash during a same-State upgrade could make the old manifest resolve the unpublished new runtime payload. The source-health numerical trace failure (#277 / run `36787098288`) is separately explained by only one successful independent provider (`razzball`) versus the two-provider live-health gate; it does not implicate the history iterator.

Correction in progress: new Python cache/artifact model versions now include protocol, batch, count, seed, and interpreter version; records marked `legacy-unrecorded` preserve a read-only lookup at the old base model version. A deterministic staged-write/restart regression reproduces the same-State manifest boundary at 50,000 trials. Local full validation: **1,903 passed** / one known Starlette warning; focused restore/cache 70 passed and exact identity assertions 2 passed. Exact-head CI and fresh review of the correction are pending. Secure Render email/password retry succeeded; the service remains unchanged on main, with profiler/acceptance flags off.

Next: publish code + operations handoff to PR #311, run exact CI/review, then reversible batch-500 hosted validation with actual concurrent Home/My Team/Product Context requests, full generation readiness/publication, exact RSS/high-water, restart restoration, and rollback to main. A high-water above 536,870,900 bytes is a Management capacity stop; no merge/adoption is authorized.

## 2026-10-01 — Review portability follow-up

On pushed candidate `b85f62f6d5f3bcbe570cf50ffbb907ee2556f37c`, fresh review found a P2 in `test_50000_run_production_output_remains_bit_identical`: the payload digest included patch-specific `rng_runtime_version`, but baselines were chosen by Python major/minor, and the test failed for supported future minors. The test-only fix normalizes that identity field to major.minor before hashing numerical outputs and remaining replay metadata. Existing 3.11/3.12 baselines remain; other supported minors require exact repeat replay. Focused 6 passed, full suite 1,903 passed (one existing warning). This candidate is not yet pushed or independently reviewed; Render remains untouched pending those gates.

Exact-head CI #4082 on `9d9c3e45fba165768ec67faf6b5dcaf953958756` then exposed that the Python 3.11 expected digest must be recalculated after normalizing the runtime identity. The deterministic CI-observed digest is `63660717b6f9d6cd71142fe16dd27c3146a8a24058c2a5c951ea08f32d4a76c2`; that baseline is now updated in the candidate. Focused simulation equivalence tests pass 6/6 on local Python 3.12, with clean `git diff --check`. CI/review must be repeated on the new exact head. Live-provider trace #279 succeeded while #278 previously failed the independent-source minimum with only Razzball, supporting the source-health classification. Render remains main and unchanged.

The fresh exact-head review on `70d75285bf97b56eae584392477b267457836ccb` reported P1 truncation in operations history and P2 weakness from a same-run digest fallback. The P2 fallback is removed; the regression accepts only fixed per-minor reviewed baselines (3.11/3.12 today). The P1 was accurate on the pushed file: local `CURRENT_STATE.md` was complete, but the prior GitHub blob transfer sourced a long shell response that had been truncated by the tool. The full file was rewritten from complete local source via bounded chunks and the GitHub blob SHA was verified against reconstructed content for all three operations files. A subsequent review found the unbounded Python metadata still claimed 3.13+ support without a fixed digest. Candidate metadata now restricts the tested runtime range to 3.11/3.12 (`>=3.11,<3.13`); no RNG or model semantics change. Exact-head CI/review required; Render remains unchanged.
