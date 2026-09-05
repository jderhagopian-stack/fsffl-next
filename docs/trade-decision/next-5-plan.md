# NEXT-5 Trade Decision Plan

NEXT-5 answers: **What does this proposed transaction do to each franchise, and how should that bilateral evidence be interpreted?**

## Charter gate

NEXT-5 lives in the Decision layer of the FSFFL NEXT architecture.

It may consume:

- canonical point-in-time league state from NEXT-1;
- probabilistic player forecasts from NEXT-2;
- typed market, intrinsic, pick, transaction, and league-context value evidence from NEXT-3;
- team-specific lineup, replacement, resilience, competitive outcome, calculated-state, and structured before/after utility outputs from NEXT-4.

It may not rewrite or independently recalculate those upstream authorities.

NEXT-5 owns bilateral transaction evaluation. It does **not** own broad candidate search, package generation, or opportunity ranking; those belong in NEXT-6 Search/Optimization. Reports and presentation remain NEXT-7/8.

## Core authority split

1. **Transaction representation** — canonical proposed transfer of players, picks, and supported transaction assets between two teams.
2. **Scenario construction** — create explicit before/after canonical roster/asset states for both sides without mutating source state or inventing unavailable assets.
3. **Bilateral consequence evaluation** — consume NEXT-4 scenario outputs for both franchises.
4. **Economic interpretation** — compare typed NEXT-3 transaction/market/intrinsic evidence without collapsing incompatible value concepts or scales.
5. **Decision evidence** — represent whether a transaction improves, harms, or trades off different authoritative channels for each side.
6. **Negotiation/acceptance evidence** — estimate plausibility from market/league/history evidence while remaining distinct from franchise utility.

## Implemented slices

### Slice 1 — transaction contracts and scenario integrity

Implemented:

- immutable bilateral proposal and leg contracts using canonical NEXT asset types;
- player, pick, and FAAB ownership validation against one pre-trade snapshot;
- immutable canonical before/after state construction;
- incoming players placed on BENCH so NEXT-4 remains authoritative for optimized role;
- future-state, duplicate-asset, impossible-ownership, FAAB, and source-immutability tests.

### Slice 2 — bilateral NEXT-4 deltas

Implemented:

- independent before/after TeamUtilityVector comparison for both teams;
- competitive, resilience, and asset-portfolio channels remain separate;
- team identity and incompatible scale/concept checks fail closed;
- no master score or recommendation.

### Slice 3 — transaction economics

Implemented:

- separate market, intrinsic, acquisition-price, and sale-price package summaries;
- expected package means may aggregate on compatible scales;
- package uncertainty is not fabricated without an authoritative covariance model;
- missing economic evidence is explicit rather than treated as zero;
- FAAB remains unevaluated until governed conversion evidence exists.

### Slice 4 — bilateral decision contract

Implemented foundation:

- directional assessment for authoritative team-consequence channels;
- uniform gain, uniform loss, mixed, neutral, and incomplete side shapes;
- bilateral mutual-gain / one-sided / mixed-or-incomplete classification;
- missing channels fail closed and cannot promote a trade to mutual gain;
- no scalar weighting across wins, resilience, and dynasty economics.

Materiality is separate and explicit:

- competitive/resilience materiality policy has no hidden defaults;
- economic materiality is tied to one explicit NEXT-3 ValueScale/version;
- thresholds require provenance, evidence-through date, and versioning;
- current tests use synthetic thresholds only and do not establish production authority.

### Slice 5 — acceptance / negotiation evidence

Implemented contracts, not an empirical probability model:

- typed point-in-time acceptance evidence items and evidence sets;
- explicit future-leakage protection;
- acceptance probability estimate contract with uncertainty interval and lifecycle status;
- explicit `NOT_ESTIMATED` state so missing calibration cannot become a fabricated prior;
- acceptance remains separate from franchise utility and decision shape.

The empirical acceptance model remains future work and must be calibrated from admissible point-in-time league/market/history evidence before promotion.

## Anti-double-counting rule

Every real-world effect enters the final decision exactly once.

Examples:

- Superflex scarcity belongs upstream in structural Value and actual NEXT-4 roster replacement consequences, not in a new generic QB premium here.
- Current-year points/wins belong to NEXT-4 simulation, not a second contender bonus in Trade Decision.
- Market price belongs to NEXT-3 and may inform opportunity cost / acceptance evidence; it is not itself team utility.
- Owner preference is explicit and separate from calculated team state.

## Validation philosophy

NEXT-5 must pass:

- structural ownership/state mutation tests;
- bilateral symmetry/integrity tests;
- channel-separation tests;
- obvious sanity cases such as rejecting economically absurd one-sided exchanges without relying on arbitrary master scores;
- point-in-time/future-leakage tests;
- exact-head CI;
- eventually realistic league adversarial cases through the shared runtime path.

Historical or empirical calibration should be batched where possible. Lack of perfect evidence must not erase a real effect: use bounded, versioned, future-updatable provisional behavior only where justified.

## Remaining NEXT-5 work

1. Integrate governed materiality policy into a richer decision view without making synthetic test thresholds authoritative.
2. Add explicit owner-posture overlay that changes preference interpretation but never calculated consequences.
3. Build the empirical acceptance/negotiation challenger from admissible point-in-time evidence; keep non-authoritative until promotion criteria pass.
4. Add obvious bilateral sanity cases and anti-double-counting/authority import guard.
5. Complete NEXT-5 exit review, exact-head CI, and merge.

## Downstream boundary

NEXT-5 evaluates a proposed transaction.

NEXT-6 will ask questions such as:

- Which assets should I shop?
- What counterparties fit?
- What packages are worth testing?
- Where is the bilateral negotiation frontier?
- What waiver/trade opportunities improve my team?

NEXT-5 must be strong enough that NEXT-6 can search over it without inventing its own value or utility logic.
