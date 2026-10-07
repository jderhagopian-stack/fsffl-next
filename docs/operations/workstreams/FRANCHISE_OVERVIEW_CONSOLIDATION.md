# Franchise Overview Consolidation

Updated: 2026-10-07
Status: ACTIVE — bounded implementation focused-green; stable merge gate pending
Authority: Management directive 2026-10-07, AGENTS.md, OPERATING_PROTOCOL.md, Project Charter, North Star Product Directive, architecture authority boundaries, CURRENT_OPERATIONS.md.

## Objective

Consolidate the standalone **Home** experience into **Franchise → Overview** so the managed-team Franchise Overview becomes the primary managed-team landing experience.

This is a presentation/product consolidation, not a new model or authority program.

The finished product should preserve the strongest approved Home visual language while eliminating Home-specific duplicate interpretations of Current intelligence.

## Management product contract

### Landing experience
- **Franchise Overview becomes the managed-team landing page.**
- Standalone **Home is retired** as a product surface.
- This tranche does **not** change the bottom-navigation structure yet. Bottom-nav promotion/replacement is a separate follow-on decision and must not be bundled here.
- Routing/landing behavior may be updated only as needed to make managed-team Franchise Overview the landing destination while preserving the existing navigation contract until the follow-on.

### Preserve the approved Home visual language
Carry forward the Home presentation qualities Management explicitly approved:
- managed-team identity treatment;
- dials/gauges where already useful;
- approved color language and visual hierarchy;
- **Season Outlook**;
- **What Matters Right Now**;
- scan-first, compact mobile presentation.

The goal is not to transplant Home code wholesale. Preserve the successful visual language while rebuilding the content as a Franchise Overview consumer of canonical authorities.

### Canonical content authority
Franchise Overview may organize, compress, visualize and explain governed outputs. It must not recreate them.

Use existing canonical Franchise / Current / Simulation authority:
- current roster/team identity and roster construction from the canonical Franchise/team presentation contract;
- Current Position & Depth only from the accepted lineup-slot Current authority completed in the #408–#415 program;
- competitive outlook / playoff / championship / scenario outcomes from Simulation authority;
- Value/Intrinsic evidence only through existing canonical Value contracts;
- pick ownership/outlook only through the accepted asset/pick presentation authority.

**No legacy Home-specific Current definition may survive.**
In particular:
- do not revive `team_view.position_strengths` as a competing Current rank/pressure-point authority;
- do not calculate a second position-strength formula for Franchise Overview;
- do not infer or synthesize Simulation outcomes in presentation;
- do not create a hidden composite “team score” or master ranking.

### Overview content intent
Franchise Overview should answer, in order:
1. **Who is this franchise?** — team identity and current competitive context.
2. **Where does it stand?** — Season Outlook from canonical Simulation/current evidence.
3. **What matters right now?** — concise governed interpretation using canonical Current / Simulation / Value evidence, never legacy Home heuristics.
4. **Where are the roster strengths/weaknesses?** — compact visual summary sourced from canonical Current Position & Depth, with drill-through rather than duplicated calculations.
5. **What should I inspect next?** — clear paths into the existing Roster and Assets & Picks tabs or other already-authorized surfaces.

“What Matters Right Now” is a presentation narrative over governed evidence. It may select/highlight existing authoritative facts; it may not invent recommendation economics or a new ranking formula.

### Existing Franchise tabs stay intact
- **Roster remains intact.**
- **Assets & Picks remains intact.**
- Their existing contracts, content ownership, data sources and drilldowns are not redesigned in this tranche.
- Overview may link/drill into them but must not merge away or duplicate their detailed content.

### Home retirement boundary
Retiring Home means:
- remove or bypass standalone Home rendering/routes only after Franchise Overview provides the accepted managed-team landing experience;
- eliminate Home-only duplicated presentation logic that would otherwise remain authoritative-looking;
- preserve reusable visual components/styles where they improve Franchise Overview and do not carry legacy authority;
- do not delete shared underlying canonical API/data contracts merely because Home consumed them.

Do not perform unrelated cleanup in the same tranche.

### Navigation boundary
- **Do not change the bottom-nav structure in this tranche.**
- No decision is made here about which surface becomes the fourth primary bottom-nav item after Home retirement.
- Market vs Trade Center naming/navigation remains outside scope.
- A separate Management follow-on will decide bottom-nav composition.

### Mobile / product quality
- iPhone/Safari remains the physical acceptance device.
- Preserve the compact visual density Management approved on the accepted Home and #415 Position & Depth surfaces.
- Avoid large dead zones, duplicated headings, or stacked explanatory prose when a compact visual summary/drilldown will do.
- The default read should follow SEE → UNDERSTAND → INTERACT → DRILL DEEPER.

