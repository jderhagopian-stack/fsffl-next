# Current Position & Depth Correction

Updated: 2026-10-06
Status: PHYSICAL ACCEPTANCE REOPENED — #408 core authority accepted; bounded Current presentation/coverage corrective active
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
- hosted runtime rebuilds the Current contract from fresh governed evidence for each presentation build and obtains preseason fallback evidence through the existing governed in-season loader; the published presentation surface is the reusable read cache;
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


### 2026-10-06 — PR #408 draft reconciliation under final P0.6 protocol
Current main is now `4f49106676b98d39ab7d43fa5fa241368bb7b55c`. The final P0.6 method supersedes the older “generic PR CI runs the full suite” wording recorded earlier in this checkpoint:

- implementation PRs remain **draft** during corrective/code/checkpoint pushes;
- generic `CI / test` is focused development validation only;
- the one full suite runs from `.github/workflows/stable-full-suite.yml` only after the exact stable head is marked ready for review;
- if code changes after that run, return to draft before pushing and mark ready again only when the new head is stable;
- before merge, the current PR head must exactly equal the successful stable-full-suite head;
- GitHub enforcement is not claimed; this is the procedural pre-merge gate.

PR #408 was converted back to draft before making the corrections below.

#### Open review finding — cache freshness
Codex review on reviewed head `f54c8dcd4b9d05cdcc0793c224412071161d4c11` correctly identified that the hosted Current contract cache was keyed only by `(league_id, state_id)`. ROS evidence and the completed-week boundary can advance while canonical State identity remains unchanged, and a transient unavailable result could therefore persist across same-State republications.

Bounded correction:
- removed the State-only `_current_position_depth_cache` entirely;
- `_current_position_depth_provider()` now composes from fresh governed completed-actuals + ROS evidence whenever a new presentation payload is built;
- exact published presentation continuity remains the reusable read cache after composition, so this does not create a second lifecycle/cache authority;
- an explicit regression forbids reintroducing the State-only Current cache.

#### Prior PR test blockers
The pre-final-P0.6 PR run happened while #408 was incorrectly non-draft and used the older generic full-suite workflow. Its relevant failures were:
- stale static expectations for the superseded “optimized starter production” Current wording;
- one standing read-only Atlas copy assertion lost during copy cleanup.

Those Current/Atlas assertions were corrected narrowly. The unrelated Simulation replay digest failure from that obsolete full-suite run is not being patched in this workstream; current main's accepted P0.6 full-suite gates passed and this tranche does not alter Simulation.

No Forecast, Simulation, Dynasty/#370, Career Intrinsic, publication-generation, or provider-refresh semantics are broadened by these corrections.


### 2026-10-06 — draft corrective validation complete
PR #408 draft head `477b17d9981effd2d65397fdab02d123019c7b06` completed the post-review focused gate successfully:
- `CI` run `37563486886`: success under the final P0.6 draft-focused protocol;
- `League Atlas North Star focused validation` run `37563486829`: success, including JavaScript syntax, **106 focused tests passed / 1 warning**, real-league Atlas composition sanity, final live-provider authority audit, and evidence upload;
- Home, Franchise, Live Forecast corrective trace, PR164 corrective regression, and Private-beta Intrinsic diagnostics triggered by the touched shared files all completed successfully;
- `Stable full suite` correctly skipped while the PR remained draft.

The cache-freshness review thread was answered and resolved after this evidence. PR #408 is mergeable/clean against current main `4f49106676b98d39ab7d43fa5fa241368bb7b55c`. No executable changes remain planned. After this documentation-only checkpoint push receives its ordinary draft focused check, the exact head may be marked ready for the **single** stable full-suite gate.


### 2026-10-06 — first stable-head gate returned to draft
PR #408 stable candidate `e45deb15298cdd255565d8ddb56a0ccb8cebdf34` was marked ready only after all draft focused workflows were green. Stable full-suite run `37563840095` verified that exact head before testing, then completed **2,207 passing tests / 1 failure / 1 warning**. The only failure was the existing 50,000-trial Simulation replay digest guard:

