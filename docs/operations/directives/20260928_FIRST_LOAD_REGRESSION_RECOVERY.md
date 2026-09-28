# 2026-09-28 — First-load regression recovery

## Management decision

Treat the current private-beta startup/connect behavior as a **beta-availability regression**, not a new product-design problem.

The product had a previously reliable first-load contract. Restore that known-good behavior while preserving later atomic-publication and lifecycle-safety guarantees. Do not redesign Forecast, Simulation, Value, Intrinsic, Search, or market semantics.

## Confirmed regression evidence

Earlier working lineage:
- PR #54 merged as `0021aefc7c1477b0f26e30ff7810ab48e6fd2b21` specifically stopped partial persistence from blocking hosted Connect League. Its contract was: once canonical Sleeper State is usable in memory, Connect League may finish; large persistence work continues outside the user-facing connect path.
- PR #56 merged as `a8527e1580f48bfded7749d76e98f43c4f4e579e` made the hosted connect flow durable/single-flight and explicitly showed mobile Safari progress such as `Starting import…` and `Loading league…`.

Later regression:
- PR #261 merged as `c57bc394986ce871ceca672efaacb54f1346eed0` while fixing State-first persistence/switch safety. The current hosted connect path now calls `wait_for_checkpoint(..., timeout=30.0)` after `set_league_state()` and before declaring activation complete.
- That durability barrier was intended to protect lifecycle/switch correctness, but on first connect it recreates the user-facing blocking behavior PR #54 removed.

Physical clean-reset evidence on 2026-09-28:
- Server-side Jimmy runtime/presentation pointers and Sleeper sync cursor were deliberately cleared while historical/model evidence was preserved.
- The hidden hosted acceptance harness was disabled.
- The iPhone submitted the Sleeper ID at ~22:45:29Z; the POST was accepted with 200.
- The Connect League page gave no useful visible acknowledgement/progress and remained visible for more than a minute.
- A `/api/product-context` read took ~51.6 seconds during this flow.
- The fresh FSFFL State eventually persisted at ~22:47:52Z.
- The user was never asked to select a team, yet two `POST /api/select-team` calls occurred.
- Current mobile code can silently restore `fsffl:last-team` from Safari localStorage via `restoreSelectedTeam(...)`, so clearing only server state did not create a truly clean browser first-run.
- After league activation, Forecast replay correctly determined the old raw Forecast was incompatible because material player/NFL-team identity inputs changed and selected fresh acquisition.
- No new Forecast/Simulation/Value publication followed; the server later returned to near-idle without the product surfacing a clear terminal failure to the user.

## Required product contract

Restore the known-good first-load behavior:

1. **Immediate acknowledgement.** Submitting a Sleeper league ID must visibly acknowledge the action immediately in the browser (for example, disabled button + `Starting import…` / `Loading league…`). A long silent Connect League screen is a failure.
2. **League usability is not blocked on durable checkpoint completion.** Once canonical Sleeper State is valid and activated in memory for the requested league, the user may proceed. Persistence remains asynchronous. Do not weaken the stricter durability requirement for final published intelligence generations.
3. **Team selection must be truthful.**
   - A genuinely fresh browser/session must require an explicit managed-team choice.
   - A previously saved team may be restored only as an explicit session-restore behavior when the saved team is valid for the loaded league.
   - Do not silently treat stale browser-local state as a fresh choice.
4. **Separate connection from intelligence enrichment.** League connection/managed-team selection must become usable before Forecast/Simulation/Value/Intrinsic enrichment finishes. The enrichment may continue in the background.
5. **Visible enrichment state.** Once intelligence work begins, show clear stage/progress. If it fails or is interrupted, show an explicit terminal reason/action instead of leaving the product looking idle or indefinitely loading.
6. **Preserve atomic publication.** Working Forecast/Simulation/Value/Intrinsic must remain isolated from readers until a coherent generation is ready. The correction must not reintroduce half-published intelligence.
7. **Preserve lifecycle safety.** Do not broadly roll back PR #261 or #291. Remove the user-facing connect barrier while retaining switch-safe persistence ordering, per-user lifecycle serialization, restart authority, and final-generation durability.

## Required diagnosis

Before changing tests or code mechanically:
- compare current hosted connect/mobile flow against PR #54/#56;
- determine the narrowest safe way to make State activation user-visible without waiting for the durability queue;
- identify why the fresh intelligence job stopped after selecting `fresh_acquisition` and why no terminal failure was surfaced;
- identify the exact browser-local-state path that caused silent managed-team restoration and distinguish session restore from fresh connect.

## Acceptance matrix

Run this before asking the product owner to test again.

### A. True fresh first-run
Start with:
- no server runtime pointer/presentation pointer for the test user;
- no saved league/team browser-local state;
- no hidden acceptance workload.

Prove:
- submit league -> immediate visible acknowledgement;
- requested league becomes usable without waiting on a large persistence checkpoint;
- explicit team selection is presented;
- selected team is applied exactly once;
- Home/Franchise can render State-only while intelligence enriches;
- intelligence progress is visible;
- terminal success publishes one coherent generation, or terminal failure is explicitly surfaced.

### B. Restored session
With valid saved server + browser state:
- restore quickly;
- previously selected team may be restored automatically only when valid for that league;
- background revalidation must not blank the product.

### C. League switch
- switching leagues preserves PR #261/#291 safety;
- no old-team cross-league contamination;
- no blocking Connect League wait on final intelligence durability from the previous league;
- no stale worker may publish after the switch.

### D. Restart
- a final published generation remains restart authority;
- an in-progress State-only first connection may be recoverable without being mistaken for a published intelligence generation;
- restart does not resurrect an invalid browser/team pairing.

## Gates

Before merge:
- focused regressions for A-D green;
- full CI green;
- read-only red-team specifically on first-load/session-restore/switch boundaries, P1/P2 only.

After merge:
- deploy exact merge SHA;
- run a controlled hosted **true clean first-run** with browser-local state explicitly empty;
- then restored-session + league-switch + restart acceptance;
- only after those pass ask for physical iPhone/Safari validation.

Do not start Simulation 2.0, Long-Term Intrinsic, or other post-stabilization foundation work until this beta-availability incident is closed.