## Non-goals / preserved boundaries

Do not change:
- Current Position & Depth semantics or #415 accepted physical behavior;
- Dynasty/#370;
- Forecast model/runtime authority;
- Simulation model/runtime semantics;
- Career/Long-Term Intrinsic authority;
- Market, Trade Center, Search or Decision economics;
- Roster tab contract;
- Assets & Picks tab contract;
- bottom-nav structure;
- P0 lifecycle/publication architecture;
- saved-session/refresh policy.

No new provider refresh, publication surface or lifecycle negotiation is authorized merely to support this consolidation.

## Implementation sequence

1. **Trace current surfaces before code.**
   - map standalone Home route/render/data dependencies;
   - map Franchise Overview route/render/data dependencies;
   - identify which Home visual components/styles are reusable without carrying Home-specific authority;
   - identify canonical Current/Simulation/Franchise fields already published and sufficient for the consolidated Overview;
   - identify the minimum routing change required to make Franchise Overview the managed-team landing page without changing bottom-nav composition.

2. **Implement Overview first.**
   - build the consolidated Franchise Overview using canonical contracts only;
   - preserve Roster and Assets & Picks unchanged;
   - preserve physical/mobile visual quality.

3. **Retire standalone Home only after Overview is functionally complete in the same draft PR/head.**
   - no interim production state where the managed-team landing experience is missing;
   - avoid broad route/navigation cleanup beyond the minimum consolidation.

4. **Validation.**
   - focused Franchise/Home/Current/Simulation presentation tests during draft development;
   - explicit regressions proving no legacy Home `position_strengths` Current ranks/pressure-point authority survives in the consolidated Overview;
   - focused mobile/static/routing checks;
   - one exact stable-head full-suite gate only when the implementation head is final.

5. **Promotion.**
   - merge only the exact reviewed stable head;
   - deploy explicitly because Render auto-deploy is disabled;
   - verify exact merge SHA/runtime startup;
   - perform authenticated iPhone/Safari acceptance of the new managed-team landing/Franchise Overview;
   - checkpoint exact evidence before declaring directive complete.

## Acceptance criteria

The tranche is accepted only when:
- a saved/managed user lands on Franchise Overview as the managed-team landing experience;
- Overview visibly preserves approved Home identity, dials/colors, Season Outlook and What Matters Right Now presentation language;
- those sections consume canonical Franchise/Current/Simulation/Value evidence and contain no Home-specific competing Current formula;
- canonical Current Position & Depth is the only Current positional authority exposed by the consolidated Overview;
- Roster and Assets & Picks tabs are behaviorally intact;
- standalone Home is retired without changing bottom-nav structure;
- no silent heavy refresh/lifecycle regression is introduced;
- iPhone/Safari physical acceptance confirms the consolidated Overview is compact, readable and useful;
- exact stable-head test/merge/deploy identities are durably recorded.

## 2026-10-07 — start checkpoint

Management closed Current Position & Depth after authenticated #415 iPhone/Safari acceptance and immediately authorized this bounded consolidation.

This document is the **pre-implementation product contract**. No executable Franchise/Home code is changed before this checkpoint is merged to the durable operations record.


## 2026-10-07 — pre-code surface/authority trace

The first implementation trace is complete; no executable file was changed before this checkpoint.

### Existing Home surface
- Base app route defaults to `league`.
- Standalone Home is rendered by `home_dashboard.js` into `#league-screen/#home-attention`.
- Home currently reads `/api/home` and owns its own presentation shell/styles.
- Product Shell eagerly/lazily installs Home on initial load and whenever route `league` is opened.
- The main HTML still carries a Home-specific presentation guard and direct Home script delivery.
- Home's approved visual language is identifiable and reusable: circular team identity mark, compact dark cards, cyan/green dial treatment, Season Outlook rings and compact “what matters”/secondary-row visual hierarchy.
- Legacy Home positional ranks were already suppressed during the completed Current Position & Depth corrective, so no accepted Current logic needs to be preserved from Home.

### Existing Franchise surface
- `my_team_dashboard.js` already owns three tabs: **Overview / Roster / Assets & Picks**.
- Roster and Assets & Picks are already separable render functions and can remain unchanged.
- Franchise already reads canonical `/api/my-team`, `/api/league/team-views` and Value lenses.
- It additionally reads `/api/home` solely to populate standings/Simulation helpers.
- Active Franchise Overview still reads legacy `view.position_strengths` for its position rings, strongest/weakest diagnosis and pressure action. This is now a superseded Current definition and must be replaced rather than cosmetically retained.
- `/api/league/team-views` already publishes the accepted top-level `current_position_depth` contract from the completed Current program. No new Current API or formula is required.
- Franchise's own team view already exposes Simulation-derived competitive outcome fields, and league team views expose the same governed outcome coordinate for league-relative comparison. Season Outlook therefore does not need a Home-specific Simulation interpretation.

