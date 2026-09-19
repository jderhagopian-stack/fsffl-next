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

The project should not optimize for the number of models, dashboards, cards, or research layers completed. It should optimize for durable user value.

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

Every major surface must answer a distinct owner question and earn its place.

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

## Team/Owner-Adjusted Value
Bring the existing governed contract into practical use only when evidence supports it:
- universal Market Value remains immutable baseline truth;
- contextual deltas are bounded and additive;
- team need and residual owner preference enter once;
- uncertainty and provenance remain inspectable;
- no double counting through Decision Utility;
- no hidden default coefficient simply because a concept “should matter.”

### Phase 3 exit gate
Core product work is not done because the screens look better. Before moving primary product focus to major new historical experiences, verify that:
- each core surface answers a clearly different question;
- a user can understand the primary view without reading model documentation;
- advanced provenance/method detail is available but secondary;
- the live beta produces recognizable, useful Behavioral owner insights where evidence exists;
- Trade Finder regularly surfaces credible acquisition paths beyond trivial Cardinal matches;
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
3. Run the coordinated Core Product Usefulness + Existing Intelligence Online phase.
4. Build Historical Intelligence after the core live beta is demonstrably useful.
5. Build League History, Lore, Franchise Timeline, and personality experiences.
6. Build FSFFL Publications as polished narrative products over governed outputs.
7. Expand Analytics / investigation surfaces.
8. Add scenario / future experiences.
9. Continue Product Validation, Performance, Forecast/Simulation validation, and Parameter Recalibration across all phases.
10. Grow the longer-term FSFFL Evidence Warehouse and proprietary intelligence flywheel.
11. Complete commercialization hardening before broad launch.

---

# Maintenance rule

Update this document whenever a material roadmap decision is made.

Future continuation prompts and new development chats should read this file before creating a new priority order.

When a phase materially advances, update its current status and exit-gate evidence rather than merely marking the phase “done.”