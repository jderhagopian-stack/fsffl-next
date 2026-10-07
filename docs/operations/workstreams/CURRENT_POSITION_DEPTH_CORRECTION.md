# Current Position & Depth Correction

Updated: 2026-10-06
Status: ACTIVE — implementation authorized
Authority: Management directive 2026-10-06, accepted Current Position & Depth / Forecast Authority Audit, Issue #369 history, OPERATING_PROTOCOL.md, CURRENT_OPERATIONS.md.

## Outcome

Correct the League Atlas **Current** Position & Depth consumer without reopening accepted Forecast, Simulation, Intrinsic, Career Coverage, Architecture Recovery, or Dynasty/#370 semantics.

The accepted audit found two consumer-semantics defects:
1. Current uses live full-season provider projections instead of the already-governed completed-actuals + rest-of-season season outlook.
2. FLEX/SUPERFLEX starters are attributed back into their actual QB/RB/WR/TE rooms, so a small optimized-lineup change can move roughly one whole player's production between fixed-position ranks.

This workstream corrects those two boundaries only.

## Accepted product contract

### Current production authority
- Once the season is underway, Current player production uses the existing governed **completed actuals + current ROS** season-outlook coordinate.
- Reuse the existing governed in-season outlook path; do not fit/retrain/recalibrate Forecast and do not create a parallel season model.
- Completed actuals remain facts; ROS remains Forecast authority. Compose them once under the existing governed contract.
- Preseason/offseason behavior must remain governed by existing supported authority rather than inventing completed-actuals data.

### Current grid / lineup-slot semantics
- The Current Position & Depth grid follows the league's configured lineup slots rather than assuming a fixed four-column QB/RB/WR/TE map.
- Fixed QB/RB/WR/TE columns measure only players assigned to those required fixed slots.
- FLEX and SUPERFLEX production must **not** be attributed back into QB/RB/WR/TE Current strength.
- When configured, FLEX and SUPERFLEX appear as their own Current columns and rank/index their optimized slot contribution directly.
- K and DST appear only when configured in the league and only when the existing governed Current production authority supports those positions. Unsupported authority must remain explicit/unavailable; do not synthesize projections or silently treat missing evidence as zero.
- Do not invent fractional FLEX/SUPERFLEX allocation rules.

### Depth semantics
- “Depth” remains separate drilldown evidence: roster/depth context may explain a room but does not get mixed into the Current strength formula.
- The scan-first Current grid remains about optimized lineup-slot production/rank. Bench/IR/taxi depth belongs behind the cell in drilldown evidence unless an existing governed contract explicitly says otherwise.

### Dynasty boundary
- Dynasty lens and Issue #370 economics/room-strength semantics are unchanged.
- Do not alter Career Intrinsic inputs, Dynasty room formula, coverage policy, generation fencing, or Dynasty presentation continuity in this tranche.
- Current may gain additional lineup-slot columns without forcing Dynasty to redefine its accepted QB/RB/WR/TE room semantics.

## Issue #369 continuity preserved

#369 began with the old Current contract: optimized starter production attributed back to actual position. Subsequent work added the Current | Dynasty lens and then corrected presentation/lifecycle defects without reopening Dynasty semantics. This correction intentionally supersedes only the old **Current** authority/attribution assumptions now disproven by the accepted audit.

Preserve the accepted mobile layout, loading states, publication-generation safety, saved-session restore policy, last-good continuity, and Dynasty fail-closed behavior established by the #369 follow-up sequence.

## Implementation plan

1. Trace the existing Current position-strength builder and its optimized-lineup slot assignment.
2. Replace the Current player production input with the existing governed in-season completed-actuals + ROS outlook, preserving supported preseason behavior.
3. Change Current aggregation from actual-position attribution to configured lineup-slot attribution:
   - fixed slots stay fixed;
   - FLEX and SUPERFLEX remain distinct;
   - K/DST are included only when configured and supported.
4. Drive Current grid columns from governed league lineup configuration in stable scan-first order.
5. Keep Current drilldown roster/depth evidence separate from the strength calculation.
6. Add focused contract tests for authority, slot attribution, dynamic columns, K/DST support/unavailability, and no Dynasty/#370 drift.
7. Use focused tests during development. At one stable PR head, run affected focused regressions and **one full suite** as merge gate.
8. Merge only that passing stable head, explicitly deploy because Render auto-deploy is disabled, verify exact merged SHA/live deploy/startup, then update this checkpoint with exact evidence. Documentation-only closeout after deploy does not require redeploy.

## Acceptance checks

Implementation acceptance requires direct evidence that:
- in-season Current consumes governed completed actuals + ROS, not live full-season provider SEASON evidence;
- a FLEX winner changing from WR to RB cannot move that player's production between fixed WR/RB strength;
- FLEX and SUPERFLEX are independently visible/ranked when configured;
- leagues without FLEX/SUPERFLEX do not render phantom columns;
- configured K/DST only appear with supported governed production evidence and fail explicitly otherwise;
- fixed-position ranks use only required fixed-slot starters;
- depth evidence remains available in drilldown but does not change Current strength;
- Dynasty/#370 outputs/contracts are unchanged;
- League Atlas still renders correctly from exact current and verified last-good presentation generations.

## Execution log

### 2026-10-06 — start checkpoint
- Reconciled current main with CURRENT_OPERATIONS.md and OPERATING_PROTOCOL.md.
- Read Issue #369 body/history. #369's original Current semantics explicitly attributed FLEX/SUPERFLEX back to actual position; later comments repeatedly instructed not to reopen #370 Dynasty semantics while correcting presentation/lifecycle defects.
- Accepted audit authority: Current presently consumes live full-season provider projections; completed actuals contribute zero; repository already has governed `build_governed_in_season_outlook()` composing finalized weekly actuals + REST_OF_SEASON Forecast. Audit also proved the large observed RB/WR rank swing was overwhelmingly FLEX attribution rather than underlying room change.
- Management-approved extension recorded here: Current grid follows configured lineup slots; FLEX/SF are first-class Current columns; configured K/DST appear only at supported authority; Depth is separate drilldown evidence.
- No implementation code changed before this checkpoint.
