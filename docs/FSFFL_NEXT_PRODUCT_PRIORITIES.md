# FSFFL NEXT — Living Product Development Priorities

This document is the canonical product-development roadmap for FSFFL NEXT. It is intended to survive across chats, branches, and workstreams so priorities, sequencing, and definitions of done do not get lost.

## Product goal

Move FSFFL NEXT from a technically sophisticated private beta into a stable, useful, differentiated, fun, commercially viable fantasy-football product.

The product should combine:
- serious decision intelligence;
- persistent league context;
- distinct, intuitive product surfaces;
- league history, personality, and storytelling;
- polished recurring reports/publications;
- governed model improvement over time.

## Operating principle

The project should not optimize for the number of models, dashboards, cards, PRs, or research layers completed. It should optimize for durable user value.

Every major development phase must answer two questions:
1. Did we build the capability correctly?
2. Did the resulting product become materially more useful, understandable, fast, or engaging for a real owner?

Model sophistication and product usefulness advance together. A backend capability is not considered fully productized until its governed output is exposed in a clear experience, tested in the live beta, and shown to improve a real user task.

---

# PHASE 1 — Private-beta stability and runtime reliability — NOW

Finish the current Render/mobile/runtime stabilization before expanding product scope.

Immediate requirements:
- reliable league connection on mobile Safari;
- no black-screen / touch-freeze failures;
- no duplicate connect jobs or polling loops;
- Opportunities must load without route-level render loops or unnecessary deep Decision work;
- long-running work must not depend on a fragile browser request;
- clear loading / available / stale / unavailable states;
- no regressions to Forecast, Value, Decision, Search, Simulation, or Behavioral authority boundaries.

Current direction already implemented or underway:
- background hosted league connection;
- single-flight connect behavior;
- durable runtime checkpoints;
- restore-first hosted league refresh;
- incremental Sleeper change probes;
- durable Behavioral history;
- reduced startup work and route-level mobile stabilization.

### Phase 1 exit gate
Do not declare runtime stabilization complete until the live beta demonstrates:
- repeated mobile reconnects without black-screen or touch-freeze failure;
- no duplicate hosted connect work for one user action;
- restored league state is usable before expensive provider refresh finishes;
- Opportunities can open and become useful without automatically launching unnecessary deep Decision work;
- failures degrade into explicit stale/unavailable states rather than broken UI;
- measured user-perceived latency is captured for connect, restore, Opportunity load, and explicit deep analysis.

---

# PHASE 2 — Persistent League State & Incremental Sync — HIGH PRIORITY

Treat persistence as core product architecture, not merely a performance optimization.

Desired user experience:
- first connection performs expensive provider ingest and canonicalization;
- subsequent visits restore the stored league immediately;
- FSFFL checks Sleeper and other providers in the background for changes since last sync;
- unchanged historical seasons are not repeatedly reacquired or reconstructed;
- only materially changed facts invalidate dependent artifacts;
- the existing product remains usable while sync occurs (stale-while-revalidate);
- settings eventually include an explicit control for deleting stored league data.

Architecture goals:
- durable canonical provider facts;
- durable historical / point-in-time state;
- durable current league state;
- durable Behavioral evidence where appropriate;
- versioned derived artifacts with provenance;
- material-state fingerprints and selective invalidation;
- incremental recomputation instead of full rebuilds;
- provider synchronization cursors / delta checks where available;
- safe fallback when a provider does not expose true deltas.

### Phase 2 exit gate
Persistence is not finished merely because data is stored. Before moving primary focus away from this phase, verify that:
- a previously connected league can be restored after hosted restart without a new full ingest;
- unchanged Sleeper state skips unnecessary full reacquisition;
- changed state invalidates only dependent artifacts where practical;
- current league, historical state, Behavioral evidence, and derived artifacts survive the lifecycle they are intended to survive;
- stale-while-revalidate behavior is visible and understandable in product surfaces;
- repeated visits are materially faster than first connection;
- persistence failure never silently corrupts or replaces authoritative model truth.

---

# PHASE 3 — Core Product Usefulness + Existing Intelligence Online — HIGH PRIORITY