- test: `tests/test_simulation_hot_loop_equivalence.py::test_50000_run_output_matches_governed_settings_derived_postseason_baseline`;
- Python 3.11 expected digest: `ab42d84f680f82467c3088842019788cad0b375783b0aed5b37113e694678a65`;
- observed digest on #408: `8a2c44b86d81ef48f36345f1cd243f1007328eedab1b3a6d40fb6f01193808ff`;
- #408 changes no Simulation implementation or accepted Simulation semantics;
- current main's immediately preceding accepted P0.6 stable full-suite run `37559055898` passed all 2,197 tests on Python 3.11.16 / NumPy 2.4.6; the failed #408 gate had silently moved to Python 3.11.17 / NumPy 2.4.6 because Actions specifies the `3.11` minor rather than a patch.

PR #408 was returned to **draft before any further push**. Do not update the governed replay digest merely to make this unrelated failure pass. Diagnose the branch-local cause with focused test-order/isolation runs and correct only proven pollution or integration coupling.

### 2026-10-06 — terminal regular-season review finding
The exact-head ready review identified a second bounded Current defect: when Sleeper reports the NFL regular season complete at Week 18, the shared in-season orchestration clamps the ROS start to Week 18 while also loading Week 18 as completed actuals. The normal completed-actuals + ROS composer correctly rejects that overlap, which would make every Current rank unavailable after the regular season.

Accepted interpretation for this consumer: terminal regular season is the degenerate **completed actuals + zero ROS** case. Use governed completed actuals only, with no invented future projection or uncertainty, and preserve explicit provenance/evidence-basis labeling. Correct this narrowly in the Current authority path or a reusable Forecast helper if one already exists; do not alter Simulation, Dynasty/#370, or general provider lifecycle semantics.


### 2026-10-06 — terminal-season correction and focused acceptance
The Week-18 review finding is corrected within Forecast authority:
- `compose_completed_actuals_only()` now represents the terminal regular season as factual SEASON observations with zero remaining uncertainty;
- `build_governed_in_season_outlook()` uses that path only when `completed_through_week == 18`, returns no forward forecasts, labels the basis `completed_actuals_only`, and never requests an overlapping ROS period;
- League Atlas explicitly says “completed regular-season actuals … no ROS games remain” for this basis;
- K/DST authority remains unchanged: standard completed-actuals acquisition still covers offensive QB/RB/WR/TE only, so configured K/DST continue to fail explicitly when unsupported.

Draft focused evidence on the terminal correction:
- League Atlas run `37564796042`: success, **108 focused tests passed / 1 warning**, JavaScript syntax, real-league Atlas composition sanity, live-provider authority audit and evidence upload;
- all other triggered focused workflows at the terminal-correction head were green;
- the Week-18 review thread was answered and resolved.

Final static delivery identities after the terminal copy correction:
- `league_comparison.js` blob `f8041ee367c4b1144128ac9538f3cf2f12607f72` → Atlas key `20261005-atlas-f8041ee367c4`;
- `product_shell.js` blob `1a77b171b49f20f41ed1171eb5a97d90d2e11de6` → index key `git-1a77b171b49f`.

### 2026-10-06 — stable-gate Simulation blocker root cause
Focused isolation proved the failed Simulation replay digest was not caused by #408 product code:
- diagnostic run `37564690642` passed the 50,000-trial replay guard on the branch in isolation, after the new Current tests, after the changed Current/Atlas tests, and on current main;
- the Simulation test, Simulation implementation, benchmark request and pyproject blobs are byte-identical between current main and #408;
- runner evidence then exposed the real difference: the accepted P0.6 main gate used Python **3.11.16**, while the failed #408 stable gate had automatically advanced to **3.11.17** under `actions/setup-python` with `python-version: "3.11"`.

The replay test already intended to normalize exact Python patch identity because its governed output baseline is per Python minor, but it normalized only the visible `rng_runtime_version` fields. Multiverse `simulation_id` and `world_id` are derived from the exact runtime string, so the patch version still leaked into the supposedly patch-normalized digest.

