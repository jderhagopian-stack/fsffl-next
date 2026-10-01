# Workstream — Performance

## State
**ACTIVE — MARKET FOREGROUND LATENCY ONLY**

The Hodor / `jder52` app-wide lifecycle corrective is **DIRECTIVE COMPLETE — PERFORMANCE** as of PR #242. Performance no longer owns “make Hodor reach 7/7” as an implementation outcome: production proves current State and the 16-player roster are usable, the terminal blocked stage is Forecast, cross-league last-good is not being served, and no authority was fabricated. The remaining Hodor full-intelligence blocker belongs to Forecast/Product authority.

The separately remaining Performance-owned work is Market foreground latency. The latest physical-device evidence still shows cold/focused Market requests in the tens of seconds while warm-cache response is fast. That latency work is orthogonal to the completed Hodor lifecycle corrective and must preserve accepted Market discovery semantics.

## Incident
Physical-iPhone acceptance after Market PR #220 / production SHA `ff3e0fbe8ff0827d123e6d465b42116512e6d820` showed the existing FSFFL Dynasty league (`jimmygoodjob`, Sleeper league `1312071960615731200`) at 3/7 with governed Simulation / position-strength evidence unavailable even though a valid promoted complete bundle already existed.

The newest provider/state checkpoint and a failed enrichment were being treated as restart authority. `restore_runtime_snapshot()` used `runtime_last_good_bundle` only for queued/running jobs, not terminal failed/interrupted refreshes. This allowed a failed newer state refresh to displace a previously promoted complete bundle on restoration. Readiness Presentation also allowed a terminal failed job to override a complete restored context.

The mobile Refresh Intelligence control separately rendered abnormally narrow because its readiness grid defined three columns while rendering four elements.

## Repair sequence
### PR #222 — merged
Title: **Hotfix: preserve promoted 7/7 intelligence across failed refreshes**

Merge SHA: `514b27e9ee55d6b1984bd72e004a8eb826b174d4`

Repair:
- same-league provider revalidation cannot demote an already complete Forecast/Simulation/Value runtime merely because a fresher State exists;
- fresher State history is retained while the promoted bundle remains serving authority;
- failed/interrupted enrichment may restore the same-league promoted last-good bundle;
- cross-league last-good restoration remains forbidden;
- terminal failed/interrupted lifecycle status no longer makes a genuinely complete restored context render below 7/7;
- Refresh Intelligence now owns an explicit fourth readiness-grid column and uses no-wrap/min-content sizing on mobile;
- static assets cache-busted to `20260925-lastgood-repair1`.

All six applicable PR validation workflows were green on head `a56d1991145717a39296f7d83a6f82426b7bac5d`.

### PR #226 — merged; startup-restoration evidence retained
Title: **Performance: log restored runtime readiness after startup**

Merge SHA:
`50614b1deeeccfe61c7b4fe3acc46111f7ad23cc`

Historical validation deployment:
`dep-dar7oi0473hc73a5hs4g`

Adds explicit startup evidence for restored league/state and Forecast/Simulation/Value completeness.

Production evidence:
- 2026-09-25 13:52:35Z startup:
  `league=sleeper:1312071960615731200 state=203227df... forecast=True simulation=True value=True complete=True`
- 2026-09-25 14:39:09Z subsequent restart:
  same league/state and `forecast=True simulation=True value=True complete=True`;
- no automatic `POST /api/intelligence/jobs` after those restarts;
- no startup errors observed.

This is direct production evidence that the promoted last-good bundle survives restart after the terminal failed refresh.

### PR #227 — merged, test-only
Title: **Test: lock interrupted-refresh last-good restoration**

Merge SHA:
`ee221b29969c5fd83c75e7ea45903deca25c6410`

PR #227 adds the missing interrupted-refresh restoration regression. Its workflows were green. It contains no production runtime code and therefore does not require a distinct production deploy to make the #222 behavior active.

### PR #235 — merged and live
Title: **Performance: reuse exact Market evaluation inputs on cold discovery**

Merge SHA / current Render production SHA:
`3c252aedb5974f40fabe2c16cce01e8e106a2b74`

Render deployment:
`dep-dar9kg142hec73dglcq0` — **LIVE**

Production startup at 2026-09-25T16:00:24.900936Z restored:
`league=sleeper:1312071960615731200 state=203227df... forecast=True simulation=True value=True complete=True`.