Treat UI/product work and bringing existing model capabilities online as one coordinated program rather than two sequential silos.

The current beta should become substantially more useful before the project opens many new research families.

The North Star remains **SEE → UNDERSTAND → INTERACT → DRILL DEEPER**. The product should feel simple, visual, modern, mobile-first, and consumer-friendly on the surface while preserving analytical depth underneath.

Every major surface must answer a distinct owner question and earn its place. Do not solve information architecture problems by simply adding more cards, charts, or jargon.

## Product/UI transformation remains a first-class Phase 3 goal

The aesthetic, organizational, and interaction redesign continues in parallel with model/intelligence work.

Default product behavior should emphasize:
- graphical comparison and scanning before prose;
- obvious numerical hierarchy;
- player/team identity;
- compact charts, bands, bars, rings/gauges, heat maps, before/after comparisons, and distributions where they improve understanding;
- fewer repetitive cards and long mobile lists;
- intentional mobile layouts rather than compressed desktop layouts;
- concise first-read interpretation with deeper methodology and provenance on drill-down;
- consumer language by default, model terminology secondarily;
- clear action paths from insight to deeper analysis.

The canonical North Star product directive remains authoritative for visual and interaction direction. Intelligence improvements must strengthen that experience, not postpone it.

## Home — “What should I care about right now?”
Focus on prioritized, actionable changes rather than generic summary cards.

Candidate jobs:
- strongest current opportunity;
- biggest roster risk;
- important league movement;
- what materially changed since the last visit;
- shortcuts into deeper surfaces.

## My Team — “What is actually driving my franchise?”
Focus on roster diagnosis:
- optimized starting-lineup strengths and weaknesses;
- bench/depth quality;
- fragility and replacement exposure;
- age/value-duration profile;
- draft capital;
- position ranks and upgrade priorities;
- actual roster-alternative context where governed.

## League Comparison — “How do these teams differ?”
Focus on comparative identity rather than repeated totals:
- contender/rebuilder profile;
- young/old;
- deep/top-heavy;
- positional wealth and need;
- pick-rich/pick-poor;
- meaningful league-relative strengths.

## Opportunities / Trade Finder — “Where is there something worth doing?”
Continue improving:
- realistic price discovery and negotiation frontiers;
- fewer theoretical/unrealistic packages crowding results;
- premium-target access;
- realistic counter generation;
- bilateral utility calibration;
- strategic-posture search lens separate from calculated competitive state;
- owner-specific intelligence only when mature enough to justify Search use;
- caching and search-speed improvements;
- explicit distinction between closest market match and strongest FSFFL opportunity.

## Trade Center — “What happens if I make this specific deal?”
Focus on a concrete bilateral decision:
- concise primary decision summary;
- counterparty perspective;
- roster needs before/after;
- lineup and Simulation consequences;
- package economics;
- realistic alternatives/counters;
- originator context;
- Wins Above Replacement / actual roster alternative where governed;
- Behavioral proposal fit as evidence, not fabricated acceptance probability.

## Behavioral Intelligence — “How should I understand and approach this owner?”
Productionize the governed owner-intelligence stack:
- observed history;
- context-controlled position preferences;
- package-shape tendencies;
- confidence, coverage, recency, and stability kept visible and separate;
- pick-vs-player tendencies;
- counterparty / negotiation tendencies where supported;
- Team/Owner-Adjusted Value context where governed;
- proposal fit routed to Trade Center;
- no fabricated rejection evidence or acceptance odds.

## Canonical value architecture — three distinct value questions

FSFFL should not collapse all player value into one universal number. The product should distinguish three separate economic coordinates:

1. **Broad Market Value — “What does the broader dynasty market think this asset is worth?”**
   - external consensus / exchange benchmark;
   - format-aware and evidence-backed;
   - reflects observed market pricing and sentiment;
   - remains distinct from FSFFL's own fundamental estimate.

