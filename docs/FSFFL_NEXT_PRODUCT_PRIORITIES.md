# FSFFL NEXT — Living Product Development Priorities

This document is the canonical product-development priority list for FSFFL NEXT. It is intended to survive across chats, branches, and workstreams so planned work does not get lost.

## Product goal

Move FSFFL NEXT from a technically sophisticated private beta into a stable, useful, differentiated, fun, commercially viable fantasy-football product.

The product should combine:
- serious decision intelligence;
- persistent league context;
- distinct, intuitive product surfaces;
- league history, personality, and storytelling;
- polished recurring reports/publications;
- governed model improvement over time.

## Priority 1 — Private-beta stability and runtime reliability — NOW

Finish the current Render/mobile/runtime stabilization before expanding scope.

Immediate requirements:
- reliable league connection on mobile Safari;
- no black-screen / touch-freeze failures;
- no duplicate connect jobs or polling loops;
- Opportunities must load without route-level render loops or unnecessary deep Decision work;
- long-running work must not depend on a fragile browser request;
- clear loading / available / stale / unavailable states;
- no regressions to Forecast, Value, Decision, Search, Simulation, or Behavioral authority boundaries.

Current baseline as of 2026-09-09:
- main: `a8527e1580f48bfded7749d76e98f43c4f4e579e`
- PR #56: durable league sessions + single-flight connect merged and live.

## Priority 2 — Persistent League State & Incremental Sync — NEAR TERM / HIGH PRIORITY

Treat persistence as core product architecture, not merely a performance optimization.

Desired user experience:
- first connection performs the expensive provider ingest and canonicalization;
- subsequent visits restore the stored league immediately;
- FSFFL then checks Sleeper/other providers in the background for changes since last sync;
- unchanged historical seasons are not repeatedly reacquired or reconstructed;
- only changed current-season facts invalidate dependent artifacts;
- existing product remains usable while sync occurs (stale-while-revalidate);
- settings include an explicit control for deleting stored league data.

Architecture goals:
- durable canonical provider facts;
- durable historical / point-in-time state;
- durable current league state;
- versioned derived artifacts with provenance;
- material-state fingerprints and selective invalidation;
- incremental recomputation instead of full rebuilds;
- provider synchronization cursors / delta checks where available;
- safe fallback when a provider does not expose true deltas.

## Priority 3 — Core product usefulness and UI experience — HIGH PRIORITY

The current beta is too rudimentary and sterile. Improve the experience without turning UI into decorative clutter.

Every major surface must answer a distinct user question and earn its place.

Core surfaces to bring to a polished usable state:
- Home;
- My Team;
- League Comparison;
- Trade Center;
- Opportunities / Trade Finder;
- Behavioral Intelligence.

Experience goals:
- clearer hierarchy and navigation;
- mobile-first layouts;
- richer drill-downs;
- less technical jargon in primary views;
- model methods/provenance available in secondary detail, not dominating the UI;
- better team branding and league-specific context;
- more personality, discovery, and fun;
- richer loading, empty, success, and stale states;
- avoid repeated generic dashboard cards.

Do **not** solve this by simply adding more cards or charts.

## Priority 4 — Finish bringing existing model capabilities fully online

A large amount of backend capability already exists but is not yet fully exposed in the product.

### Behavioral Intelligence
- production runtime point-in-time coverage;
- owner preference evidence with uncertainty;
- package-shape tendencies;
- better recency/stability handling;
- pick-vs-player tendencies;
- counterparty / negotiation behavior where supported;
- no fabricated rejection evidence.

### Team/Owner-Adjusted Value
- empirically defensible bounded mapping;
- team need + residual owner preference integration;
- uncertainty and provenance;
- no mutation of universal Market Value;
- no double counting through Decision Utility.

### Trade Finder / Opportunity Engine
- more realistic price discovery and negotiation frontiers;
- reduce theoretical/unrealistic packages crowding results;
- premium-target access;
- realistic counter generation;
- bilateral utility calibration;
- owner-specific intelligence later;
- caching and search-speed improvements;
- maintain separation between strategic posture and calculated competitive state.

### Decision / Simulation product integration
- concise main decision summaries;
- simulation effects reflected correctly in primary UI;
- counterparty perspective;
- realistic alternatives;
- needs before/after;
- actual roster alternative / wins-above-replacement context where governed.