### Routing / landing boundary
- Current initial route is `league`; Product Shell separately handles `my_team`.
- The bottom-navigation metadata still contains both Home and Franchise and is explicitly out of scope.
- Minimum consolidation path: preserve `league` as the unselected-team/connect bootstrap, but once a managed team exists normalize managed `league` navigation to `my_team` and make `my_team` Overview the landing destination. This retires the managed standalone Home surface without deciding the later bottom-nav composition.
- Standalone Home JS no longer needs to load/install for a managed session.

### Bounded implementation decision
- Recompose **Franchise Overview only**.
- Carry Home's approved identity/dial/card visual language into the existing Franchise Overview tab.
- Season Outlook reads the existing governed Simulation-derived outcome on the Franchise/team-view contract.
- Position summary / “What Matters Right Now” reads only the published `current_position_depth` slot-strength rows for the managed team.
- Slot drill-through navigates to League Atlas Position & Depth rather than recreating detailed Current room logic inside Franchise.
- Roster and Assets & Picks renderers/data contracts are not changed.
- Do not create a new server publication surface, new lifecycle negotiation, new Current calculation or new Simulation calculation.


## 2026-10-07 — bounded implementation checkpoint

Implementation has started only after the product contract and pre-code trace were durably checkpointed.

Current draft implementation:
- Franchise North Star state now attaches the already-published top-level `current_position_depth` contract from `/api/league/team-views`;
- active Franchise Overview no longer reads legacy `view.position_strengths`;
- Season Outlook reads the Franchise/team-view `utility.competitive_outcome` Simulation-derived coordinate and league-relative expected-wins rank from the existing league team views;
- “What Matters Right Now” selects the weakest **canonical Current lineup slot** as a presentation highlight only; it shows the existing rank/index and links to League Atlas Position & Depth rather than inventing a recommendation or second room model;
- compact Current slot rings are rendered from canonical `current_position_depth.slot_order/strengths`; slot drill-through goes to League Atlas;
- approved Home identity/card/dial/color treatment has been carried into Franchise Overview;
- Roster and Assets & Picks render functions are unchanged;
- Franchise no longer reads `/api/home` for Overview composition;
- managed `league` navigation is normalized to `my_team` once a managed team exists, so Franchise Overview becomes the managed-team landing experience while the no-team `league` route remains a connect/select bootstrap;
- the bottom-navigation metadata is unchanged: Home / Franchise / League / Market remain structurally present pending the separate follow-on decision;
- standalone Home JS is no longer delivered or installed, and the Home-only first-paint presentation guard is removed;
- Franchise and Product Shell browser delivery keys are content-derived so Safari receives the consolidated bundles.

No server/model/lifecycle contract has been added or changed. Focused Franchise/Home-routing/Current presentation validation is the next gate. Do not run the Stable full suite until the exact implementation head is focused-green and stable.


## 2026-10-07 — focused implementation validation green

Draft executable/test head `f568e385683f7d0ef809840bfc0e98732f1be181` is focused-green and clean against main `4a1d3147795ed37a149963754210fd63b80c7d25`.

Focused evidence:
- CI `37677132290`: success;
- Franchise North Star `37677132339`: success (**61 passed**);
- Home North Star / retirement + destination regression `37677132235`: success (**81 passed / 1 unrelated Starlette warning**); the historical Home real-league sanity step correctly used its checked-in environment-boundary evidence because CI has no production database secret;
- League Atlas North Star `37677132354`: success;
- PR164 focused corrective regression `37677132359`: success (**123 passed / 1 unrelated Starlette warning**);
- Live Forecast corrective trace `37677132392`: success;
- Stable full suite `37677132282`: correctly skipped while PR #418 remains draft.

The first focused attempt exposed only stale static assertions from the old Home/Franchise routing wording; product behavior was not reverted. Those tests were reconciled to the accepted consolidation contract. Shared readiness/manual-refresh/mobile-delivery regressions were preserved rather than discarded when the Home UI tests were retired.

