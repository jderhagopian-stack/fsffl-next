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
6. **Negotiation/acceptance evidence** — eventually estimate plausibility from market/league/history evidence while remaining distinct from franchise utility.

## First implementation slices

### Slice 1 — transaction contracts and scenario integrity

- immutable transaction proposal types;
- explicit giver/receiver asset ownership validation;
- canonical player/pick transfer application;
- no impossible duplicate ownership;
- no mutation of source LeagueState;
- point-in-time/future-leakage checks;
- no recommendation language.

### Slice 2 — bilateral NEXT-4 deltas

- evaluate before/after TeamUtilityVector for both sides;
- preserve competitive, resilience, and economic channels separately;
- expose direction and magnitude of deltas without a master score;
- fail closed when required upstream evidence is absent or incompatible.

### Slice 3 — transaction economics

- consume NEXT-3 typed market/intrinsic/transaction evidence;
- preserve scale/concept compatibility;
- distinguish franchise utility from market price and likely transaction price;
- avoid generic consolidation, QB, contender, or scarcity bonuses unless a real effect is empirically justified and has one authoritative home.

### Slice 4 — bilateral decision contract

- identify Pareto-improving, mixed-tradeoff, and clearly dominated outcomes by authoritative channel;
- calculated team state remains separate from owner strategic posture;
- owner posture may later affect decision preference explicitly without rewriting calculated consequences;
- no candidate search or package balancing.

### Slice 5 — acceptance / negotiation evidence

- build a separately typed acceptance or market-feasibility estimate from point-in-time league/market/history evidence;
- utility and acceptance must never be conflated;
- low evidence must widen uncertainty rather than silently produce confidence;
- challenger/provisional behavior governed explicitly.

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

## Downstream boundary

NEXT-5 evaluates a proposed transaction.

NEXT-6 will ask questions such as:

- Which assets should I shop?
- What counterparties fit?
- What packages are worth testing?
- Where is the bilateral negotiation frontier?
- What waiver/trade opportunities improve my team?

NEXT-5 must be strong enough that NEXT-6 can search over it without inventing its own value or utility logic.