2. **FSFFL Intrinsic Value — “What does FSFFL think this asset is actually worth?”**
   - independent multi-year football/economic value;
   - informed by Forecast-owned future production, career trajectory, development/decline, attrition, uncertainty, longevity, replacement-adjusted surplus, and defensible league-level scarcity/opportunity cost;
   - must remain meaningfully independent from Market Value;
   - may disagree with broader consensus by design;
   - team-specific roster need does not belong inside this coordinate.

3. **League Market Value — “What does this specific league appear to think this asset is worth?”**
   - league-specific exchange coordinate inferred from actual league transactions and governed league-level evidence;
   - may reflect positional premiums, pick appetite, package preferences, consolidation behavior, scarcity, liquidity, and recurring league pricing patterns;
   - must not be confused with one specific owner's preference or one team's need.

**Team Utility remains downstream and separate:** “What is this asset worth to this particular franchise in this situation?”

Decision and Search should eventually exploit disagreement among Broad Market Value, FSFFL Intrinsic Value, League Market Value, and Team Utility rather than collapsing them into an opaque master score.

Examples of useful disagreement:
- Intrinsic > Broad Market > League Market can indicate a potential league-specific buy opportunity.
- League Market > Broad Market > Intrinsic can indicate a potential sell-high environment.
- Team Utility can then determine whether that market opportunity actually fits the focal franchise.

## Decision-intelligence sequence inside Phase 3

The current Decision/Value work should follow this sequence so the reason for the intrinsic-value research is not lost:

### 1. Separate Decision dimensions and fail closed — foundation completed
- near-term competitive impact and long-term franchise value remain separate dimensions;
- market economics remain separate from both;
- incomplete evidence must not masquerade as a comprehensive final trade disposition;
- Simulation-backed analysis is still incomplete when required Value evidence is absent.

### 2. FSFFL Intrinsic Value — current research focus
- draft PR #131 is the canonical research workstream;
- existing affine mapping is a control, not presumed truth;
- benchmark transparent multi-year replacement-adjusted surplus **Model A** using strict chronological reconstruction;
- compare candidate replacement definitions empirically;
- preserve uncertainty, provenance, and market independence;
- richer hybrid **Model B** remains blocked unless Model A leaves a demonstrated, identifiable residual problem;
- no production promotion without evidence-supported promotion criteria.

### 3. Strategic conflict resolution — next after intrinsic foundation
Interpret cases where a deal helps now but hurts long-term value, or vice versa.
- calculated competitive state and optional owner horizon may shape interpretation;
- strategic posture remains owner agency, not a replacement for calculated state;
- do not create a crude contender multiplier or opaque weighted master score;
- outputs should be explainable in plain English, e.g. “strong near-term gain, moderate long-term loss.”

### 4. Bounded Trade Grades
After the underlying dimensions are mature enough:
- provide user-friendly bounded grades/ranges with visible confidence/evidence completeness;
- grades summarize authoritative Decision dimensions; they do not create new model truth;
- uncertainty should widen ranges/lower confidence rather than erase useful guidance.

### 5. Directional Owner Intelligence
Use actual Behavioral evidence to improve negotiation guidance:
- historical owner tendencies may inform approach, package shape, and proposal fit;
- avoid fabricated acceptance probabilities;
- confidence, recency, coverage, and stability remain visible.

### 6. League Market Value
After the Intrinsic Value foundation is sufficiently governed:
- build a league-level pricing coordinate using historical league transactions and other admissible league evidence;
- separate persistent league pricing behavior from one owner's idiosyncratic preference;
- preserve Broad Market Value and Intrinsic Value as independent reference coordinates.

### 7. Search/Decision exploitation
Trade Finder and Trade Center should use the value-coordinate disagreements to identify and explain opportunities:
- buy-low / sell-high candidates;
- league-specific mispricing;
- premium targets where FSFFL believes market/league price understates football value;
- overvalued assets where league pricing materially exceeds FSFFL intrinsic value;
- only then apply Team Utility and bilateral Decision consequences.

## Team/Owner-Adjusted Value
Bring the existing governed contract into practical use only when evidence supports it:
- universal Market Value remains immutable baseline truth;
- contextual deltas are bounded and additive;
- team need and residual owner preference enter once;
- uncertainty and provenance remain inspectable;
- no double counting through Decision Utility;
- no hidden default coefficient simply because a concept “should matter.”