Reviewed implementation boundaries at this checkpoint:
- no backend/API/model/runtime/lifecycle file changed;
- active Franchise Overview contains no `/api/home` read and no `view.position_strengths` Current consumer;
- Roster and Assets & Picks active renderers remain intact;
- bottom-navigation metadata is unchanged;
- no-team `league` connect/bootstrap remains available;
- managed `league` resolves to `my_team`;
- standalone Home JS is no longer shipped by the document shell or dynamically installed by Product Shell;
- Current Position & Depth drill-through delegates to League Atlas;
- Trade Center dynamic navigation remains intact under the normalized-route variable.

Current delivery identity:
- consolidated `my_team_dashboard.js` blob `7844908b5c0bc09026dc143aa3812c8fc9f4a2a0`;
- Franchise inner key `20261007-franchise-7844908b5c0b`;
- `product_shell.js` blob `32ad2d78af0f34e61fcc2630d9d81478301bd68f`;
- outer Product Shell key `git-32ad2d78af0f`.

No executable work remains planned. After this documentation-only checkpoint head is stable, mark that exact PR head ready for the one P0.6 Stable full-suite gate; merge/deploy only if green.


## 2026-10-07 — first stable-gate result / test-only correction

Exact candidate `a8988aee5af75d0e0efa11e74a8c9564c74314c1` was marked ready only after all focused workflows were green and the checkpoint showed no planned executable work.

Stable full-suite run `37681492299` correctly verified that exact PR head before testing. The suite completed **2,224 passed / 2 failed / 1 warning**. Both failures were stale test expectations in `tests/test_readiness_progress_truth_static.py` that still required the retired standalone `home_dashboard.js` bundle to be shipped from `index.html`:
- `test_readiness_recovery_busts_refresh_asset_without_churning_unchanged_shell`;
- `test_continuity_release_busts_recovery_presentation_assets`.

This is a test-contract mismatch, not a product/runtime regression. The accepted Franchise consolidation explicitly removes standalone Home delivery, and focused Home/Franchise retirement validation had already proven that behavior.

PR #418 was returned to draft before changing the head. The only correction is test-only: those two readiness/static assertions now require `/static/home_dashboard.js` to be **absent** from the document shell while preserving the existing checks for forecast-refresh, Product Shell, Safari recovery and session-recovery asset identity. No executable file changed after the focused-green implementation head.

Next gate:
- allow ordinary draft focused validation to complete on the corrected head;
- if green and no new executable finding appears, checkpoint the exact head and mark it ready for a fresh Stable full-suite run;
- merge/deploy only that exact successful head.


## 2026-10-07 — test-only gate correction focused-green

The stale readiness/static assertions exposed by Stable full-suite run `37681492299` were corrected without changing executable behavior. The assertions now enforce the accepted Home-retirement contract: `index.html` must **not** ship `/static/home_dashboard.js`, while unchanged refresh/recovery/Product Shell delivery identity checks remain intact.

Exact corrected draft head `b72e85f6054d7e81176d774d7b8fb5f9325526db` is focused-green:
- CI `37682328049`: success;
- Franchise North Star `37682328141`: success;
- Home North Star / retirement + destination regression `37682328151`: success;
- League Atlas North Star `37682328068`: success;
- PR164 focused corrective regression `37682328051`: success;
- Live Forecast corrective trace `37682328024`: success;
- Stable full suite `37682328287`: correctly skipped because PR #418 remained draft.

The only executable implementation remains the previously reviewed focused-green Franchise consolidation. No executable, server, model, Current, Simulation, lifecycle, Roster, Assets & Picks, or bottom-navigation behavior changed after implementation head `f568e385683f7d0ef809840bfc0e98732f1be181`.

No further executable or test work remains planned. After this documentation-only checkpoint push, mark the exact final PR head ready for the fresh Stable full-suite merge gate. If that exact head is green, merge/deploy/checkpoint; do not broaden scope.


## 2026-10-07 — second stable-gate stale assertion

Fresh Stable full-suite run `37683206596` on documentation-final head `088c54af77423270021e1520e458cc09aa52f711` again reached the exact-head gate correctly. Result: **2,225 passed / 1 failed / 1 warning**.

The sole failure was another stale assertion in the same readiness/static regression: it still required the removed `homeNorthStarStaticVersion` and the old fixed Franchise version string `20261001-continuity2`. The active Product Shell correctly has no Home static-version constant and uses the content-derived Franchise key tied to `my_team_dashboard.js`.

PR #418 was returned to draft before the head changed. The correction remains test-only:
- assert `homeNorthStarStaticVersion` is absent from Product Shell;
- assert the Franchise version equals `20261007-franchise-<current my_team_dashboard.js git blob prefix>`.