## Priority 5 — Historical Intelligence

Build historical features as both serious analysis and an engaging look back at league history.

### Historical Trade Grader
Two distinct outputs:
1. Point-in-time Decision Grade — was the decision good using only information knowable then?
2. Retrospective Outcome — what happened afterward, clearly separated from the original decision quality.

Needs:
- point-in-time state reconstruction;
- historical projections / value / player career state;
- historical pick reconstruction;
- uncertainty and evidence completeness;
- strict leakage prevention;
- polished reports and API contracts.

Note: the 2022 startup draft in the user's league must not be treated as a normal trade/preference sample because picks were used to nominate players in a live-action draft.

### Historical Pick Coordinate
- point-in-time pick values;
- no current pick values used as historical truth;
- no hidden restricted third-party dependency;
- no new valuation channel.

## Priority 6 — League History, Lore & Personality

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

All such claims must remain grounded in governed historical data and avoid unsupported causal storytelling.

## Priority 7 — FSFFL Publications / Periodical-Style Reports

Revive and expand the polished report concept from the original model as a first-class product experience.

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

## Priority 8 — Analytics / Investigation Surfaces

Build out the read-only analyst layer after core product surfaces and historical foundations are solid.

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

## Priority 9 — Scenario / Future Product Capabilities

Later-stage product experiences:
- What-If / Alternate History;
- governed historical branching;
- scenario simulations;
- richer future-state exploration;
- deferred 3-year dynasty positional outlook.

The 3-year dynasty position outlook is intentionally deferred until more urgent product work is complete.

## Priority 10 — Performance & Commercial Latency — CONTINUOUS TRACK

Performance is a commercial requirement and runs alongside the roadmap.

Already established direction:
- measure full user-perceived latency;
- reuse material-state artifacts;
- cache repeat analyses;
- avoid unnecessary recomputation;
- use short server-owned background jobs for long work;
- lazy-load deep surfaces;
- cheap client-side filtering;
- progressive available/loading/stale states;
- monitor production behavior;
- optimize without reducing model fidelity.

## Priority 11 — Parameter Provenance & Dynamic Recalibration — CONTINUOUS RESEARCH TRACK

The end-state is not a pile of static coefficients.

Every material parameter should have:
- provenance;
- evidence quality;
- reason for existence;
- empirical estimation path where appropriate;
- validation and promotion criteria;
- uncertainty / bounded prior when evidence is incomplete;
- future update mode.

Do not replace parameters solely by intuition, and do not force known effects to zero simply because perfect coefficients are unavailable.

## Priority 12 — Persistent League Intelligence → FSFFL Evidence Warehouse — LONGER TERM

Longer-term strategic objective: use governed, de-identified historical league evidence to improve FSFFL's own models and reduce dependence on third-party intelligence.

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
- actual realized fantasy outcomes;
- eventual acceptance / negotiation priors where valid evidence exists.

Important governance:
- operational customer data and generalized model-training/calibration eligibility must remain separate concepts;
- use de-identification/minimization where possible;
- preserve provenance and model/dataset versions;
- provide appropriate user privacy/data controls;
- do not assume service storage automatically grants generalized training rights.

## Priority 13 — Commercialization Hardening

Before broad launch:
- validate league/team agnosticism;
- unusual scoring/lineup/roster edge cases;
- multi-league support;
- onboarding;
- permissions/privacy/data deletion;
- explainability;
- robust failure states;
- source resilience and data freshness;
- monitoring/observability;
- account/billing/business functionality later, after core usefulness is proven.

## Standing architecture and governance

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

## Current recommended phase order

1. Stabilize the private beta / Render runtime.
2. Implement Persistent League State & Incremental Sync.
3. De-sterilize and complete the core product surfaces.
4. Bring existing Behavioral / Value / Trade / Decision capabilities fully online.
5. Build Historical Intelligence.
6. Build League History & Lore and FSFFL Publications.
7. Expand Analytics / investigation surfaces.
8. Add scenario / future experiences.
9. Continue performance, calibration, and commercialization hardening across all phases.
10. Grow the longer-term FSFFL Evidence Warehouse and proprietary intelligence flywheel.

## Maintenance rule

Update this document whenever a material roadmap decision is made. Future continuation prompts and new development chats should reference this file before creating a new priority order.