### Phase 3 exit gate
Core product work is not done because the screens look better or because backend models exist. Before moving primary product focus to major new historical experiences, verify that:
- each core surface answers a clearly different question;
- the default experience is visually understandable without reading model documentation;
- the North Star visual/interaction grammar is recognizably present across major surfaces;
- advanced provenance/method detail is available but secondary;
- Broad Market, FSFFL Intrinsic, League Market, and Team Utility are conceptually and technically separated where available;
- the live beta produces recognizable, useful Behavioral owner insights where evidence exists;
- Trade Finder regularly surfaces credible acquisition paths beyond trivial cardinal matches;
- Trade Center explains why a deal helps/hurts each side in plain English;
- repeated dashboard cards and redundant metrics have been materially reduced;
- mobile layouts are functional and intentionally designed, not merely compressed desktop layouts;
- latency for common tasks is acceptable for repeated use;
- at least several real beta sessions produce a documented “useful discovery” rather than only technically correct output.

---

# CONTINUOUS TRACK A — Product Validation & User Feedback

This track runs through every phase.

Do not evaluate success only through architecture tests and CI. Repeatedly test the live product against real owner questions.

For each meaningful product slice, ask:
- Did the user understand what the screen meant without explanation?
- Did it reveal something non-obvious or actionable?
- Did the recommendation feel credible?
- Did the user want to drill deeper?
- Was anything confusing, repetitive, sterile, or overly technical?
- Was it fast enough to use voluntarily rather than merely tolerate?
- Did the result align with known league reality when used as validation data?

Maintain a lightweight validation log for material beta findings so the same UX/model issues are not rediscovered across chats.

A feature that passes tests but repeatedly fails these questions is not finished.

---

# CONTINUOUS TRACK B — Performance & Commercial Latency

Performance is a commercial requirement and runs alongside the roadmap.

Direction:
- measure full user-perceived latency;
- instrument major phases before guessing at bottlenecks;
- reuse material-state artifacts;
- cache repeat analyses;
- avoid unnecessary recomputation;
- use server-owned background jobs for long work;
- lazy-load deep surfaces;
- run cheap filters before expensive Simulation/Decision work;
- progressively expose available/loading/stale states;
- parallelize independent provider work where safe;
- optimize without reducing model fidelity.

Current unresolved commercial concern:
- fresh high-fidelity Simulation remains expensive, including 50,000-run scenarios;
- optimize the Simulation kernel/runtime, caching, reuse, orchestration, and persistence without reducing requested simulation fidelity;
- exact-repeat reuse is useful but does not eliminate the need to reduce genuinely fresh analysis latency.

Performance work should target measured bottlenecks rather than broad speculative rewrites.

---

# CONTINUOUS TRACK C — Forecast / Simulation Validation

Forecast and Simulation remain authoritative for their existing outputs, but their behavior must be empirically observable.

Current focus includes diagnosing compressed expected-win distributions by separating:
- between-team scoring-mean spread;
- ordinary weekly scoring noise;
- fallback/projection coverage;
- expected-win spread.

Do not “fix” compressed results with arbitrary presentation multipliers. Correct the earliest authoritative layer where evidence shows the distortion originates.

---

# CONTINUOUS TRACK D — Parameter Provenance & Dynamic Recalibration

The end-state is not a pile of static coefficients.

Every material parameter should have:
- provenance;
- evidence quality;
- reason for existence;
- empirical estimation path where appropriate;
- validation and promotion criteria;
- uncertainty / bounded prior when evidence is incomplete;
- future update mode.

Do not replace parameters solely by intuition, and do not force known effects to zero solely because perfect coefficients are unavailable.

Avoid opening broad new parameter-research families when the current product phase has unresolved high-impact usability or reliability problems, unless the research is needed to fix one of those problems.

The intrinsic-value work in PR #131 is justified within Phase 3 because it repairs a material missing Decision dimension and directly supports Trade Finder / Trade Center usefulness.

---

# PHASE 4 — Historical Intelligence