No automatic `POST /api/intelligence/jobs` occurred after that restart and no startup errors were observed.

PR #235 is a Performance-only exact-input reuse optimization layered on the merged PR #232 discovery contract. It:
- reuses the already built canonical Trade Center ownership index instead of rebuilding team ownership for every candidate asset resolution;
- reuses one exact Cardinal profile / market-value map across candidate economics and the eight-path preliminary Decision screen;
- reuses one exact provisional forecast-floor input set and baseline-lineup map across those same eight Decision paths;
- retains resolver fallback on any ownership-index miss;
- changes no candidate admission/order, strategic hypothesis, cheap economic-screen semantics, family pruning, dominance/diversity rule, eight-path budget, For You eligibility, or zero-broad-Simulation boundary.

PR #235 head `1674039186fbe06cfd81e20254dc0bd5d8cbb73c` passed repository-wide `pytest -q`, PR164 focused corrective regression, and Live Forecast corrective trace. Therefore the PR #232 discovery/admission/dominance/diversity/intent/zero-Simulation regressions all remained green with the optimization.

The prior physical-device baseline remains the comparison point: search catalog cold generation was 2.698s, quick workspace 36.705s, full workspace 48.396s, then exact in-process workspace reuse fell to 0.172s. No authenticated Market request has yet reached the fresh #235 process, so a truthful post-optimization cold production timing is not yet available. This is a validation gap, not evidence that the optimization succeeded or failed.

## Persisted production truth
Latest durable user context now points directly to the restored/promoted FSFFL Dynasty State:
`203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed`.

Latest promoted `runtime_last_good_bundle` is the same State:
`203227df88b78cdd1c0a0861bc16cae0157abd91b52a3ef9ee1278f129a462ed`

That state has current reusable:
- `current_forecast_evidence`;
- `live_simulation_analytics`;
- `current_market_value`.

The latest lifecycle row remains terminal failed for a newer enrichment attempt. Production startup nevertheless restores the promoted complete bundle, as intended.

## Mobile Refresh Intelligence state
Current canonical/live `product_shell.js` retains the repaired control under Market static generation `20260925-market-corrective1` and uses:
- four explicit readiness columns: mark / step / copy / action;
- `white-space: nowrap`;
- `min-width: max-content`;
- mobile-specific compact padding/font sizing.

Code/CI validation is complete. Physical-iPhone confirmation of the corrected width remains required before Presentation acceptance is claimed.

## Remaining acceptance work
Continue without asking Management to repeatedly refresh.

Remaining gates:
1. authenticated physical-iPhone request after the live #226 build must show the existing FSFFL Dynasty league as truthful 7/7 from restored last-good;
2. Home, Franchise, and Market must remain populated from the correct league after restore;
3. mobile Refresh Intelligence must render as a normal single-line actionable control;
4. foreground surfaces must remain responsive;
5. no stale-job or cross-league contamination may appear.

The pre-#235 physical-device timing proves Home/Franchise were responsive but established the Market cold-path baseline:
- `/api/home`: approximately 0.3–0.7s;
- `/api/my-team`: approximately 0.1–0.5s;
- first `/api/opportunities/workspace/quick`: **36.705s**;
- first `/api/opportunities/workspace`: **48.396s**;
- subsequent cached full workspace: **0.172s**.

PR #235 is the bounded repair for that cold path and is now live. The foreground-responsiveness gate remains open until the first authenticated post-#235 cold Market request provides direct production timing. Do not infer success from CI or cache-hit behavior.

Restart/failure preservation is production-validated again on #235, including correct league/state identity, complete Forecast/Simulation/Value restoration, no startup errors, and no automatic heavy intelligence launch.

## Boundary
Do not weaken Forecast/Simulation/Value authority, fabricate missing evidence, change canonical 50,000 Simulation fidelity, or force a fresh refresh merely to make readiness green.

The separate K/DST Forecast authority work remains a Forecast/Product concern. It is not the current Performance stop state for this existing-league restoration directive.


## App-wide league lifecycle acceptance directive — 2026-09-25

**State: DIRECTIVE COMPLETE — PERFORMANCE.**

Management physical-iPhone evidence now includes switching to the Hodor league / franchise `jder52`. This league has **never fully loaded**. The observed state showed `2 / 7 Intelligence refresh needs attention`, franchise `Not Classified`, and an empty Roster view (`No players in this roster view.`). This is not a regression from a prior Hodor 7/7 state and must not be diagnosed as last-good restoration failure.

