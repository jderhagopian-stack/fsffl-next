# FSFFL NEXT — North Star Visual Design & Interaction System

Status: **approved hybrid visual direction; bounded reference implementation pending management visual review**  
Date: 2026-09-20

Management approved a hybrid direction: **LOOK LIKE THE SUPPLIED EIGHT-SCREEN PREMIUM DARK, MOBILE-FIRST EXAMPLE. THINK LIKE THE CORRECTIVE NORTH STAR SYSTEM.** The supplied reference governs aspirational look/feel; this document governs hierarchy, interaction, progressive disclosure, and analytical authority. It governs Presentation only. It does not create model truth.


## Approved product-family benchmark

The approved aspirational product family is a premium dark, mobile-first fantasy-football application with:
- a dark, high-contrast shell;
- persistent, obvious mobile navigation;
- clear tabs/segmented controls when they map to real product states;
- stronger player, franchise, and owner identity;
- polished consumer-product typography and spacing;
- richer graphical intelligence: bars, rings, heat maps, comparison charts, trajectory visuals, and compact summaries when governed inputs support them;
- restrained elevation and cards used for bounded objects rather than every section;
- consistent cross-surface language across Home, Franchise, League, Market, Trade Center, Simulation/League Impact, and Owner Intelligence.

The eight-screen reference is a **visual/product benchmark, not a model specification**. Illustrative constructs in that mockup—such as Team Grades, Fit scores, behavioral certainty, recommendation strength, or similar labels—must not be copied unless FSFFL has governed authority for that exact output. Preserve the visual role with the nearest governed truth, a qualified signal, or an explicit unavailable/uncertain state.

### Hybrid rule

Use the approved dark consumer-product language for the surface. Preserve the corrective system underneath:
- one dominant truth;
- strong hierarchy;
- open composition where useful;
- exact evidence beside graphics;
- progressive disclosure;
- methods/provenance secondary;
- intentional mobile recomposition;
- upstream authority unchanged.

## 1. The interaction model: SEE -> UNDERSTAND -> INTERACT -> DRILL DEEPER

### SEE
The first 2–3 seconds must expose the primary truth without requiring paragraph reading.

Required implications:
- one dominant visual anchor per screen or decision state;
- identity appears before metadata;
- the most important comparison is graphical when graphics materially shorten interpretation;
- the most important exact number is typographically dominant;
- strengths, weaknesses, risk and action state use stable visual semantics;
- supporting facts do not compete at the same scale.

### UNDERSTAND
The user should be able to explain *why* the primary truth is present after one short scan.

Required implications:
- exact governed values remain visible next to visual encoding;
- relative context is explicit: rank, benchmark, before/after, counterparty, league average or horizon;
- one short interpretive sentence may bridge the visual evidence to meaning;
- prose does not restate every number;
- uncertainty is shown when governed evidence exposes it and otherwise remains unavailable.

### INTERACT
The default surface should invite a useful next inspection or action without forcing deep detail.

Required implications:
- hover/focus/tap reveals labels, exact values or adjacent context;
- selection changes visual focus, not model authority;
- one primary action is visually dominant only when an upstream authority justifies it;
- secondary actions are quieter and grouped by workflow;
- comparisons preserve state/context identity while the user explores.

### DRILL DEEPER
Technical depth stays available without dominating the first read.

Required implications:
- evidence, methods, provenance, exact tables and model metadata live in expandable drawers or secondary views;
- deep analytical views are linked to the same primary object/decision;
- no important governed evidence is deleted merely to simplify the surface;
- unavailable evidence fails closed rather than being replaced by decorative substitutes.

## 2. Composition system

### Approved dark-shell interpretation

The canonical shell is dark and premium, but **dark does not mean dense**. Use tonal depth, type scale, negative space, selective dividers, and a small number of elevated bounded objects. Avoid turning every fact into a navy rounded rectangle. A dominant stage may be open within the dark shell rather than placed inside another card.

A default decision/intelligence surface uses four layers:

1. **Primary Insight Stage**
   - dominant takeaway or decision state;
   - large identity and/or exact metric;
   - one visual comparison that explains the takeaway;
   - optional single primary action.

2. **Context Rail**
   - compact secondary signals that answer “what else matters?”;
   - visually subordinate to the stage;
   - no wall of equal-weight cards.

3. **Action Layer**
   - the justified workflow step: inspect, simulate, build, counter, target, stress test, etc.;
   - Presentation may surface an action only when the upstream system already supports it.

4. **Evidence / Drill-down**
   - exact tables, model detail, provenance, secondary metrics, methods;
   - collapsed or moved below the first viewport by default.

### Open composition rule
Cards are reserved for bounded interactive objects, warnings, or discrete modules. A section does **not** become a card merely because it needs grouping. Prefer:
- open canvas;
- strong type;
- whitespace;
- alignment;
- rules/dividers;
- one accent field;
over repeated dark rounded containers.

## 3. Typography & scale

The approved benchmark is app-like and mobile-first: concise labels, strong exact numbers, and compact but readable hierarchy. The corrective type scale remains the guardrail against the current beta's small-label/equal-weight failure mode.

The system uses scale to signal authority and reading order.

- **Primary takeaway:** 42–64 px desktop, 32–44 px mobile where space allows.
- **Identity:** 24–36 px desktop, 22–30 px mobile.
- **Primary exact metric:** 28–48 px depending on context.
- **Comparison / section heading:** 18–24 px.
- **Supporting body:** 13–16 px.
- **Evidence labels / provenance:** 10–12 px.

Rules:
- small uppercase labels are supporting texture, never the main content;
- no important insight should require reading multiple 9–11 px labels;
- exact values use tabular numerals;
- avoid using bold everywhere; reserve weight for hierarchy.

## 4. Spatial rhythm

Default spacing values are presentation guidance, not model logic:
- 8 px micro gap;
- 16 px component gap;
- 24–32 px section gap;
- 48–72 px major section transition;
- 72–120 px hero/stage breathing room on wide desktop when the surface can afford it.

Rules:
- negative space is an information tool;
- nested borders indicate nested interaction, not mere layout;
- repeated 12–18 px rounded cards are a failure mode when they flatten hierarchy;
- no more than one visually dominant bordered surface in the first read unless the workflow itself is intrinsically bilateral.

## 5. Identity system

Identity uses only governed or directly available assets.

### Franchise identity
- canonical display name;
- “Your franchise” / counterparty / league role;
- current calculated state when authoritative;
- optionally one governed signature fact such as strongest position or pick-capital state.

### Player identity
- full name;
- position;
- age when available;
- team/roster role where available;
- canonical player image only if an authorized source exists. Do not invent headshots.

### Owner identity
- canonical owner/display name;
- managed-team association;
- evidence-coverage context;
- observed Behavioral history only; no personality label without support.

Derived initials/monograms may be used as typographic placeholders because they derive directly from canonical names, but they may not imply an official logo.

## 6. Canonical data-visualization primitives

### Rank Band
Purpose: show league-relative position quickly.
- exact rank + population always visible;
- benchmark or league average marked;
- underlying exact index/value available on tap or adjacent label;
- no new score.

### Delta Band
Purpose: show signed before/after or scenario change.
- zero-centered;
- exact signed value always visible;
- same-unit comparisons may normalize visual length for legibility;
- normalization must be disclosed and may not be interpreted as model materiality.

### Probability Shift
Purpose: show governed probability level or before/after change.
- absolute probability may use a ring or filled arc;
- change uses a Delta Band or paired marker;
- horizon/denominator must be explicit.

### Risk Band
Purpose: show fragility or exposure.
- exact governed risk diagnostic visible;
- direction/benchmark explicit;
- do not invent “safe/danger” thresholds unless upstream authority provides them.

### Trajectory Strip
Purpose: show age, draft capital or horizon movement over time.
- horizontal time axis;
- sparse annotated milestones;
- no fake interpolation between unavailable observations.

