# Point-in-Time State Semantics

FSFFL NEXT treats historical reconstruction as a foundational capability.

## Core rule

Any model evaluation must be reproducible from information that was reasonably knowable at the evaluation timestamp. Future information may not leak backward into state, projections, market context, or calibration features.

## Canonical state

A `LeagueState` represents a league at a specific effective timestamp and contains or references:

- league rules and scoring configuration;
- season and week context;
- teams and rosters;
- taxi/IR/reserve state;
- draft-pick ownership;
- standings and schedule state;
- transaction history known by that time;
- player/NFL status known by that time;
- projection snapshots available by that time;
- market snapshots available by that time;
- model/evidence version metadata.

A state is immutable once materialized. New facts create a new state or derived snapshot rather than mutating historical truth.

## Effective time vs ingestion time

Every external record should distinguish:

- `effective_at`: when the fact became true or knowable;
- `ingested_at`: when NEXT received it.

Historical reconstruction uses `effective_at` and provider availability semantics, never current ingestion time alone.

## Missingness

Historical gaps must remain explicit. NEXT must not silently substitute present-day values for missing historical values.

Permitted handling includes:

- source-specific fallback known to have existed at the time;
- bounded imputation with uncertainty;
- omission from a calibration sample;
- an explicit `unknown` state.

The chosen method must be recorded in provenance.

## Snapshot identity

A state should eventually have a deterministic identity derived from material inputs, including league rules, source snapshots, timestamp, and normalization version. Equivalent inputs should reproduce the same state identity.

## Historical model execution

Backtests must pin:

1. the historical league state;
2. projection/market information available at that point;
3. the model version being evaluated;
4. parameter/evidence versions;
5. random seeds or simulation metadata when stochastic.

This enables fair challenger-vs-production comparisons without hindsight contamination.

## Commercial implication

Point-in-time state must be platform-neutral. Sleeper is an adapter that supplies records; Sleeper identifiers and payload shapes must not define the canonical domain model.
