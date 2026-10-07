# Franchise Overview Consolidation

Updated: 2026-10-07
Status: ACTIVE — product contract checkpointed; implementation not yet started
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