Build historical features as both serious analysis and an engaging explanation of franchise history.

## Historical Trade Grader
Two distinct outputs:
1. Point-in-time Decision Grade — was the decision good using only information reasonably knowable then?
2. Retrospective Outcome — what actually happened afterward, clearly separated from original decision quality.

Needs:
- point-in-time state reconstruction;
- historical projections / value / player career state;
- historical pick reconstruction;
- competitive state and roster context at the time;
- uncertainty and evidence completeness;
- strict leakage prevention;
- polished reports and API contracts.

The 2022 startup draft in the user’s league must not be treated as a normal trade/preference sample because picks were used to nominate players in a live-action draft.

## Historical Pick Coordinate
- point-in-time pick values;
- no current pick values used as historical truth;
- no hidden restricted third-party dependency;
- no new valuation channel.

### Phase 4 exit gate
Historical Intelligence should demonstrate:
- strict leakage tests on known examples;
- explicit incomplete-evidence states;
- PIT grade and retrospective outcome never collapsed into one score;
- historical pick uncertainty surfaced rather than hidden;
- results that can be explained in plain English with evidence provenance;
- league-agnostic contracts suitable for later UI/report reuse.

---

# PHASE 5 — League History, Lore & Personality

Historical product surfaces should feel like a league museum / record book rather than a dry archive.

Potential experiences:
- championship history;
- all-time standings and records;
- longest winning streaks;
- highest-scoring weeks;
- biggest blowouts;
- playoff heartbreaks and upsets;
- rivalries and owner-vs-owner records;
- dynasty eras;
- best team never to win;
- biggest rebuilds;
- trade and draft superlatives;
- franchise timelines;
- season storylines;
- notable anomalies and league-specific lore.

All claims must remain grounded in governed historical data and avoid unsupported causal storytelling.

This phase should connect current state, historical causality, counterfactual exploration, and future decisions into a coherent franchise experience rather than isolated archive pages.

---

# PHASE 6 — FSFFL Publications / Periodical-Style Reports

Revive and expand polished reports as a first-class product experience.

Candidate publications:
- Preseason Preview;
- Weekly League Report;
- Trade Deadline Special;
- Playoff Preview;
- Draft Guide;
- Midseason Awards;
- Year in Review;
- Record Book;
- Franchise Retrospective;
- League Almanac.

Report standards:
- polished, readable, shareable presentation;
- plain-English narrative;
- charts/tables/graphs only where useful;
- league/team agnostic architecture;
- originator and bilateral context for trades;
- needs before/after;
- age, rank, projected PPG where relevant;
- realistic alternatives/counters;
- Wins Above Replacement where governed;
- no “estimated wins above average starter” metric.

Reports should synthesize authoritative outputs; they do not create model truth.

---

# PHASE 7 — Analytics / Investigation Surfaces

Build the read-only analyst layer after core product surfaces and historical foundations are solid.

Includes:
- Analytics Terminal;
- trade-partner intelligence;
- FSFFL-vs-market rankings;
- player/team drill-downs;
- richer heat maps;
- team-centric value views;
- Decision Utility / Inspector support;
- cross-league analytics;
- mobile adaptation.

The three-value architecture should become a major Analytics lens here, including Broad Market vs FSFFL Intrinsic vs League Market rankings and residuals.

The terminal presents intelligence; it does not create model truth.

---

# PHASE 8 — Scenario / Future Product Capabilities

Later-stage product experiences:
- What-If / Alternate History;
- governed historical branching;
- scenario simulations;
- richer future-state exploration;
- deferred 3-year dynasty positional outlook.

The 3-year dynasty position outlook remains intentionally deferred until more urgent product work is complete.

---

# LONGER-TERM STRATEGIC TRACK — FSFFL Evidence Warehouse

Use governed, de-identified historical league evidence to improve FSFFL’s own models and reduce dependence on third-party intelligence where appropriate.

Potential flywheel:
`League ingest → normalized historical evidence → better calibration / valuations / projections → better product → more league data → stronger models`

