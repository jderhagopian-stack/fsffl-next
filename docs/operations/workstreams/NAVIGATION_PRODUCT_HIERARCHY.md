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