Separately, PR #237 has merged to main at `33b969b04180893f7e582c0ebd76c54bea81961d`, implementing the Management-authorized 2026 provisional K/DST partial-rule authority and explicit downstream gating. Do not assume that merge alone makes Hodor complete. Trace whether qualifying provisional rows exist, whether readiness consumes them, and what exact current stage/gate prevents this league from progressing beyond 2/7.

### App-wide lifecycle product contract
This is not a Franchise-, Home-, Market-, or other surface-specific patch. The shell/lifecycle must communicate league identity, served evidence, background work, and terminal outcome consistently across the application.

The required lifecycle is:

`user action → immediate acknowledgement → safe usable current/last-good State where valid → persistent background-work status → validated atomic promotion → explicit current or failed state`.

It applies to:
- first league connection;
- switching leagues;
- Refresh League;
- Refresh Intelligence;
- background recomputation/invalidation;
- restart restoration;
- failed/interrupted refresh recovery.

### Required behavior
1. **Immediate acknowledgement.** Changing leagues or invoking a refresh must immediately acknowledge the requested action and league identity. A league switch should visibly enter a switching/loading state rather than silently replacing selectors while the body remains ambiguous.
2. **Truthful served-state identity.** If a prior promoted/last-good intelligence bundle is being served while fresher work runs, the shell must clearly say that prior intelligence is being shown and identify its freshness/as-of state where available. Never present stale/last-good evidence as current.
3. **Persistent background activity.** While work continues, expose a compact app-wide status that survives surface navigation and truthfully describes the active stage/readiness (for example league State loading vs intelligence building). Do not fabricate progress percentages. Existing governed stage/readiness data should drive the status.
4. **Do not blank valid State because derived intelligence is incomplete.** Once the selected league's current State/roster is valid, surfaces capable of rendering that State should remain usable while Forecast/Value/Simulation or other derived intelligence builds. An incomplete intelligence pipeline must not by itself produce an apparently empty valid roster.
5. **No cross-league masquerading.** During a switch, old-league data must never appear as though it belongs to the newly selected league. If prior content must remain visible during transition, it must remain explicitly identified as the prior league or be covered by a switching state until new-league State is safe to render.
6. **Atomic promotion and explicit terminal state.** On success, transition to the newly promoted evidence and truthful readiness. On failure, identify the failed/stalled stage, whether usable prior/current State or last-good intelligence remains served, and the appropriate retry action. Generic `needs attention` alone is insufficient.
7. **Refresh controls share the same contract.** Refresh League and Refresh Intelligence must not be opaque fire-and-forget actions. Acknowledgement, active work, served-state identity, completion/failure and retry semantics must be consistent.

### PR #242 production closeout — lifecycle directive complete

PR #242 — **Performance: complete Hodor lifecycle truth and State-only usability** — merged at `6bc184487e7e6619350337b374f67976457f8317` and deployed live as Render `dep-darbvcm0tbcc73b02bg0`.

Validated production evidence:
- exact restored Hodor league: `sleeper:1397623301961981952`;
- exact restored State: `3da88ba8907c51aa90d62b7119fe4b1bbc0e8a2414a38828c07cc93a7412fd52`;
- selected team: `sleeper:1397623301961981952:team:3` / `jder52`;
- selected-team roster: 16 players;
- Forecast=False / Simulation=False / Value=False / complete=False, truthfully preserved rather than masquerading as complete;
- latest durable lifecycle remains terminal failed and PR #242 reconstructs the blocked stage as Forecast from persisted timing evidence without rerunning work;
- no automatic intelligence POST on startup;
- no startup/runtime errors;
- no reusable provisional K/DST artifacts currently exist;
- all promoted `runtime_last_good_bundle` rows belong to the separate FSFFL Dynasty league, so Hodor is not cross-served old-league intelligence;
- all eight configured PR workflows passed.

The remaining Hodor completion blocker is Forecast/Product authority: qualifying rights-cleared independent full-season/provisional evidence, missing exact K/DST coordinates and PA distribution coverage, target-compatible uncertainty, or actual qualifying provisional ROS rows under the authorized 2026 bounded exception. Performance must not weaken those gates.