Possible learned evidence includes:
- real trade clearing prices;
- package economics;
- positional scarcity by league structure;
- pick pricing over time;
- consolidation premiums;
- contender/rebuilder behavior;
- draft outcomes;
- roster trajectories;
- realized fantasy outcomes;
- league-specific pricing tendencies;
- eventual acceptance / negotiation priors where valid observed evidence exists.

Governance:
- operational customer data and generalized model-training/calibration eligibility remain separate concepts;
- use de-identification/minimization where possible;
- preserve provenance and model/dataset versions;
- provide appropriate privacy and deletion controls;
- do not assume service storage automatically grants generalized training rights.

---

# COMMERCIALIZATION HARDENING — BEFORE BROAD LAUNCH

Before broad launch:
- validate league/team agnosticism;
- test unusual scoring/lineup/roster edge cases;
- support multi-league usage;
- improve onboarding;
- provide permissions/privacy/data deletion controls;
- maintain explainability;
- harden failure states;
- improve source resilience and freshness handling;
- establish production monitoring/observability;
- address account/billing/business functionality after core usefulness is proven.

---

# Standing architecture and governance

Canonical pipeline:
`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Non-negotiables:
- Presentation never calculates model truth.
- Search never invents Value/Decision truth.
- Behavioral Intelligence does not mutate universal Market Value directly.
- Broad Market Value, FSFFL Intrinsic Value, League Market Value, and Team Utility remain distinct coordinates/decision inputs and must not be collapsed into one hidden universal score.
- League Market Value describes league-level exchange behavior; owner-specific preference belongs in Behavioral / owner-adjusted context.
- Simulation owns stochastic competitive outcomes.
- Decision owns bilateral consequences, legality, package economics, materiality, and disposition.
- Overlapping signals must be controlled/residualized/attributed once.
- Strategic posture / owner agency is distinct from calculated competitive state.
- User-specific league examples are validation data, never product specification.
- All product logic remains league-agnostic and team-agnostic.
- Sophisticated backend; plain-language outputs.
- No opaque master/composite score should be introduced merely to simplify product presentation.
- Missing or weak evidence should be represented as unavailable/uncertain rather than fabricated precision.

---

# Workstream discipline

Parallel work is allowed, but fragmentation is not a goal.

Rules:
- before modification, re-fetch exact current main and inspect exact files being changed;
- use separate branches/PRs and preserve newer parallel work;
- do not open a new adjacent research workstream simply because it is interesting if a higher-priority live-product problem remains unresolved;
- a workstream should define its user/product outcome and its exit gate before expanding scope;
- after meaningful slices, run focused tests and full CI as appropriate;
- deployment should use an exact validated merged SHA;
- maintenance/documentation-only PRs should not interrupt active application work unless they conflict with the same file.

---

# Current recommended phase order

1. Finish private-beta/runtime stabilization.
2. Finish Persistent League State & Incremental Sync and prove restore/revalidation behavior.
3. Continue the coordinated Phase 3 program: North Star UI/product transformation plus existing intelligence online.
4. Within Phase 3 Decision intelligence: complete Intrinsic Value Model A research/benchmarking, then strategic conflict resolution, bounded Trade Grades, directional Owner Intelligence, and League Market Value.
5. Connect Broad Market / Intrinsic / League Market disagreement to Trade Finder, Trade Center, and Team Utility while continuing commercial-latency work.
6. Build Historical Intelligence after the core live beta is demonstrably useful.
7. Build League History, Lore, Franchise Timeline, and personality experiences.
8. Build FSFFL Publications as polished narrative products over governed outputs.
9. Expand Analytics / investigation surfaces.
10. Add scenario / future experiences.
11. Continue Product Validation, Performance, Forecast/Simulation validation, and Parameter Recalibration across all phases.
12. Grow the longer-term FSFFL Evidence Warehouse and proprietary intelligence flywheel.
13. Complete commercialization hardening before broad launch.

---

# Maintenance rule

Update this document whenever a material roadmap decision is made.

Future continuation prompts and new development chats should read this file before creating a new priority order.

When a phase materially advances, update its current status and exit-gate evidence rather than merely marking the phase “done.”
