# 2026-09-29 — Runtime architecture audit corrective

## Management disposition

Independent read-only architecture review confirms that the founding analytical architecture remains sound. Recent failures are primarily **runtime/application architecture drift plus implementation defects inside that drift**, not a failure of the Data -> State -> Forecast -> Value -> Decision -> Search -> Analytics/API -> Presentation authority chain.

This corrective is now part of the runtime stabilization gate.

Do not broaden into Forecast/Simulation/Value/Decision semantics, Simulation 2.0, Long-Term Intrinsic, Market expansion, or a broad persistence rewrite.

## Founding invariant to restore

**Valid canonical State must be usable without durable restore/persistence being a prerequisite.**

Plain language:
- opening a valid league should not require recovering old saved work first;
- saving/restoring old work is for continuity and restart recovery, not permission to use current State;
- managed-team identity must be established before team-dependent intelligence begins;
- completed intelligence publishes as one coherent generation;
- background/recovery work may fail without invalidating otherwise valid State.

## Confirmed audit finding

On the reviewed current-main lineage, a cold foreground runtime read can still invoke durable restore before fresh Connect activation:

- persistent runtime `get()` can call lazy `_restore_once()` when no State is present in memory;
- that restore performs durable snapshot I/O while holding the per-user lifecycle operation;
- `activate_league_state_for_connect()` uses the same per-user lifecycle operation;
- hosted Connect can call runtime `get()` before queuing the background import.

Therefore a cold restore can still delay the request that is intended to begin fresh State activation.

This is a confirmed code-path **P1 availability exposure**. It was not proven as the cause of the latest successful #292 primary-FSFFL hosted leg, but stabilization may not close while the architecture still permits persistence recovery to sit in front of fresh Connect.

## Current implementation lineage

- PR #292 merged as `8c162c5a7bf6120ecc72566e72dd11f634a93ee9` and materially restored State-first first-load behavior.
- #292 hosted acceptance proved coherent primary-FSFFL initial publication, responsive PI overlap, last-good continuity during rebuild, coherent changed-State promotion, and acceptable memory.
- #292 full acceptance stopped at Hodor because only one live Forecast source was healthy.
- PR #293 (`Recover Hodor raw Forecast replay after clean runtime reset`) has since merged as `49ce8cae4f588fefc7c879e643504ee1b015cf42` and is live. Hosted acceptance is currently running on that exact lineage.
- PR #293's review also raised a P2: replay discovery must continue past newer **incompatible** raw artifacts to find an older raw-compatible artifact rather than stopping discovery at the first raw artifact. Do not ignore that review finding merely because #293 merged.

## Required corrective architecture

Keep:
- canonical provider-neutral State;
- strict Forecast source-health authority;
- exact Forecast/Simulation/Value dependency identities;
- atomic working -> published generation;
- per-user lifecycle sequencing;
- managed-team identity checks;
- fail-closed behavior on incompatible persisted evidence;
- truthful partial authority.

Correct:
1. **Foreground `get()` becomes an in-memory published read.**
   - It must not synchronously perform durable restore on the fresh Connect critical path.
2. **Durable restore becomes explicit orchestration.**
   - Perform it outside fresh State activation's critical section.
   - Install restored data only if the captured league/runtime identity is still current when restore completes.
3. **Cold Connect activates imported State first.**
   - Once valid canonical State is loaded, expose it.
   - Checkpoint State asynchronously.
   - Do not wait for old durable intelligence recovery before State becomes usable.
4. **Managed team precedes team-dependent intelligence.**
   - Preserve #292 generation-aware replacement behavior.
5. **Raw Forecast replay discovery is compatibility-aware while scanning.**
   - Newer incompatible raw artifacts must not prevent discovery of an older compatible governed raw artifact.
   - Replay only exact raw-compatible evidence; otherwise acquire fresh and preserve source-health rules.

## Deterministic proof required before stabilization closes

A. Cold restore vs fresh Connect
- no State in memory;
- durable prior runtime/published evidence exists;
- fresh Connect begins while restore would otherwise be eligible;
- fresh canonical State becomes usable without waiting for durable restore;
- late restore cannot overwrite/rebind the newly selected league/team;
- no deadlock or starvation.

B. True fresh first-run
- empty server runtime pointer and empty browser-local league/team state;
- immediate Connect acknowledgement;
- explicit managed-team selection;
- State-only usability before enrichment;
- coherent eventual publication or explicit terminal failure.

C. Restored session
- valid saved session restores quickly;
- restore remains a continuity optimization, not a requirement for correctness.

D. League switch and replay
- FSFFL -> Hodor -> FSFFL;
- raw replay scans past incompatible candidates;
- compatible governed evidence replays;
- genuinely incompatible evidence fails closed to live acquisition;
- no cross-league/team contamination.

E. Restart
- only the last actually published coherent generation is restart authority;
- State-only/current-session activation is not confused with published intelligence authority.

## Acceptance sequence

Do not interrupt the currently running #293 hosted acceptance unless it reveals a concrete failure.

After that run:
1. reconcile its exact evidence;
2. address any still-open replay P2;
3. implement the cold-restore/fresh-Connect boundary above;
4. focused deterministic regressions A-E;
5. full CI;
6. bounded read-only P1/P2 red-team of the runtime lifecycle;
7. one exact-SHA deploy;
8. complete hosted clean-first-run/restored-session/FSFFL -> Hodor -> FSFFL/restart acceptance;
9. only then request physical iPhone/Safari validation.

## Terminal condition

Runtime stabilization closes only when:
- persistence recovery is no longer on the fresh Connect critical path;
- Hodor replay/acquisition behavior is authority-correct;
- full hosted lifecycle acceptance passes;
- physical Safari confirms the real user journey.

No claim of "one last fix" or terminal readiness before those gates are actually exercised.
