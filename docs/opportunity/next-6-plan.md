# NEXT-6 Opportunity Engine Plan

NEXT-6 answers: **Given the authoritative league state, values, team consequences, and transaction decision logic, what opportunities are worth testing for this team?**

## Charter gate

NEXT-6 is the Search / Optimization layer of FSFFL NEXT.

It may consume:

- canonical point-in-time league state from NEXT-1;
- NEXT-2 forecasts only through their authoritative downstream consequences;
- typed NEXT-3 value and transaction-price evidence;
- NEXT-4 team utility, simulation, lineup, replacement, resilience, and scenario outputs;
- NEXT-5 bilateral trade evaluation, economics, decision shape, materiality, negotiation feasibility, acceptance evidence, and disposition.

It may **not**:

- alter player/pick values;
- add a second scarcity, Superflex, contender, consolidation, or roster-need premium;
- rewrite NEXT-4 competitive outcomes or team utility;
- invent acceptance probability when NEXT-5 says `NOT_ESTIMATED`;
- convert incomplete evidence into positive action authority;
- hide search preferences inside upstream calculations;
- own report/presentation logic (NEXT-7/8).

Search proposes and orders candidates. Upstream layers remain authoritative about what those candidates mean.

## Governing search principles

### 1. Discovery and action authority are separate

An interesting theoretical candidate may remain visible for diagnostics or market testing while being ineligible for actionable promotion.

Examples:

- counterparty-dominated proposal -> may be visible as diagnostic/theoretical, not promoted as realistic actionable opportunity without contrary acceptance evidence;
- unknown acceptance -> remains unknown;
- incomplete economic evidence -> visible with missing evidence, not silently scored as zero;
- conditional NEXT-5 disposition -> requires the explicit governed materiality policy that produced it.

### 2. Multi-objective before scalar ranking

The search space should preserve distinct objectives such as:

- focal-team competitive improvement;
- long-term economic improvement;
- roster resilience;
- market/transaction economics;
- counterparty consequences;
- negotiation feasibility;
- evidence completeness.

NEXT-6 should prefer Pareto/frontier logic and explicit ranking policy over a hidden master opportunity score.

### 3. Search may prune, not revalue

Pruning may remove candidates that are structurally impossible, obviously dominated, outside configured search bounds, or redundant. It may not change asset value or utility to make search easier.

### 4. Expensive work should be staged

Use cheap authoritative evidence to reduce the universe before expensive simulation where safe:

1. structural eligibility / ownership;
2. coarse typed market/economic bounds;
3. candidate/package generation;
4. NEXT-4/NEXT-5 scenario evaluation;
5. expensive simulation or deeper frontier expansion only for survivors.

Any shortcut must be validated not to remove known good opportunities systematically.

## Opportunity classes

NEXT-6 should support a common opportunity contract with type-specific evaluators.

Initial classes:

- bilateral trades;
- waiver/free-agent additions and corresponding roster drops;
- asset-shopping / likely counterparty discovery;
- counter/price-curve exploration around a proposed trade.

Future opportunity classes may plug into the same search framework without creating new valuation authority.

## Implementation slices

### Slice 1 — search contracts and candidate lifecycle

- immutable opportunity/candidate identity;
- focal team and point-in-time state identity;
- discovery status vs action-authority status;
- evidence completeness and rejection reasons;
- deterministic reproducibility/versioning.

### Slice 2 — trade candidate universe

- enumerate legal counterparties and transferable asset sets from canonical state;
- configurable search bounds for package size and asset types;
- no arbitrary value changes;
- cheap economic bounds may prune only when scale-compatible and evidence-complete.

### Slice 3 — package generation and deduplication

- canonical package identity independent of asset ordering;
- no duplicate/equivalent packages;
- bounded combinatorial generation;
- incremental expansion around promising candidates rather than exhaustive explosion.

### Slice 4 — NEXT-5 evaluation pipeline

For each surviving proposal:

- construct canonical before/after scenario;
- consume/obtain NEXT-4 team consequences;
- bind NEXT-3 economics;
- calculate economic net where complete;
- classify bilateral decision shape;
- attach explicit owner posture;
- apply governed materiality only when supplied;
- assess negotiation feasibility;
- obtain conditional disposition;
- preserve `NOT_ESTIMATED` acceptance as unknown.

### Slice 5 — negotiation frontier / price discovery

- expand from a seed proposal along explicit asset/package changes;
- identify focal-team and counterparty Pareto/frontier regions;
- show where a proposal transitions from dominated to mixed/mutual-gain territory;
- avoid the legacy failure mode where search stops too early or theoretical packages crowd out realistic ones;
- no hidden package-concentration premium unless governed upstream evidence supports it.

### Slice 6 — opportunity ordering

Ordering policy should be explicit and versioned.

Initial architecture should allow:

- Pareto-front membership;
- action-authority tier;
- evidence completeness;
- focal-team material gains/losses;
- negotiation feasibility;
- optional user strategic posture as a separate preference overlay.

No unvalidated scalar ranking weights should be made authoritative merely for convenience.

### Slice 7 — waiver / free-agent opportunities

- legal add/drop state mutation;
- actual roster replacement and lineup consequences through NEXT-4;
- economic value through NEXT-3;
- compare hold/drop/add scenarios without trade-specific counterparty logic;
- share candidate lifecycle, evidence, and ranking contracts with trade opportunities.

### Slice 8 — sanity, performance, and exit

- synthetic opportunity sanity suite;
- known failure-harvesting cases from legacy behavior as regression concepts, not inherited authority;
- candidate-universe completeness checks on bounded fixtures;
- pruning recall tests;
- deterministic/reproducible search;
- profiler and staged-cost checks;
- authority/import boundary guard;
- integrated real-league beta when networked runtime becomes available.

## Known NEXT-5 constraints NEXT-6 must respect

The following are explicit, not bugs to work around:

- production materiality thresholds are not yet calibrated;
- acceptance probability is `NOT_ESTIMATED` until an empirical model is promoted;
- owner posture does not yet automatically resolve mixed material tradeoffs;
- package economic covariance is unavailable.

NEXT-6 may search and surface candidates under these conditions, but must preserve the uncertainty and withhold unsupported action claims.

## First implementation target

Build the common **candidate lifecycle and action-authority contract** first.

This is the key architectural guardrail that lets the Opportunity Engine explore aggressively without presenting every theoretical candidate as a realistic recommendation.
