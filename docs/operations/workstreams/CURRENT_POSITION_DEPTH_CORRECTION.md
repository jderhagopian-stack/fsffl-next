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


### 2026-10-06 — implementation trace / bounded design decision
- The shared Team Utility `build_league_relative_position_strengths()` contract currently aggregates `LineupAssignment.position`, intentionally attributing FLEX/SUPERFLEX back to actual player position. Simulation and Franchise consume that shared contract. **Do not mutate it in this tranche.** Current Position & Depth will receive a separate slot-based consumer contract so Simulation/Franchise semantics and Dynasty/#370 remain unchanged.
- The accepted lineup optimizer already records both configured `assignment.slot` and actual player `assignment.position`. Current will reuse the same joint optimized lineup and aggregate by `assignment.slot`; this preserves lineup optimization while preventing FLEX/SUPERFLEX production from entering fixed QB/RB/WR/TE totals.
- The governed in-season authority already exists: `build_governed_in_season_outlook()` -> finalized Sleeper weekly actuals + current REST_OF_SEASON Forecast (or the existing governed remaining-preseason-prior fallback) -> `compose_completed_actuals_with_ros()`. Current will consume this output without changing Forecast fitting/calibration.
- The production `league_team_views` presentation surface is already atomically persisted with Atlas. The new Current slot contract will be attached at the top level of that existing surface, so exact-generation/last-good continuity requires no new publication surface or lifecycle negotiation.
- Current slot order will include each configured supported starter-slot type once, preserving the league's configured lineup order; configured counts remain explicit. Fixed slots, FLEX, SUPERFLEX, K and DST are therefore league-driven rather than a hard-coded four-column grid.
- K/DST boundary: the standard governed completed-actuals + ROS path currently supplies offensive QB/RB/WR/TE fantasy-point authority, while the accepted 2026 K/DST path is explicitly provisional/partial-rule evidence and is not Team Utility authority. This correction will **show configured K/DST columns but leave rank/index explicitly unavailable unless the governed Current season-outlook input itself contains supported K/DST fantasy-point evidence.** It will not silently promote partial provisional K/DST evidence into a league-relative rank.
- A slot is rankable only when every team can fill that configured slot count from governed Current outlook evidence. Otherwise the slot remains visible but unavailable league-wide; missing evidence is not converted to zero. Deeper missing bench forecasts remain explicit player evidence and do not by themselves invalidate a legally filled optimized slot.
- Current drilldown will use the new completed-actuals + ROS player evidence and current optimized slot assignments. Dynasty drilldown remains on its accepted career-forward room contract.


### 2026-10-06 — implementation checkpoint
Implemented on the work branch, not yet promoted:
- added a separate `current_position_depth` product contract backed by the existing governed in-season outlook; no change to Forecast model/runtime fitting;
- Current lineups reuse the existing joint optimizer but aggregate strength by configured `assignment.slot` rather than actual player position;
- configured slot presence/order/count now comes from `LeagueRules.lineup`; FLEX/SUPERFLEX are independent columns and fixed slots cannot receive their contribution;
- configured K/DST remain visible but fail closed league-wide when governed Current season-outlook evidence cannot fill the slot;
- player/depth rows carry completed-actuals + ROS season-outlook evidence and optimized slot assignment separately from the strength numerator;
- `/api/league/team-views` now carries the Current contract as part of the already-governed atomic presentation surface; no new presentation surface/generation mechanism was added;
- hosted runtime caches the exact-State Current contract and obtains preseason fallback evidence through the existing governed in-season loader;
- League Atlas Current browser grid now consumes the new contract and derives columns dynamically; Dynasty continues to hard-code its accepted QB/RB/WR/TE room lens and uses the unchanged Dynasty endpoint/room contract;
- Current Overview pressure-point/position takeaway no longer reads the old full-season/actual-position strength rows;
- focused regressions added for FLEX isolation, SUPERFLEX isolation, configured K/DST unavailable behavior, depth separation, endpoint exposure and client contract selection.

Development validation has not yet been declared complete. The final static delivery fingerprints must be refreshed only after the implementation head is otherwise stable, then the P0.6 merge gate will run affected focused validation plus one full suite.


### 2026-10-06 — focused development validation green
A temporary branch-only focused workflow was used solely to satisfy the P0.6 development-validation step without opening a merge-gate PR or running the full suite early. It was removed before the stable PR head and will not merge to `main`.

Final focused development run:
- workflow run `37556570175`;
- JavaScript syntax check passed;
- 122 focused tests passed with 1 unrelated Starlette TestClient deprecation warning;
- coverage included the new Current contract, governed in-season Forecast orchestration, lineup optimization, unchanged legacy league-relative position strength, League Atlas browser/static contracts, presentation continuity and provisional K/DST guardrails.

The focused run confirmed:
- FLEX points remain in the FLEX slot rather than moving into RB/WR;
- SUPERFLEX is independently ranked from fixed QB;
- configured K/DST are visible but unavailable without governed Current season-outlook fantasy-point authority;
- depth/player evidence remains separate from the slot-strength numerator;
- the legacy shared Team Utility actual-position strength contract still passes unchanged;
- browser Current consumes the new slot contract while Dynasty keeps its fixed QB/RB/WR/TE contract.

The temporary workflow was deleted at branch commit `bfe3a6e193c4c7eba0f2ffbfa8726e291309a802`. No full suite has been run for this correction yet. The next step is a bounded exact-head review, then the stable PR merge gate with affected focused workflows plus one full CI suite.


### 2026-10-06 — post-review focused revalidation
The bounded review refinement narrowed exception handling so only failure to obtain the governed in-season authority is converted to an explicit unavailable Current contract; implementation defects in slot composition are no longer mislabeled as missing Forecast authority.

Focused revalidation after that executable change:
- temporary branch-only workflow run `37556763122`: success;
- JavaScript syntax: success;
- 122 focused tests passed / 1 unrelated Starlette TestClient deprecation warning;
- temporary workflow removed again at `7226acaf865863f5bf74a6e11e1903d9fb9b750e`.

No production implementation changes remain planned before the stable merge-gate PR.


### 2026-10-06 — latest-main reconciliation / stable PR candidate
While this workstream was active, `main` advanced from `6b12cc349ac9f13ccfa00d644169382650310540` to `f58872782aa08a38b816517f2c9465439bda4820` through an operations/CI hygiene commit only; no product source overlapped this correction. The new root `AGENTS.md`, refreshed CURRENT_OPERATIONS/OPERATING_PROTOCOL, charter, North Star and architecture authority documents were read and reconciled before promotion.

The branch CURRENT_OPERATIONS entry now starts from the new main wording plus this active workstream, avoiding a stale-status overwrite. The permanent League Atlas focused workflow now includes the new Current Position & Depth module and focused tests so future Atlas changes preserve this consumer contract.

Product implementation remains unchanged from the final focused-green logic. Static delivery identities remain:
- `league_comparison.js` Git blob `0c4d44ec1d671d526b06294406b3a078a2135375` → inner Atlas key `20261005-atlas-0c4d44ec1d67`;
- `product_shell.js` Git blob `1625483baa5a506fbdf00d296768c8a95be83a0f` → outer index key `git-1625483baa5a`.

The branch is now ready for the stable PR merge gate. No more executable changes are planned unless exact-head validation identifies a defect.