Narrow testing correction only:
- Simulation implementation, RNG protocol, seeds, football outputs, selected worlds, world indexes and production replay identity are unchanged;
- the test now recomputes only those two derived Multiverse IDs against the reviewed baseline patch identity for the current Python minor, while continuing to hash all football outputs and replay coordinates;
- the existing governed expected digest is unchanged;
- post-correction hash-seed sweep `37565403757` passed the replay guard for `PYTHONHASHSEED=0..31` on Python 3.11.17;
- draft focused workflows at correction head `4b0068ede67f4682376ad0f3e15cca701bb53a88` all passed; the stable full suite remained correctly skipped while draft.

Temporary diagnostic workflows were removed before the stable candidate. No Simulation production semantics were modified.


### 2026-10-06 — #408 stable gate, merge and live deployment
Final stable candidate:
- PR #408 exact stable head: `8d13b6df888246b4c582021548eff1a8152c8170`;
- all draft-head focused checks on that exact head were green, including `CI` run `37565765862`, `League Atlas North Star focused validation` run `37565765767`, Home `37565765800`, Franchise `37565767562`, Live Forecast corrective trace `37565765685`, PR164 corrective regression `37565765650`, Private-beta Intrinsic diagnostics `37565767858`, and corrective live-provider numerical trace `37565768216`;
- both review findings were resolved before promotion: same-State Current cache freshness and terminal Week-18 completed-actuals-only handling.

P0.6 stable merge gate:
- marking exact head `8d13b6df888246b4c582021548eff1a8152c8170` ready triggered the one `Stable full suite` run `37566936822`;
- the workflow verified the PR head matched that SHA before and after testing;
- result: **2,211 passed / 1 warning** in 127.56s;
- no executable change followed the green gate.

Merge/deploy identity:
- PR #408 squash-merged as `ca11ae3f485316c8936012af05bde96868d8f61c`;
- Render deploy `dep-db2rr1id0e5s73e6o7fg` was triggered explicitly because auto-deploy is disabled;
- deploy completed `live` at `2026-10-07T03:35:12.325987Z` on exact commit `ca11ae3f485316c8936012af05bde96868d8f61c`;
- application startup completed cleanly at `2026-10-07T03:35:06.744526822Z`;
- durable saved context restored to ready in `7,911.17 ms` (`restore_id=57888dc5-4137-4969-8f42-231e1dce7e04`);
- startup evidence showed successful persisted reads for league snapshot, current Forecast evidence, Simulation analytics, Market value and publication generation; no startup error-level failure was observed.

Accepted implementation now live:
- Current uses governed completed actuals + ROS during the regular season;
- after Week 18 it uses governed completed actuals + zero ROS with explicit `completed_actuals_only` provenance;
- fixed QB/RB/WR/TE exclude FLEX/SUPERFLEX attribution;
- configured FLEX and SUPERFLEX are independent Current columns;
- configured K/DST remain explicit and rank only when supported by governed Current authority;
- depth remains separate drilldown evidence;
- same-State republication recomputes Current from fresh governed evidence rather than reusing a State-only cache;
- Dynasty/#370, Career Intrinsic, provider-refresh lifecycle and Simulation production semantics are unchanged.

**MANAGEMENT GATE — CURRENT POSITION & DEPTH:** code, exact-head validation, merge, static delivery identity and hosted startup/runtime deployment are accepted. A final authenticated iPhone/Safari Current-lens check remains the only unproven presentation layer: confirm the Current grid renders configured lineup-slot columns, fixed-position ranks do not absorb FLEX/SUPERFLEX contribution, and the displayed Current evidence copy reflects completed actuals + ROS. Do not reopen settled model/cache/terminal-season findings unless contradictory hosted or physical evidence appears.


### 2026-10-07 — physical iPhone/Safari acceptance failure after #408
Management supplied authenticated iPhone/Safari physical evidence after live deploy `dep-db2rr1id0e5s73e6o7fg`. Contradictory evidence reopens only the affected Current Position & Depth acceptance layer under OPERATING_PROTOCOL.md; the lower-level #408 authority/slot-attribution work remains accepted where physically confirmed.