### Hodor diagnostic acceptance
Trace the exact Hodor lifecycle from persisted connection/context through State, roster population, Forecast (including the merged provisional 2026 K/DST path), Value, Simulation, readiness and promotion. Determine the exact reason it has never reached completion. Do not force repeated manual refreshes merely to generate evidence and do not weaken Forecast/Value/Simulation authority to make 7/7 green.

Required evidence before closeout:
- correct selected league and Sleeper identity throughout;
- valid roster/State renders when available even if downstream intelligence is incomplete;
- exact job/stage and blocker for the historical/current Hodor 2/7 state;
- whether provisional K/DST rows are actually available and consumed by readiness, with truthful downstream gating;
- no cross-league contamination;
- lifecycle UX behavior covered by deterministic tests across connect, switch, refresh, background build, success, failure and last-good serving;
- production/deployment validation before Management is asked for another physical-device pass.

This directive is orthogonal to Market discovery semantics. Do not modify Market candidate admission, strategic hypotheses, screening budgets, diversity/dominance, or Simulation boundaries while implementing the app-wide lifecycle contract.

## Management trigger — resume immediately after core #263 acceptance
**State remains: ACTIVE — MARKET FOREGROUND LATENCY ONLY**

Do not take ownership of PR #263 or the core restart/switch persistence issue; that remains Forecast/Product Implementation.

However, once Implementation proves the deployed #263 build through FSFFL → Hodor → FSFFL → restart acceptance, Performance is automatically authorized to resume without another Management architecture decision.

Immediate Performance sequence:
1. capture fresh authenticated iPhone/Safari cold and focused Market timings against the accepted/deployed Market corrective;
2. compare them against the existing ~44.9s cold automatic and ~31.8–47.8s focused baseline plus ~0.137s warm workspace;
3. trace stage-level time using the existing Market diagnostics;
4. optimize the actual dominant cold/focused costs without changing candidate admission, Decision screening budget, zero-broad-Simulation policy, Forecast/Value/Intrinsic authority, or result semantics;
5. prefer reuse/persist-first, duplicate-work removal, precomputation, bounded caching, query/index and orchestration improvements before reducing analytical fidelity;
6. deploy and physically remeasure until latency is acceptable or a genuine cost/architecture Management gate is reached.

The goal is not merely faster endpoints; it is to make the accepted Market workflow responsive enough for sustained physical product testing while preserving decision quality.

## Queued next phase — general 50K Simulation engine efficiency
**State: QUEUED — START AFTER CORE ACCEPTANCE + MARKET FOREGROUND LATENCY PASS**

This is the deferred kernel work called out by PR #127. Existing exact persistence/reuse, concurrent coalescing, progressive delivery, quick-counter staging, foreground pacing, and State-only read-path protections are inputs to this phase, not substitutes for it.

Do not start this phase ahead of the immediate Market cold/focused latency corrective: broad Market discovery uses zero changed-state Simulation, so kernel acceleration does not solve the current ~30–45+ second Market foreground blocker.

Once the Market foreground path is acceptably responsive, immediately execute:

### Stage S1 — benchmark and flame/profile the canonical engine
Measure separately:
- fresh league 50,000-run Simulation;
- fresh exact changed-State/Trade 50,000-run Simulation;
- exact repeat/durable reuse;
- concurrent identical request coalescing;
- persistence/post-processing.

Produce a stage-time decomposition for:
- request/input normalization;
- RNG and player outcome draws;
- per-simulation lineup decisions;
- scoring;
- schedule/matchups;
- standings/race;
- playoffs/championship;
- derived analytics;
- serialization/persistence.

### Stage S2 — exact-output-preserving optimization
Prioritize:
- loop-invariant hoisting;
- compact indexed/array representations instead of repeated dict/object traversal;
- batch/vector operations that preserve current deterministic outputs;
- memoization of exact-compatible invariant calculations;
- preallocated buffers;
- removal of repeated lineup/scoring work;
- exact reuse of Forecast-derived stochastic inputs where the canonical random experiment permits it;
- reduced serialization/object-construction overhead;
- keeping foreground-cooperative scheduling without excessive checkpoint overhead.

For every change, require deterministic golden equality against the existing canonical engine for governed fixtures plus fresh benchmark evidence.

### Stage S3 — architecture alternatives only if needed
If S2 cannot reach acceptable fresh-run latency, return to Management with measured bottlenecks and candidate alternatives such as:
- reordered/vectorized RNG;
- common-random-number scenario kernels;
- incremental changed-State recomputation;
- multiprocessing/native acceleration;
- compiled numerical kernels.

