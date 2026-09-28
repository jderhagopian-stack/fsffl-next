# 2026-09-28 — Stabilization Closure Protocol

## Status
**MANAGEMENT DIRECTIVE — SUPERSEDES SERIAL ONE-DEFECT-AT-A-TIME CLOSEOUT**

## Why this exists
The atomic-publication program has repeatedly reached an apparent “one narrow fix remaining” state, only for post-merge review or hosted acceptance to expose an adjacent lifecycle/concurrency defect.

That pattern is now treated as evidence that the stabilization verification process has been too serial, not as evidence that each newly found issue should trigger another immediate patch/deploy loop.

The goal is no longer “fix the current failing line.” The goal is to close the full **publication / persistence / restore / identity-change concurrency class** before the next production acceptance claim.

## Immediate operating change
Do **not** deploy another stabilization corrective merely because its local tests and CI are green.

Before the next merge/deploy candidate is accepted, complete one bounded whole-class audit and deterministic stress matrix over the publication lifecycle.

This is still a narrow runtime stabilization program. It does not reopen Forecast, Simulation, Value, Intrinsic, Market, Search or Research semantics.

## Governing invariants
The corrected runtime must make the following true as a class:

1. **Published generation immutability**
   - Ordinary readers see one coherent published generation.
   - Working reconciliation never partially mutates it.

2. **Atomic promotion**
   - State/Forecast/Simulation/Value/presentation identity move together at the publication boundary.
   - Durable restart authority cannot advance before the corresponding publication is terminal and coherent.

3. **Per-user isolation**
   - One user's restore, refresh, team selection, league switch or publication cannot block/deadlock another user's lifecycle.
   - Locks/serialization are scoped to the smallest correct ownership domain.

4. **Consistent lock ordering**
   - No publication / restore / checkpoint / identity-change path can acquire shared locks in opposing order.
   - No unbounded lock acquisition cycle exists.

5. **Changed-State continuity**
   - Prior compatible published presentation may remain visible while target-State intelligence builds.
   - Served generation identity is exposed only when the exact team/league/State predicate permits that presentation to be served.

6. **Same-State continuity**
   - A same-State refresh never removes previously valid user-visible intelligence merely because replacement work is incomplete.

7. **Identity changes**
   - Managed-team and league changes either occur before publication and invalidate/rebase stale work, or after publication completes.
   - They never strand a half-published durable generation.

8. **Crash/restart authority**
   - Restart restores only the last actually published generation.
   - Unpublished working artifacts can never become authoritative merely because they are newer.

9. **Cross-surface truth**
   - Home, Franchise, Atlas, Market, PI and readiness/banner diagnostics identify the same actually visible generation.
   - “Intelligence current” cannot coexist with surfaces that are only temporarily missing because background work is incomplete.

10. **Foreground availability**
    - Read-only foreground requests do not wait behind heavy reconciliation except where the exact requested action requires mutation authority.

## Required pre-merge red-team
Before the next runtime corrective merges, run a read-only adversarial audit of the **whole lifecycle**, not only the current P1.

Inspect actual lock ownership/order and state transitions for:
- cold first access;
- warm same-State refresh;
- changed-State refresh;
- managed-team change;
- league switch;
- publication finalization;
- checkpoint coalescing/waiting;
- presentation promotion;
- crash between each publication phase;
- restart after each interruption point;
- two different users doing conflicting lifecycle actions concurrently;
- provider outage while persisted evidence exists.

Return only concrete P1/P2 issues with actual code paths.

## Deterministic concurrency matrix
The corrected branch must contain deterministic tests for at least:

### Single-user lifecycle
- same-State refresh + repeated surface reads;
- changed-State refresh + stale-last-good reads;
- team switch before publication;
- team switch during final publication;
- league switch during reconciliation;
- crash after working checkpoint but before presentation promotion;
- crash after presentation build but before durable publication;
- restart after each interruption point.

### Two-user lifecycle
- User A final publication while User B cold-restores;
- User A checkpoint wait while User B activates State;
- simultaneous cold restore for A/B;
- simultaneous publication for A/B;
- team switch for A while B publishes;
- league switch for A while B restores.

Every case must complete within bounded time and preserve each user's exact publication identity.

## Stress/repetition gate
After deterministic tests pass, repeat the bounded concurrency/lifecycle suite enough times to expose scheduling-sensitive failures. The test must fail on timeout/deadlock, not hang indefinitely.

Do not use random stress as a substitute for deterministic coverage; use it as an additional gate.

## Review / merge / deploy sequence
1. Fix the currently known cross-user lock inversion as part of the lifecycle contract, not as an isolated patch.
2. Run the whole-class read-only red-team on the corrected branch.
3. Address any concrete P1/P2 lifecycle findings before merge.
4. Full CI green.
5. Deterministic concurrency matrix green.
6. Bounded repeated stress green.
7. Merge once.
8. Deploy exact merge SHA.
9. Run hosted FSFFL -> Hodor -> FSFFL plus same-State / changed-State / cross-surface / team-change / restart / two-user concurrency acceptance.
10. Only then request physical iPhone/Safari validation.

## Architecture preference
Prefer a simple ownership model over additional local guards:
- publication serialization should be per-user unless a genuinely global invariant requires otherwise;
- restore/checkpoint bookkeeping should not create global cross-user critical sections where avoidable;
- one lifecycle operation should have a clear owner and one documented lock order;
- avoid nested global locks;
- do not add sleeps/retries to mask ordering defects.

If the current locking structure cannot satisfy these invariants cleanly, a bounded refactor of the runtime lifecycle/locking boundary is authorized. This is preferable to another chain of local conditionals.

## Terminal state
Stabilization is complete only when:
- no known P1/P2 lifecycle defect remains from the bounded red-team;
- deterministic + repeated concurrency gates are green;
- exact deployed SHA passes hosted acceptance;
- physical iPhone/Safari smoke confirms coherent published intelligence.

Until then, do not describe the system as “one narrow fix away.”