Physical evidence / accepted observations:
- the core fixed-slot vs FLEX/SUPERFLEX attribution is working;
- Current physical acceptance still fails because FLEX/RB/WR/TE are league-wide unavailable;
- Current column order is not the desired canonical scan order;
- Current position-detail player ordering, starter/depth counts and summary evidence are not yet slot-specific/product-correct;
- Current drawer still exposes team-wide fragility and Long-Term/Career Intrinsic shadow copy that do not belong in the Current positional summary;
- portrait iPhone layout wraps the slot headers instead of keeping one horizontally scrollable grid.

Management decisions for this corrective:
1. Trace why FLEX/RB/WR/TE are league-wide unavailable. Correct the **underlying governed coverage issue** only if an already accepted fallback exists; do not weaken fail-closed semantics or convert missing evidence to zero.
2. Current grid canonical order is `QB, RB, WR, TE, FLEX, SUPERFLEX, K, DST`, filtered to configured slots.
3. Current position-detail players sort by **Current Intrinsic Value descending**. Role/assignment remains visible. This is presentation ordering only; Value authority remains upstream.
4. Current drawer starter/depth counts are **specific to the selected slot**. A player assigned to SUPERFLEX does not count as a starter in the QB drawer merely because his actual position is QB.
5. Remove team-wide fragility from positional summary unless governed slot-specific resilience evidence exists. No new resilience model is authorized in this tranche.
6. Remove Long-Term/Career Intrinsic shadow copy from the **Current** drawer. Dynasty player/detail behavior remains unchanged.
7. Portrait iPhone Current layout must retain one horizontally scrollable grid with all configured slot columns on the same row; headers must not wrap into a second line/row.
8. Preserve lineup optimizer authority: maximize governed annual Current season-outlook points. Among equivalent optimal assignments, the higher season-outlook eligible player occupies the fixed position before FLEX/SUPERFLEX. Do not hard-code player-specific ordering.
9. Management's live physical example is Dak Prescott `327.1` vs Lamar Jackson `321.4` actuals+ROS; Dak at QB and Lamar at SUPERFLEX is currently consistent with the accepted tie/assignment rule. Any disagreement with those underlying projections is a separate Forecast-evidence question and is outside this corrective.
10. Preserve accepted actuals+ROS authority, Dynasty/#370, Simulation, and P0 architecture.

Validation protocol:
- keep implementation PR draft while correcting;
- use focused Current/Atlas/lineup coverage validation during development;
- mark one exact stable head ready only after focused evidence is green;
- run exactly one stable full-suite merge gate for that corrective head;
- merge/deploy/checkpoint only if green.

**Do not broaden scope.** In particular, do not redesign Forecast, change Dynasty/#370, alter Simulation production semantics, add a new resilience model, or reopen P0 lifecycle/publication architecture.


### 2026-10-07 — physical failure root-cause trace before corrective code
Hosted persisted evidence localizes the league-wide unavailable columns to **Forecast coverage**, not the slot-attribution guard:

- latest FSFFL `league_team_views` publication inspected: State `5ca7d09323d133ea927f142d4e2eceec56bfc885006f4b57d7df8ef16d2b9e3d`, generation `b9a5eefc00274c0c167c0701141e30919b1c5f84ebf47e6d2d325109af1d93c1`;
- Current status is `partial`; QB and SUPERFLEX are `ready`, while RB/WR/TE/FLEX are `unavailable`;
- for all 12 teams, the optimized Current contract recorded **zero** filled RB, WR, TE and FLEX slots, while QB/SUPERFLEX filled. The fail-closed league-wide guard is therefore reporting a real upstream absence rather than mis-ranking a partially filled slot.

Projection-history evidence shows the exact missing coordinate:
- current CBS ROS snapshot supplies `FUMBLES_LOST` for QB/RB/WR/TE;
- current Razzball ROS snapshot supplies `FUMBLES_LOST` for QB but not RB/WR/TE;
- the live ensemble correctly requires two independent sources per player/metric group;
- league scoring correctly treats an active scored `fum_lost` coordinate as material and refuses to interpret an undercovered coordinate as zero;
- result: the strict current ROS scorer can produce authoritative QB fantasy points but skill-position RB/WR/TE fantasy-point rows fall out of authoritative output. That in turn leaves the optimizer with no governed RB/WR/TE candidates.