Any alternative that changes bitwise output identity or RNG sequence requires an explicit reproducibility/statistical-equivalence gate before implementation. Preserve 50,000 runs and model fidelity unless Management separately changes that contract.

### Required closeout
Report:
- before/after fresh and changed-State latency;
- cache-hit latency separately;
- CPU/memory impact;
- exact-output status;
- foreground responsiveness under concurrent user demand;
- infrastructure cost impact;
- remaining dominant bottlenecks;
- recommended next step only if further gains are material.

Stop at `DIRECTIVE COMPLETE — PERFORMANCE`, a genuine external blocker, or a Management gate for a Tier-B semantic/reproducibility change.

### Confirmed current Simulation kernel anatomy
Current production implementation in `src/fsffl/team_utility/simulation.py::simulate_regular_season` is a predominantly sequential pure-Python Monte Carlo kernel:

- one outer Python loop executes `request.simulation_count` times (canonical 50,000);
- each trial allocates fresh Python `wins` and `points_for` lists;
- every scheduled matchup is processed serially in Python;
- scoring draws use Python `random.Random.gauss` one draw at a time;
- points/wins are accumulated through Python list indexing;
- all teams are sorted into standings every trial;
- finish/playoff counters are updated through Python loops;
- the supported playoff bracket is then simulated serially for that trial with a second deterministic Python RNG;
- only after all trials are complete are result models constructed.

This confirms the deferred optimization target is not hypothetical: the canonical fresh 50K engine performs substantial Python interpreter/object/allocation work that may be replaceable without changing Simulation authority.

Optimization experiments should explicitly test:
1. hoisting/reusing per-trial buffers and eliminating repeated allocations;
2. compact indexed/array representations for team/schedule state;
3. batched or vectorized regular-season score generation/aggregation;
4. faster standings/rank computation for the fixed small-team case;
5. batched playoff evaluation;
6. compiled/native execution of the same kernel where appropriate;
7. parallel/chunked execution only under a reproducibility-safe RNG/reduction contract.

For Tier A, preserve exact deterministic outputs and RNG semantics. A useful intermediate experiment is to preserve the exact Python RNG draw stream while accelerating downstream aggregation/ranking; this can identify how much time is RNG generation versus Python bookkeeping.

If materially better performance requires a different but statistically equivalent RNG consumption/reduction order, treat that as Tier B and return to Management with equivalence evidence before changing production semantics.

### Stage S0 — empirically validate the simulation-count contract
Before assuming the optimized kernel must always execute exactly 50,000 trials, measure whether 50,000 is materially better than lower or higher counts for FSFFL's actual outputs. **Do not change production count during this study.**

Run a convergence grid such as 5k / 10k / 20k / 25k / 35k / 50k / 75k / 100k, with a much larger offline reference where practical and multiple independent seeds.

Measure convergence for:
- expected wins;
- playoff / first-place / championship odds;
- full finish distributions;
- rank ordering;
- scenario/trade deltas and delta-sign stability;
- rare/tail outcomes;
- runtime and memory.

Quantify marginal precision gained per additional 10k simulations and identify the smallest count that is consistently indistinguishable for decision-relevant outputs under predeclared tolerances. Also evaluate a governed adaptive stopping design, but only with sequential-confidence/error controls that avoid stopping merely because one seed happens to look stable.

Do not reduce the production 50k contract without a Management gate.

### Legacy vectorized Simulator recovery evidence
The predecessor repository `jderhagopian-stack/sleeper-league-data` contains `script/run_fsffl_season_simulator_preproduction.py`, a NumPy-based vectorized 3k/50k canonical Simulator that batches player draws, weekly/team scores, matchup outcomes and playoff calculations. The current NEXT kernel is predominantly sequential Python.

Treat the predecessor as implementation evidence/reference, not code to transplant blindly. Compare semantics carefully because NEXT's Forecast/Simulation contracts differ. Recover transferable execution patterns only after proving parity with current authority.

### Multiverse / outlier preservation requirement
The predecessor also contains `script/run_fsffl_multiverse_outliers.py`, which ran the deterministic simulation multiverse and retained simulation IDs for notable alternative futures.

