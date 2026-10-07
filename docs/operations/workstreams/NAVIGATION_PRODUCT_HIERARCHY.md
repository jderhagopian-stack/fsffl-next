# Navigation / Product Hierarchy

Updated: 2026-10-07  
Status: ACTIVE — implementation authorized  
Authority: Management directive 2026-10-07, MANAGEMENT_CONTINUITY.md, PRODUCT_ROADMAP.md, FSFFL_NEXT_PRODUCT_PRIORITIES.md, AGENTS.md, OPERATING_PROTOCOL.md.

## Outcome

Create one coherent primary navigation hierarchy:

`Franchise | League | Explore | Trade | More`

This is a bounded **information architecture / navigation** tranche only. Preserve all destination behavior, governed analytical authority, publication/lifecycle architecture, and existing accepted product semantics.

## Product contract

### Primary navigation
- **Franchise** remains the managed-team landing surface.
- **League** remains League Atlas / competitive landscape.
- **Explore** is the existing Market destination under a consumer-facing label change only.
- **Trade** is the existing Trade Center destination promoted into the primary navigation.
- **More** contains secondary destinations that should remain accessible without occupying primary-nav slots.
- Obsolete/inert **Home** is removed from primary navigation.

### Routing / destination preservation
- Existing destination routes and internal destination identifiers should be preserved whenever possible.
- Renaming Market → Explore changes presentation/navigation labeling, not Search/Decision authority or Market economics.
- Promoting Trade Center → Trade changes navigation placement/labeling, not Trade Center functionality or Decision/Simulation behavior.
- More may reorganize links only; it must not change destination data contracts.
- Franchise remains the managed landing/default surface established by #418.
- League remains the current League Atlas destination.

### Secondary destination boundary
- More holds existing secondary product destinations rather than inventing new ones.
- Do not delete or disable an existing secondary destination merely because it moves behind More.
- Preserve direct/deep routes already used by the product unless a route is proven obsolete and Management explicitly authorizes removal.

## Explicit non-scope

Do **not** change:
- Forecast models, evidence, fallback rules, or scoring authority;
- Market/Value economics or value coordinates;
- Decision/Search economics, candidate scoring, or trade logic;
- Simulation semantics, replay identity, or counterfactual logic;
- Current/Dynasty Position & Depth semantics;
- Career Intrinsic / Foundation 4 / Career Coverage;
- State, publication, restore, refresh, caching, lifecycle, or P0 architecture;
- Franchise Overview content/semantics accepted in #418;
- League Atlas content/semantics.

No Home → Franchise product-content redesign is authorized here. #418 already retired standalone Home; this tranche removes its obsolete navigation residue.

## Sequencing

1. Checkpoint this contract before code.
2. Trace the current shared navigation renderer, destination identifiers/routes, active-state behavior, mobile/desktop presentation, More menu behavior, and tests.
3. Implement the smallest navigation-only change preserving destination functionality.
4. Use focused navigation/shared-shell tests during development while PR remains draft.
5. When the exact head is stable, mark ready and run the one Stable full-suite gate required by AGENTS.md.
6. Merge only that exact green head.
7. Explicitly deploy because Render auto-deploy is disabled; verify exact merge SHA, deploy ID, startup, and relevant route/static delivery evidence.
8. Stop at **MANAGEMENT GATE — NAVIGATION / PRODUCT HIERARCHY** for authenticated iPhone/Safari physical acceptance.

## Physical acceptance target

On authenticated iPhone/Safari:
- primary nav reads, in order: **Franchise | League | Explore | Trade | More**;
- no Home primary-nav item remains;
- Franchise opens the managed-team landing experience;
- League opens League Atlas;
- Explore reaches the existing Market experience;
- Trade reaches the existing Trade Center;
- More exposes the existing secondary destinations;
- existing destination behavior remains intact;
- primary navigation is usable in the accepted mobile shell with no obvious clipping/overlap regression.

## Post-acceptance next action

After Management physically accepts this navigation tranche, resume **Career Coverage #405** and its scorer-authority decision gate immediately. Do not enter another navigation polish loop absent contradictory acceptance evidence.

## Execution log

### 2026-10-07 — start checkpoint
- Verified GitHub main `7bddbc392832cd4de68e318f184af1ad353462a6`.
- Verified current live Render deployment `dep-db3bpn67bikc73cahdkg` serves #418 merge `ba66f906bde49bd7c956a5e495bc6e33a07ae9e6`.
- Reconciled AGENTS.md, CURRENT_OPERATIONS.md, MANAGEMENT_CONTINUITY.md, PRODUCT_ROADMAP.md, FSFFL_NEXT_PRODUCT_PRIORITIES.md, OPERATING_PROTOCOL.md, charter, North Star, architecture overview and authority boundaries.
- Management continuity already names this exact navigation tranche as next and Career Coverage #405 immediately after it.
- No executable/product code changed before this checkpoint.


### 2026-10-07 — implementation trace / draft candidate
Navigation implementation is intentionally route-preserving:

- the authoritative browser route IDs are unchanged: `my_team`, `league_comparison`, `opportunities`, `trade_center`, `behavioral_intelligence`, `what_if`, `simulator`, `reports`, `analytics`;
- the retired compatibility route `league` remains internally available for connect/restore normalization but is explicitly non-navigation and still resolves managed users to Franchise;
- primary product navigation is now exactly `Franchise | League | Explore | Trade | More` on both mobile and desktop;
- `Explore` is the existing `opportunities`/Market route with presentation-label changes only; its Search/Value/Decision behavior is unchanged;
- `Trade` is the existing `trade_center` route promoted to primary navigation; Trade Center logic and screen remain unchanged;
- `More` exposes Owners, What-If, Simulator, Reports and Analytics without duplicating Trade;
- the static pre-JavaScript sidebar fallback no longer renders Home or Market labels;
- the shell's temporary/fallback navigation also filters to primary destinations only so context updates cannot briefly repopulate retired/secondary primary items;
- desktop More reuses the existing accessible modal/sheet interaction; mobile retains the accepted five-cell bottom navigation and safe-area hardening;
- the Explore surface's top-level consumer label is updated from Market to Explore while domain terms such as Broad Market and market-match evidence remain unchanged;
- no API path, destination renderer, route identifier, model/economic code, State/publication behavior, or lifecycle code was changed.

Delivery:
- Product Shell outer cache identity was refreshed to match the modified shell blob;
- other changed static assets remain protected by the accepted content-fingerprint static-file redirect/immutable-cache mechanism.

Development syntax checks passed for `product_navigation.js`, `product_shell.js`, and `north_star_market.js`.

The branch is ready for a **draft** implementation PR and focused shared-shell/navigation validation. No full suite is authorized until the exact corrective head is stable and marked ready under P0.6.


### 2026-10-07 — focused validation green / stable-gate candidate
Executable/navigation head `4a0fe56cc0be34e75cc7982707affef280d32ccc` is focused-green.

Focused evidence:
- `CI` run `37699753797`: success (**6 passed / 1 warning**);
- `Franchise North Star focused validation` run `37699753865`: success; JavaScript checks passed and **65 tests passed**;
- `Home North Star focused validation` run `37699753796`: success; contextual-navigation JavaScript checks passed and **82 tests passed / 1 warning**;
- `League Atlas North Star focused validation` run `37699753816`: success; JavaScript checks, real-league Atlas composition sanity, live-provider authority audit and **126 tests passed / 1 warning**;
- `PR164 focused corrective regression` run `37699754018`: success (**126 passed / 1 warning**);
- `Live Forecast corrective trace` run `37699753788`: success;
- Stable full suite correctly skipped while PR #421 remained draft.

Two first-pass failures were stale tests that encoded the deliberately superseded navigation structure:
- Opportunity workspace expected one old literal route sequence even though the destination routes remained present;
- Home retirement expected the obsolete Home bottom-nav item to remain as a future follow-on.
Both were corrected as test expectations only. No analytical or destination behavior was changed to satisfy them.

Current PR #421 is clean against main `7bddbc392832cd4de68e318f184af1ad353462a6`. The product implementation is stable; no further executable changes are planned. The next exact PR head after this documentation-only checkpoint must receive its ordinary draft CI, then may be marked ready for the single P0.6 Stable full-suite merge gate.


### 2026-10-07 — #421 first Stable-gate result / stale navigation assertions only
Stable full-suite run `37700252118` tested exact ready head `b0f2119dd7390b9380d9056b54efacd8a8e7c133` and finished **2,227 passed / 3 failed / 1 warning**. The three failures are superseded navigation assertions only; product behavior matched the approved contract:

1. `test_legacy_players_route_delegates_to_market_player_board` required the old exact `players_assets` route literal and old generic nav filtering shape. The legacy route/delegation remains intact: `players_assets` is still present, marked `legacy:true,navigation:false`, and still delegates to `opportunities` with `marketTab:'player_board'`. The stale assertions were updated to that preserved compatibility route plus the new primary-only navigation filter.
2. `test_market_route_is_not_navigation_locked_before_team_context` still required the obsolete consumer label `Market`. The approved navigation label is `Explore`; route ID `opportunities`, icon/domain semantics, and non-team-scoped availability remain unchanged. The test now asserts `Explore`.
3. `test_simulator_is_first_class_team_scoped_product_route` still required Simulator to be first-class primary navigation. The approved hierarchy places Simulator under **More → Scenarios** while preserving the same `simulator` route, team-scoped behavior, lazy script loading and destination functionality. The test now verifies that secondary placement instead of restoring the superseded primary-nav contract.

PR #421 was returned to **draft before these test-only corrections were pushed**. No product/static/model/lifecycle code changed. The failed Stable run is superseded and cannot be used for merge.

Next gate: run focused navigation/shared-shell validation on the corrected draft head. If green and no executable work remains, mark that exact head ready once for a fresh Stable full-suite gate; if exact-head green, merge/deploy and stop for authenticated iPhone/Safari physical acceptance.


### 2026-10-07 — concrete gate blocker discovered after stale-test correction
Before merge, Codex review surfaced one real P2 navigation-contract defect on the corrected branch: if `product_navigation.js` fails to install, `product_shell.js::rebuildProductNavigation()` is the surviving browser fallback, but it currently renders only `item.primary` routes. That leaves Owners, What-If, Simulator, Reports and Analytics unreachable through the UI in the fallback state, violating the accepted secondary-destination preservation contract.

This is a **concrete navigation-only gate blocker**, so the earlier ready/full-suite attempt is superseded. PR #421 has been returned to draft before any product change.

Bounded correction:
- preserve the approved primary hierarchy `Franchise | League | Explore | Trade | More`;
- keep all route IDs and destination behavior unchanged;
- keep legacy `players_assets` compatibility/delegation unchanged;
- add a functional shell-level fallback **More** control that exposes the existing secondary routes when `product_navigation.js` is unavailable;
- do not expose secondary destinations as primary items and do not change model/data/lifecycle behavior.

After the correction, run focused navigation/shared-shell validation while draft. Only the final exact green head may be marked ready for the one Stable full-suite gate.
