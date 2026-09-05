# NEXT-7 Analytics & API Plan

NEXT-7 answers: **How do we expose the authoritative FSFFL NEXT outputs so a human or product can understand the league, teams, trades, opportunities, and model evidence without changing what the model decided?**

## Charter gate

NEXT-7 is a read-only Analytics / API layer.

It may consume:

- canonical State from NEXT-1;
- Forecast outputs from NEXT-2;
- typed Value outputs from NEXT-3;
- Team Utility / Simulation outputs from NEXT-4;
- Trade Decision outputs from NEXT-5;
- Opportunity Search outputs from NEXT-6.

It may organize, join, summarize, filter, serialize, label, and present those outputs.

It may **not**:

- change player/pick values;
- alter forecasts or simulations;
- create a second team-utility calculation;
- repair a trade disposition or opportunity action tier;
- convert unknown acceptance into likely acceptance;
- invent ranking weights or a league/team master score;
- add hidden business logic in report formatting;
- infer owner intent that was not supplied explicitly.

If an upstream output is missing or provisional, analytics must display that state rather than silently filling it.

## Product goals

NEXT-7 should make the system understandable in plain English and usable by a future UI/API consumer.

Core questions include:

- What does each roster look like and how strong is it now and long term?
- How do teams compare on explicit metrics such as projected scoring, playoff odds, roster value, age/forecast horizons, resilience, and draft capital?
- Which assets are most valuable to the market versus this specific team context?
- Which teams are natural trade partners based on evaluated opportunity evidence?
- Which opportunities are actionable, market-test only, diagnostic, or blocked—and why?
- What is missing or uncertain in the evidence?
- How complete was the search?
- What historical acceptance/owner-behavior evidence exists when available?

## Architectural split

### Analytics authority

Analytics may derive **read-only summaries of authoritative fields**, for example:

- sorting teams by expected wins;
- sorting assets by one named NEXT-3 value concept;
- calculating counts/percentages from explicit candidate states;
- presenting before/after deltas already produced upstream;
- grouping opportunities by counterparty, position, type, or action tier;
- turning typed values into report-ready rows.

### Not analytics authority

Analytics may not derive a new substantive decision metric such as:

- weighted league power score;
- hidden trade grade;
- hidden contender premium;
- hidden owner-likelihood score;
- opportunity score combining wins + value + acceptance;
- adjusted player value for presentation convenience.

If a future composite is desired, it must have an explicit governed upstream authority before Analytics displays it.

## Implementation slices

### Slice 1 — API/version/provenance envelopes

- stable response envelope;
- schema version;
- model/version lineage;
- league/state/as-of identity;
- generated-at timestamp distinct from evidence timestamps;
- warnings/provisional/missing-evidence fields;
- deterministic serialization.

### Slice 2 — team analytics view

Read-only team snapshot containing, when supplied:

- roster organized by canonical roster slot;
- player position and identity;
- forecast means/distributions and horizon;
- typed market/intrinsic value evidence;
- optimized starting lineup;
- roster resilience;
- competitive outcomes;
- calculated competitive state;
- owner strategic posture shown separately;
- draft-pick inventory and value evidence.

No new team-strength formula.

### Slice 3 — league analytics view

- one comparable row per team;
- explicit named metric tables/rankings;
- league distributions/percentiles only for named authoritative metrics;
- roster construction summaries;
- draft-capital summaries;
- competitive-state distribution;
- value/forecast/search evidence completeness.

### Slice 4 — opportunity analytics

- candidates grouped by action authority;
- evidence-completeness and reason counts;
- trade counterparties;
- negotiation/frontier/search coverage;
- Pareto/front membership;
- waiver/add-drop opportunities;
- unknown acceptance displayed as unknown;
- diagnostics kept visible separately from actionable opportunities.

### Slice 5 — trade partner intelligence

Consume evaluated NEXT-5/NEXT-6 evidence to summarize:

- counterparties with the largest number of evaluated compatible opportunities;
- mutual-gain / mixed / dominated counts;
- acceptance evidence status;
- historical league/owner evidence when available;
- searched/exhausted/truncated coverage.

This is descriptive partner intelligence, not a new trade-likelihood model.

### Slice 6 — report-ready view models

Provide stable data contracts for polished reports including:

- plain-English labels;
- tables/charts data;
- why/why-not evidence;
- explicit model limitations/provisional states;
- before/after consequences;
- provenance/version footnotes.

Report formatting must not contain hidden model calculations.

### Slice 7 — read-only API service

- query by league/team/opportunity identifiers;
- provider-neutral service contracts;
- deterministic response schemas;
- cache/version keys tied to authoritative input identity;
- no mutation endpoints in NEXT-7.

### Slice 8 — validation / exit

- authority/import boundary guard;
- deterministic serialization tests;
- no-hidden-score regression tests;
- missing/provisional evidence propagation;
- team/league metric ranking tests using explicitly named metrics;
- opportunity action-tier preservation;
- report-model parity with API-model fields;
- integrated live-league beta when networked runtime becomes available.

## Reports and NEXT-8

NEXT-7 owns the **read-only analytics/report data model and reproducible report outputs**. NEXT-8 owns the interactive product experience.

A polished static report may be rendered from NEXT-7 contracts provided the renderer contains no business logic. Interactive dashboards, controls, user flows, and product-specific state belong in NEXT-8.

## First implementation target

Build the common **Analytics API envelope and lineage/warning contracts** first. Every later analytics/report object should carry enough identity and provenance to reproduce what the user saw.