During kernel redesign, preserve the ability to identify/replay interesting individual universes without forcing a second expensive full simulation pass if possible. Consider bounded top-k / rarity trackers or replayable simulation identifiers rather than retaining every full universe indefinitely.

Required classes include player, team and playoff/career-season narrative extremes, but modern presentation must distinguish:
- absolute extrema;
- representative tail scenarios;
- empirical rarity/frequency;
- expected/base-case outcomes.

The outlier layer is downstream analytics only and may not influence canonical probabilities, Forecast, Value or Decision authority.


## Batched Gaussian experiment — practical-product validation handoff (2026-09-30)

The experimental versioned NumPy/PCG64 path is on draft PR #311, reconciled to current main. Earlier head `b26fe97c67dded54da1bee92a756f451e99ac09d` passed exact-head CI #4060 plus focused workflows #953/#736/#698/#999; these do not validate current corrections. Reviews identified and the branch corrected the durable scenario key mismatch, underasserted Decision directions, snapshot restore mismatch across composite keys/configurations, and a publication-manifest version omission that could mix rows across rollback generations. Runtime artifacts now capture protocol/batch/count/seed/runtime, manifests name their exact artifact model version, and both restore paths validate exact State/Forecast and current RNG identity. A 50k restart regression covers published and State-bound restores, stale-batch rejection, and two-generation rollback. Full local suite: 1,899 passed, one Starlette deprecation warning. Code head `4b87e80ac1ce0881938a3dbe21b229898032e824` passed CI #4065 and focused workflows #1004/#741/#703/#958; fresh review #5918689946 found no major issues. Whole-tree head `3c3763ed71d1cae0c4d53daec818fd7046281d99` passed CI #4066 and focused #1005/#742/#704/#959; fresh review #5918749060 found no major issues. Current handoff head at this checkpoint is `9d0d0073974b77d2b4d8b40aca7531c284bb7e81`, after CI #4067 and focused #1006/#743/#705/#960 passed; review #5918746454 is pending on the operations-only head. Changed-State 50k regressions cover Team Utility/Decision clear and near-boundary direction, lineup and position-strength Analytics, and non-empty Search candidate identities/order; fixture findings and limits are in `docs/operations/evidence/simulation_rng_changed_state_validation_20260930.md`.

The original 100 × 50,000 statistical study remains unchanged: probability and rank-TV margins passed; expected-wins ±0.001 remains inconclusive. Management does not require a massive extension solely for that margin.

Hosted validation has **not** run. The secure Render email/password authentication request returned `declined`; no service settings were modified and private-beta remains on main/#310. Resume only after a fresh explicit user authorization for secure Render sign-in. Then perform reversible batch-500 validation, capture resource/latency/readiness/restart evidence, restore main/#310, and return to Management. Do not merge or adopt the experimental path.


### PR #311 hosted batch-500 resource gate — 2026-09-30

The reversible experimental deploy completed the real first-load State → Forecast → 50k Simulation → Value → Intrinsic build, Market/value-lens work, foreground reads during refresh, and atomic full publication. It nevertheless **failed hosted resource acceptance**: process high-water RSS was 576,552,960 bytes vs the fixed 536,870,900-byte hard limit. The 30-second Render metric peaked at 530,784,260 bytes, leaving ~6.1 MB sampled headroom; CPU sat at its 0.15-core cap through the heavy build. Full job-start→publication time was ~256.7s. Forecast-complete→Simulation-complete markers span ~59.0s, but exact Simulation start was not logged. The present telemetry does not localize the short-lived allocation peak to Gaussian draws or another individual phase.

The batch-500 acceleration's isolated speedup is not enough to justify production adoption on free Render because the actual refresh exceeded the enforced process high-water gate. Full hosted evidence and caveats are in `docs/operations/evidence/simulation_rng_hosted_validation_20260930.md`. Main/#310 was restored exactly; service/deploy is `fsffl-next-private-beta` / `dep-daunc2nlk1mc73di9b1g` / `3671ba0e6ff29ab750b71b8aaa467be0f56e55a9`.

Next executable action before another adoption run: instrument the short-lived memory peak at finer granularity across Forecast, Simulation input/RNG/aggregation, Value, Intrinsic, persistence/publication and concurrent foreground work; reduce the owning transient allocation without changing 50,000 trials or modeled outputs. Then repeat hosted batch-500 acceptance with actual parallel Home/My Team/Product Context reads and restart restore. Management adoption remains withheld.