### Distribution
Purpose: show governed uncertainty.
- median/mean and interval/quantiles if available;
- do not draw distributions from only a point estimate.

### Atlas / Heat Map
Purpose: make league structure visually discoverable.
- each cell corresponds to a governed coordinate such as position rank/strength, age, pick capital or fragility;
- color/area encode only declared dimensions;
- exact values remain accessible on focus/tap;
- no hidden composite “power” score.

### Package Comparison
Purpose: compare assets and bilateral consequence.
- side-by-side identity;
- one clear exchange direction;
- exact FSFFL/Market evidence remains separate from Decision outcome;
- package economics, Simulation consequence and Behavioral evidence retain separate lanes.

## 7. Action language

Presentation may not invent a recommendation.

Rules:
- if Decision returns an action/disposition, use that language as the action anchor;
- if Search returns discovery only, use “investigate,” “open,” “compare,” or “work in Trade Center,” not “buy/sell/accept”;
- if evidence is incomplete, the primary action may be “simulate,” “review evidence,” or “choose a package”;
- acceptance probability is never synthesized from Behavioral history.

## 8. Progressive disclosure

First scan should usually contain:
- identity;
- one dominant takeaway;
- one primary comparison;
- one risk/opportunity/context rail;
- one primary action.

Second layer:
- supporting exact metrics;
- package/roster detail;
- counterparties;
- alternatives;
- uncertainty.

Third layer:
- methods;
- evidence/provenance;
- exact tables;
- model/source/version details.

## 9. Interaction specification

Hover/focus/tap:
- reveals exact values and labels;
- highlights related league/player/team objects;
- never changes analytical meaning.

Selection:
- establishes the object being investigated;
- persists context across related surfaces where the existing product architecture supports it.

Drill-down:
- expands in place when the user benefits from continuity;
- opens a dedicated surface when the task changes from scan to decision.

Motion:
- restrained and functional;
- emphasize transition/focus, not decoration;
- honor reduced-motion preferences.

## 10. Mobile composition

Mobile is a different reading order, not a shrunken desktop.

Rules:
- stage first;
- identity before metadata;
- bilateral desktop columns become ordered vertical lanes;
- tables become ranked bands, accordion detail, or explicit horizontal exploration only when the horizontal relationship itself is essential;
- primary action remains reachable without scrolling through evidence;
- tap targets at least 44 px where practical;
- long explanatory copy moves below the primary visual.

## 11. Cross-surface consistency and intentional identity

Shared across surfaces:
- type hierarchy;
- identity rules;
- status/risk/action semantics;
- Rank / Delta / Probability / Risk / Trajectory / Distribution grammar;
- evidence drawer;
- mobile scan pattern.

Intentional surface identity:
- Home: command / priority;
- Franchise: diagnosis / roster anatomy;
- League: atlas / landscape;
- Market: discovery / opportunity flow;
- Trade Center: bilateral decision / consequence;
- Owner Intelligence: dossier / observed-pattern story.

Shared grammar must not make every page look identical.

## 12. Transitional versus canonical

The PR #159 Delta Band semantics are accepted: bilateral, zero-centered, exact-value-preserving, no grade. Its compact render remains **transitional**.

The prior PR #160 light editorial reference is retained as structural learning—dominant decision state, identity, breathing room, bilateral consequence storytelling, exact evidence, and methods below the fold—but its light aesthetic is **not** the approved brand target.

The approved visual destination is the premium dark, mobile-first product family described above. Canonical authority comes from this design system plus management-approved rendered reference compositions, not from any one existing CSS file.

## 13. Product validation gate

A new surface or major recomposition is not “done” because its data exists or tests pass. It must also demonstrate:
- main truth perceived in 2–3 seconds;
- dominant visual hierarchy;
- materially reduced reading burden;
- consumer-facing identity;
- graphical communication where useful;
- exact evidence still available;
- clear next interaction;
- intentional mobile composition;
- live-beta validation when authenticated inspection is available.