No executable behavior changed. Re-run ordinary draft focused validation, then mark the exact corrected head ready for a fresh Stable full-suite gate. Do not merge a superseded head.


## 2026-10-07 — ready-review findings before final promotion

Automated ready-head review surfaced two bounded product defects on the consolidated Franchise implementation. Both are inside this tranche and must be corrected before another Stable gate:

1. **Publication-generation alignment (P1).** Franchise loads `/api/my-team` and `/api/league/team-views` in parallel. Both responses already carry response-level `publication_generation_id`, but the client only checked the State ID after both reads. A same-State publication promotion between the two reads could therefore combine Simulation/team evidence from generation A with Current/league evidence from generation B. Corrective contract: validate both State identity and response publication generation across the pair; retry a bounded number of times, then keep/fail closed to last-good instead of mixing generations. No new lifecycle negotiation or backend contract is authorized.
2. **Overview action controls (P2).** The new Overview renders `data-franchise-route` and `data-franchise-tab-open` actions, but the active North Star render path did not bind those selectors. Corrective contract: bind the existing route actions and internal Roster / Assets & Picks tab openers. Do not change navigation composition or add new destinations.

The separate readiness-test finding from the prior Stable run has already been corrected. PR #418 remains draft while these two executable defects are fixed and focused-tested. A new Stable full-suite gate is required after the exact corrective head is focused-green.


## 2026-10-07 — final-head review blockers before merge

Exact ready head `a746e577e2813acd71bb689f4e787843e2186964` passed Stable full-suite run `37685510399` successfully. Before merge, final automated review on that **same exact head** surfaced two bounded presentation defects. Under AGENTS.md's reviewed-stable-head rule these are merge blockers, so PR #418 was returned to draft before changing code.

1. **Last-good continuity alignment.** The new Franchise pair loader requires both served State IDs to equal the target `expectedStateId`. That rejects an accepted `presentation_continuity.mode === "stale_last_good"` pair, where both responses legitimately serve the same prior State/generation while explicitly targeting the current canonical State. Correct behavior: accept a pair only when both responses target the expected State, agree on served State, and agree on publication generation. Do not weaken generation fencing or mix publications.
2. **Independent Franchise tabs on league-read failure.** The pair loader uses an uncaught `Promise.all`, so a transient `/api/league/team-views` failure prevents the otherwise healthy `/api/my-team` response from rendering. Roster and Assets & Picks are owned by the managed-team contract and must remain usable. Correct behavior: fail closed only for league-relative Overview/Current evidence when the league read is unavailable; retain the managed-team response and intact tabs.

These corrections do not change the product contract, Current semantics, Simulation, Roster, Assets & Picks, bottom navigation, lifecycle architecture, or server APIs. After focused Franchise validation is green, a new exact-head Stable full-suite gate is required before merge.


## 2026-10-07 — final review corrective focused-green

The two exact-head review blockers from `a746e577e2813acd71bb689f4e787843e2186964` were corrected narrowly in Franchise presentation only.

Executable corrective head: `000ffe4ac7821d599a9112f97f17dca8765ff248`.

Corrections:
- Franchise response alignment now distinguishes **target State** from **served State**. Both responses must target the canonical expected State, agree on the same served State, and carry the same non-null publication generation. This preserves exact-generation safety while accepting governed `stale_last_good` continuity.
- Franchise reads now settle independently. A failed `/api/my-team` read still fails the Franchise load, but a transient `/api/league/team-views` failure preserves the valid managed-team response. League-relative Overview/Current evidence becomes unavailable; Roster and Assets & Picks remain usable.
- No backend, model, Current, Simulation, Roster, Assets & Picks, bottom-nav, publication or lifecycle contract changed.
- Safari delivery fingerprints were refreshed: `my_team_dashboard.js` blob `5531858fec44723044023453ec891e780e40c881` → Franchise key `20261007-franchise-5531858fec44`; `product_shell.js` blob `a390c91094697fc74ad2885d7115f0a351f34ab5` → outer Product Shell key `git-a390c9109469`.

Focused validation on the executable head is green:
- Franchise North Star `37688553389`: success;
- Home North Star `37688553370`: success;
- League Atlas North Star `37688553401`: success;
- CI `37688553429`: success;
- PR164 focused corrective regression `37688553416`: success;
- Live Forecast corrective trace `37688553510`: success;
- Stable full suite `37688553376`: correctly skipped while PR #418 remained draft.

Both final review threads were answered and resolved after this evidence. No executable work remains. The next PR-head movement is documentation-only checkpointing; mark that exact final head ready for one fresh Stable full-suite gate, then merge/deploy only if the successful gate still matches the PR head exactly.