An **already accepted Forecast fallback exists** and will be reused rather than weakening that strictness:
- the immutable preseason baseline is already the governed fallback when current provider output fails;
- `remaining_prior_from_preseason()` already converts that accepted season prior to only the unplayed schedule before completed actuals are added;
- the accepted preseason-baseline authority loader already applies Forecast's first-party `FUMBLES_LOST` supplement when the league scores that coordinate, preserving the existing strict scorer and provenance.

Bounded corrective design:
1. keep live current ROS authoritative wherever the strict scorer produces a player fantasy-point row;
2. for a player missing from authoritative live ROS output, use that player's **already-governed preseason remaining prior** only when available;
3. never replace a supported live player, never synthesize zero, and leave the player missing if neither authority can support him;
4. label the mixed evidence basis explicitly so Presentation does not imply every player came from live ROS;
5. keep the existing slot-level fail-closed rule unchanged.

The preserved preseason raw baseline has enough historical subject coverage to fill the configured offensive starter counts for the current FSFFL rosters once its accepted scoring/supplement path is applied; this is not a player-specific exception.


### 2026-10-07 — physical corrective focused validation green
PR #411 remains draft. Executable corrective head `532568a790d0999aaca406ca3941f0c72d1d5b93` is focused-green after the physical acceptance correction.

Implemented boundaries:
- strict live ROS Forecast scoring remains unchanged; live rows remain authoritative wherever supported;
- player-level holes in strict live ROS fantasy-point output may consume only the already-governed immutable preseason **remaining prior**, scored through the accepted preseason authority path (including the existing first-party FUMBLES_LOST supplement when required);
- no missing coordinate or missing player is converted to zero; unsupported evidence remains absent and the existing slot-level fail-closed rule is unchanged;
- Current slot order is canonical `QB, RB, WR, TE, FLEX, SUPERFLEX, K, DST`, filtered to configured lineup slots;
- Current drawer rows sort by Current Intrinsic Value descending while preserving Current slot assignment/role and actuals+ROS evidence;
- Current starter count is selected-slot-specific: a SUPERFLEX-assigned QB is eligible depth in the QB drawer but not a QB starter;
- Current positional summary no longer displays team-wide resilience/fragility without governed slot-specific resilience evidence;
- Long-Term/Career Intrinsic shadow evidence remains Dynasty-only and does not render in Current drawer rows/copy;
- portrait Current matrix uses one non-wrapping horizontally scrollable row for all configured slot columns;
- optimizer production code is unchanged. A generic regression locks the accepted equivalent-optimum preference that the higher season-outlook eligible QB occupies fixed QB before SUPERFLEX.

Focused evidence on exact executable head:
- `League Atlas North Star focused validation` `37571685957`: success; JavaScript syntax passed; **116 focused tests passed / 1 warning**; real 12-team Atlas composition sanity passed; final live-provider authority audit passed; evidence artifact uploaded;
- `CI` `37571685915`: success;
- `Home North Star focused validation` `37571685891`: success;
- `Franchise North Star focused validation` `37571686004`: success;
- `Live Forecast corrective trace` `37571685940`: success;
- `Corrective live provider numerical trace` `37571685890`: success;
- `PR164 focused corrective regression` `37571685914`: success;
- `Stable full suite` remained correctly skipped while PR #411 was draft.

The first draft attempt exposed only three stale static assertions from the superseded Current drawer semantics; they were corrected as tests, not by reverting the accepted product behavior. No unresolved executable finding remains.

Static delivery identities:
- `league_comparison.js` blob `2aed785d9c24b41590f6fc45e8496899f19abcde` → inner Atlas key `20261005-atlas-2aed785d9c24`;
- `product_shell.js` blob `abd5ed4d63ee760fbf7ce3cc578d35305d199dab` → outer index key `git-abd5ed4d63ee`.

No further executable changes are planned. After this durable checkpoint push receives the ordinary draft check, mark the exact PR head ready for the single P0.6 stable full-suite gate.
